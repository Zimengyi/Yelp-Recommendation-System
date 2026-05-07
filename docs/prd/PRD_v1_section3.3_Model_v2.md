### §3.3 推荐模型 Spec

> [!note] v2 更新说明 (2026-05-04)
>
> **本版本基于 Figma Make 原型审计（`figma_make_audit.md`，2026-05-04）对 v1 的定向更新。** 主要变更：
> 1. §3.3.1 新增 H9（activity 语义匹配）+ H10（MMR 多样性重排），假设总数 10 条
> 2. §3.3.2 新增 Q11（activity text 数据可用性）
> 3. §3.3.3 新增 3 个 Context 特征（`period_id` / `activity_emb` / `prior_meals_cuisines`），总特征数 23 → 26
> 4. §3.3.4 两层架构 ASCII 图更新，加入 MMR + Heuristic 后处理层
> 5. **新增 §3.3.4.5** — Trip 场景的多样性重排（MMR + Heuristic Constraint Layer）
> 6. §3.3.5 超参扫描表新增 MMR λ 行
> 7. §3.3.7 新增 L7（sentence-transformer pipeline 风险）+ L8（MMR λ 敏感度）
> 8. 底部交叉引用表更新
>
> **未改动**：DeepFM 数学形式、训练 Protocol、消融 baseline 表、正则化原理数学部分。
>
> **v2.1 增订（2026-05-05）**：新增 §3.3.0.5 stub「训练数据 vs 部署用户的桥接策略」+ 配套独立 explainer 文档 [`recommender_training_explainer.md`](./recommender_training_explainer.md)（约 600 行，用搜索域语言彻底讲透"无真实用户如何训练推荐"这一核心方法学问题）。PRD 主体只放 1 段 stub，详细讨论（搜索 vs 推荐对照、训练数据流、正负样本、temporal split、双塔/精排两层架构、offline vs online 评测、三种 deploy 用户状态 S0/S1/S2、persona demo、OOV embedding 实装、FAQ）全部在 explainer 文档里。同步在 §3.3.3 缺失处理规则末尾加链接。

>
> **v2.2 增订（2026-05-06）**：基于"我们也是搜索场景"的定位讨论后，§3.3.4 架构图升级为**单 DeepFM 模型 + 双路召回**——S1 push recsys 走 Two-Tower 召回，S2/S6 conversational recsys 走 LLM intent + hard filter 召回，两路 share 同一个 DeepFM 精排模型，**不训练独立的搜索模型**。intent 在召回阶段作 SQL-style 硬约束（cuisine match / price ≤ X / dietary 兼容），不进 DeepFM 输入特征。这是 CRS (Conversational Recommendation) 学术范式标准实现（Lei et al. 2020 EAR / Sun & Zhang 2018）。同步更新 §3.3.7 L3（Two-Tower 风险范围缩小到仅影响 S1 路径）。
---

#### §3.3.0 评分映射

本节是 ML2 期末 Project 40% 成绩的核心战场，直接覆盖 8-criterion rubric 中的 5 项。Criterion 2（假设/假说）由 §3.3.1 承接，列出 **10 条**带可验证形式的建模假设——v2 在 v1 的 H1-H8 基础上新增 H9（activity 语义对齐）与 H10（MMR 多样性重排有效性）；Criterion 3（EDA）在 §3.3.2 以 placeholder 形式给出 Zimeng + Cindy 必须回答的具体问题清单（v2 新增 Q11 activity text 数据可用性）；Criterion 4（特征工程）由 §3.3.3 展开完整的 **26 个特征**三列表（v2 新增 `period_id` / `activity_emb` / `prior_meals_cuisines` 三个 Context 特征）；Criterion 5（方案 + 过拟合检测）由 §3.3.4 给出 DeepFM 架构图 + 消融 baseline + 过拟/欠拟检查清单，**v2 在两层架构图中增加 MMR + Heuristic 后处理层，并以 §3.3.4.5 专节展开 Trip 场景多样性重排方案**；Criterion 6（选型 + 正则化）由 §3.3.5 给出超参扫描协议和正则化决策（v2 新增 MMR λ 扫描行）。

> [!success] ✅ 决策
>
> **DeepFM**（deepctr-torch 实现）作为**主交付模型（且唯一训练的 ranker）**；**双路召回**：S1 push 路走 Two-Tower / DSSM 召回 (top-200 dense retrieval)，S2/S6 conversational 路走 LLM intent + hard filter 召回 (top-100)，两路 share 同一个 DeepFM 精排；**FM**（xLearn / pyfm）+ **MF**（Surprise）作为消融对照基线；**MMR 重排层**作为 Trip 场景 top-3 候选的多样性后处理（§3.3.4.5）。**不训练独立的搜索模型**——CRS 范式下 intent 作召回 filter，不作 ranker 特征。评分卷面上，FM/DeepFM 合起来直接命中教授 rubric 原文「hybrid or factorization machine」关键词。

---

#### §3.3.0.5 训练数据 vs 部署用户的桥接策略（stub）

> [!warning] ⚠️ 关键概念
>
> **训练时的"用户" ≠ 部署时的"用户"**。训练阶段用 Yelp ~2M 历史用户（实测 1,987,897）+ ~7M reviews（实测 6,990,280）+ 15 万商家（实测 150,346）作 proxy——**模型学的是"什么样的 user features 组合 → 偏好什么样的 items" 这种可迁移 pattern**，不是绑定到具体 user_id 的口味记忆；离线评测在 Yelp temporal hold-out test 集上跑（AUC / NDCG@10 / Recall@10 / Cold-start AUC），**不需要任何 Taste hunter 真实用户**即可完成 ML2 全部评分要求。部署阶段 Taste hunter 真实用户走冷启动路径：8 个 user features 中 6 个可从对话累积偏好或默认值"重建"（avg_rating_given / review_count_log / fav_cuisine_emb / price_tolerance_avg / mean_distance_traveled / days_active），复用训练好的 weight；只有 `user_id` embedding 走 OOV mean。Demo 演示编排为三帧：S0 完全冷启动 → S1 对话累积偏好 → 压轴 Persona 锚定演示个性化能力（诚实标注「persona 模拟」）。

> [!info] 完整讨论见独立 explainer 文档
>
> 上述只是 PRD 主体里的 1 段总结。**详细讨论**（搜索 vs 推荐对照表 / 训练数据流 / 正负样本定义 + 负采样 / temporal hold-out 切分逻辑 / 双塔召回 + DeepFM 精排两层架构与倒排拉链的对应 / offline vs online 评测的边界 / 三种 deploy 用户状态 S0/S1/S2 / Demo 三帧编排话术 / OOV embedding 实装伪代码 / User Features 部署 fallback 速查表 / H6 假设的双重意义 / FAQ）见独立文档：
>
> 📄 [`recommender_training_explainer.md`](./recommender_training_explainer.md)（约 600 行，用搜索域语言彻底讲透）
>
> 这一节在 ML2 期末报告里只占 1 段——评分核心仍是 §3.3.1 H1-H10 假设、§3.3.3 26 特征、§3.3.4 DeepFM 架构、§3.3.5 正则化 sweep、§3.3.6 训练 protocol。本 stub 的存在是为了让团队（Zimeng / Cindy）和评分者一眼就能 grok "为什么我们没有真实用户也能跑出 metric"。

---

#### §3.3.1 模型假设 (rubric criterion 2)

建模假设是推荐系统可信度的基础——假设错误，再好的模型也是空中楼阁。我们在设计特征和实验之前先显式写出 **10 条**核心假设，并为每条指定可操作的验证方式，确保"假设 → 设计 → 实验 → 结论"的完整闭环。H9/H10 为 v2 新增，源自 Figma Make 原型审计发现的 Trip 场景需求。

| #             | 假设内容                                                                                                                                    | 验证方式                                                                                                                                                                           | 期望结果                                                                                           |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| H1            | 用户对相似 cuisine 的店有偏好聚类——个体对菜系存在连贯偏好，而非随机选择                                                                                               | 在训练完成的 DeepFM 中，提取 cuisine × cuisine 二阶交叉项的权重重要度；与全部二阶交叉项的 median 比较                                                                                                           | cuisine-cuisine 交叉 feature importance > median，说明 FM 二阶交叉已学到聚类偏好                               |
| H2            | 地理距离对 ranking 得分有单调负相关关系——越近的餐厅，在同等质量下排名越靠前                                                                                             | 用 SHAP 分析 `distance_from_user_km_log` 对模型输出 logit 的贡献，绘制 SHAP dependence plot                                                                                                  | SHAP 值随距离增大单调递减（95% 样本无反转），验证距离对 scoring 的单调负效应                                                |
| H3            | 高评分 + 高评论数的餐厅，其先验可信度更高；原始均值在稀疏数据下有噪声，需 log-transform + Bayesian smoothing                                                               | 比较 raw avg_rating 与 Bayesian smoothed rating 的 RMSE，在评论数 < 20 的稀疏商家子集上评估                                                                                                       | Smoothed rating 使稀疏商家的离群噪声下降 ≥ 20%；log(review_count) 与 click-like 的 Pearson > 0.15             |
| H4            | 时段（早/午/晚）显著影响候选集——餐厅的受欢迎度随时段有不同峰值                                                                                                       | 构造 `hour_bucket × cuisine` 交叉特征，在 DeepFM 和纯 FM 模型中分别计算该交叉项带来的 NDCG@10 lift（通过 ablation 开关该 feature）                                                                            | 交叉特征带来 NDCG@10 lift ≥ 0.005（绝对值）；时段 × 早餐类 cuisine 交叉的 lift 最显著                                 |
| H5            | 行程上下文（旅行第几天、所在区域聚类、**以及 activity 语义和 period_id**）会改变用户偏好，使得 trip-aware context feature 提供额外 NDCG 增益                                     | 通过 ablation 对比加入 / 不加入 `trip_day_index`、`region_cluster_id`、`period_id`、`activity_emb` 的模型，在行程型用户子集上评估 NDCG@10                                                                 | 加入完整 trip context features 后，NDCG@10 在多天行程用户子集上提升 ≥ 0.003                                      |
| H6            | Cold-start 用户（历史评论 < 5 条）的推荐质量对内容特征（cuisine / price / tags）的依赖 > 协同特征（user embedding）                                                   | 分别训练「全特征」模型和「去掉 user_id embedding」模型，在冷启动用户子集（< 5 reviews）上比较 Recall@10                                                                                                        | 去掉 user embedding 的模型在冷启动子集上 Recall@10 **不显著下降**（< 0.01 差距），说明内容特征足以覆盖冷启动                      |
| H7            | Hybrid 模型（DeepFM）比纯协同过滤（MF）有统计显著的推荐质量提升                                                                                                 | 全量测试集（temporal hold-out）上对比 DeepFM vs MF 的 NDCG@10 和 Recall@10                                                                                                                 | DeepFM NDCG@10 ≥ MF + 0.03（绝对值 3pp），Recall@10 亦优于 MF；差距用 bootstrap 置信区间验证                      |
| H8            | 序列建模（GRU4Rec 类方案）在我们 trip 场景下相对 DeepFM 没有显著优势——因为 Yelp review 数据非 session 级 click，合成 session 引入噪声                                       | 可选 ablation：在合成 session（user_id + 7 天时间窗口）上训练简版 GRU4Rec，与 DeepFM 在同测试集上比较 NDCG@10                                                                                              | GRU4Rec NDCG@10 提升 < 0.005（不显著）或低于 DeepFM；佐证不花精力在序列模型的决策                                       |
| **H9** ⭐ NEW  | **Activity 文本与餐厅类目存在显著语义匹配**——如"看完日落"语义靠近 seafood / bar / sunset view 的店；"逛 Walnut Street 之间"靠近 cafe / quick brunch。                      | 计算 `activity_emb`（sentence-transformer 输出 → 32-dim）与餐厅 `category_emb` 的 cosine similarity；ablation：在 trip plan 场景下加入 / 不加入 `activity_emb` 后 NDCG@3 / per-period diversity 的变化。 | 加入后 per-period top-3 候选的 cuisine 多样性 ≥ 0.66（avg 至少 2 unique cuisines per top-3），无显著 NDCG@3 下降。 |
| **H10** ⭐ NEW | **单段 top-3 候选的多样性（cuisine + 价位）应当通过 MMR (Maximal Marginal Relevance) 重排实现**，而不是单纯按 DeepFM score 排序——纯 score-greedy 会导致 top-3 同 cuisine。 | 对比 score-greedy top-3 vs MMR top-3 的 cuisine diversity；MMR 参数 λ 在 {0.5, 0.6, 0.7, 0.8} 之间扫描，用 per-period top-3 cuisine diversity vs NDCG@3 评估。                                 | MMR 能保证 per-period top-3 cuisine 多样性 ≥ 0.66，同时 NDCG@3 相比 greedy 下降 < 0.005（多样性增益不以质量为代价）。      |

**备注**：H8 为可选验证项，若时间紧张可作为 Future Work 中的"为何不做序列模型"论据引用，无需实验。H5 中 trip context 的合成方法（将同一用户在 ±3 天内的评论聚合为伪行程 session）作为已知限制在 §3.3.7 中详述。H9/H10 对应的 demo activity 库共 27 条（3 days × 3 periods × 3 candidates），详见 §3.3.7 L7。

---

#### §3.3.2 EDA 计划 (rubric criterion 3 — Zimeng + Cindy 主笔)

> [!warning] Status
>
> **本节由 Zimeng + Cindy 主笔**，2026-05-05 前交一稿初版。以下为 EDA 必须回答的具体问题清单，作为分工起点，非最终内容。

EDA 需要回答的 11 个关键问题（按优先级排序）：

1. **用户评分分布与 power-law 检查**：Yelp 评分是否呈现 J 型分布（大量 4-5 星，少量 1-2 星）？用户活跃度是否满足 power-law（少数用户贡献大量 review）？绘制 rating 直方图 + user review count 对数-对数图，拟合幂律指数。

2. **User-Item 矩阵稀疏度 heatmap**：对 target 城市（Philadelphia + Tucson + Tampa）子集，计算矩阵密度（non-zero ratio）。稀疏度 > 99.5% 时需讨论 cold-start 策略对模型选择的影响。

3. **Top categories 分布**：Yelp `categories` 字段多值，统计 top-30 cuisine/类目频次，确认 Italian / Chinese / Mexican / Sushi / Brunch 等高频标签的分布，指导 multi-hot 编码维度设计。

4. **地理分布可视化**：对 3 个 target 城市的餐厅 lat/lon 做 scatter map，确认数据密度和覆盖范围；同时验证 k-means 区域聚类（`region_cluster_id`）的合理 k 值（肘部法则，k=5-10）。

5. **时段入住分布（合成 trip context 依据）**：从 review 的 `date` 字段提取小时分布（Yelp review date 精确到日期，无小时；可用 tip/check-in 数据或 business hours 推断）。如果缺少小时信息，在 EDA 中明确说明 trip-context 特征的数据来源限制。

6. **冷启动用户比例**：统计 review_count < 5 的用户占比（预期 > 40%）；以及 target 城市中 review < 10 的商家占比。这直接决定 H6 假设的重要性和内容特征的权重。

7. **照片覆盖率**：统计 target 城市餐厅中有至少 1 张 Yelp photo 的商家比例；如果 photos.json（5GB）未下载，用 photo_count 元数据字段（business 表中）估算。决定 F1 卡片 UI 的 fallback 策略（无图时用 `#DCDDE8` placeholder）。

8. **Review 长度分布**：分析 review text 字符数分布（P50 / P90 / P99），为 AI Overview 模块的 LLM 输入 token cap 选定截断阈值（建议 P90 对应约 512 tokens）。

9. **跨城市用户流动率**：计算在 ≥ 2 个不同城市有 review 的用户占比——这是"trip-planning 用户"的代理指标，越高则说明 Yelp 数据对旅行推荐场景的覆盖越好。

10. **人气偏差（Popularity Bias）诊断**：Top-1% 商家贡献的 review 数占比；如果 > 50%，说明存在显著人气偏差，需要在训练时做 popularity debiasing 或在报告 Criterion 7 中说明其对 NDCG 的影响。

11. **⭐ Activity text 数据可用性评估（v2 新增，Zimeng + Cindy 必须回答）**：Yelp Open Dataset **没有**原生 activity 描述字段；需评估以下两种替代路径的成本与可行性：(a) **LLM 生成**——对每个行程时段动态生成 activity 文本（Sonnet 单次 ~0.003$，demo 27 条约 $0.08，可接受；但线上场景是实时生成，引入延迟）；(b) **手工模板库**——预制 30-50 条 activity 模板（Philadelphia 经典景点 + 活动类型），覆盖 demo 场景（多样性受限，但无 LLM 调用延迟）。EDA 产出：明确推荐哪条路径，以及 demo 27 条 activity 文本的来源说明。

**EDA 产出形式要求**（给 Zimeng + Cindy 的格式指引）：

| EDA 问题 | 期望产出图表 / 统计 | 报告节点 |
|---|---|---|
| Q1 评分分布 + power-law | rating 直方图 + log-log user review count scatter | §3.3.2 EDA 图 1/2 |
| Q2 稀疏度 heatmap | 用户 × 商家 density matrix（随机 1K × 1K 采样） | §3.3.2 EDA 图 3 |
| Q3 Top categories | 条形图 top-30 cuisine 频次 | §3.3.2 EDA 图 4 |
| Q4 地理分布 | 散点图（3 城市各一张）+ k-means 肘部曲线 | §3.3.2 EDA 图 5 |
| Q5 时段分布 | 若有 check-in 数据：小时分布直方图；否则：business hours 解析结果 | §3.3.2 EDA 图 6 |
| Q6 冷启动比例 | 饼图 / 柱状图（< 5 review 用户占比 vs ≥ 5） | §3.3.2 EDA 文字 |
| Q7 照片覆盖率 | 简单统计数字 + 商家 photo_count 分布直方图 | §3.3.2 EDA 文字 |
| Q8 Review 长度 | 箱线图（P25/P50/P75/P90/P99） | §3.3.2 EDA 图 7 |
| Q9 跨城市流动率 | 单一统计数字 | §3.3.2 EDA 文字 |
| Q10 人气偏差 | Lorenz 曲线 + Gini coefficient | §3.3.2 EDA 图 8 |
| Q11 Activity text 可用性 | 路径对比表（LLM 生成 vs 模板库）+ demo 27 条 activity 来源说明 | §3.3.2 EDA 文字（与 §3.3.7 L7 联动） |

---

#### §3.3.3 特征工程 (rubric criterion 4)

特征工程的核心原则：**所有特征均来自 Yelp Open Dataset 原生字段，不引入外部 API**（规避 Google Maps 依赖）；数值型特征做 log-transform 处理长尾分布；类别型特征视 cardinality 选择 embedding 或 one-hot；context features 的合成逻辑在 §3.3.7 中文档化为已知限制。v2 新增 3 个 Trip 场景 Context 特征（`period_id` / `activity_emb` / `prior_meals_cuisines`），在 H9/H10 假设验证中起核心作用。

共计 **26 个特征**，分 User / Item / Context 三组（Context group v2 由 6 扩展至 9）：

| 特征名                                        | 类型                                        | Yelp 数据源字段路径                                                   | 转换方式                                                                                                                                | 为什么有用                                                                                                                                                                                   |
| ------------------------------------------ | ----------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **— User Features (8) —**                  |                                           |                                                                |                                                                                                                                     |                                                                                                                                                                                         |
| `user_id`                                  | Embedding (cardinality ~2M)               | `review.user_id`                                               | 查表 embedding, dim=8 (default)                                                                                                       | 捕捉用户长期偏好的协同过滤信号                                                                                                                                                                         |
| `avg_rating_given`                         | Numeric                                   | `user.average_stars`                                           | 归一化到 [0,1]                                                                                                                          | 用户评分尺度校准（宽松 vs 严格评分者）                                                                                                                                                                   |
| `review_count_log`                         | Numeric                                   | `user.review_count`                                            | log1p(x)                                                                                                                            | 用户活跃度代理；处理 power-law 长尾                                                                                                                                                                 |
| `mean_distance_traveled`                   | Numeric                                   | 从 user 历史 review 的 business lat/lon 聚合计算                       | log1p(mean of pairwise dist); 可简化为用户历史 unique city 数                                                                                | 衡量用户旅行半径，高值 → 对旅行推荐更感兴趣                                                                                                                                                                 |
| `fav_cuisine_emb`                          | Embedding (dim=8)                         | user 历史 review 商家的 categories 聚合                               | 对 top-3 cuisine one-hot 做平均 pooling                                                                                                 | 用户显式口味偏好；cold-start 用户可用全局 prior 填充                                                                                                                                                     |
| `price_tolerance_avg`                      | Numeric                                   | 用户历史 review 商家的 `attributes.RestaurantsPriceRange2` 均值         | 归一化到 [0,1]                                                                                                                          | 用户消费档次偏好                                                                                                                                                                                |
| `days_active`                              | Numeric                                   | `user.yelping_since` → 到今天的天数                                  | log1p(days)                                                                                                                         | 用户平台粘性，影响协同信号可靠性                                                                                                                                                                        |
| `elite_flag`                               | Binary                                    | `user.elite` 是否非空                                              | 1/0                                                                                                                                 | Elite 用户的 review 可靠性更高，可作为权重加权                                                                                                                                                          |
| **— Item Features (9) —**                  |                                           |                                                                |                                                                                                                                     |                                                                                                                                                                                         |
| `business_id`                              | Embedding (cardinality ~150K)             | `business.business_id`                                         | 查表 embedding, dim=8                                                                                                                 | 捕捉商家隐向量（协同侧）                                                                                                                                                                            |
| `categories_multi_hot`                     | Multi-hot (top-50 categories)             | `business.categories`                                          | 拆 comma-separated → multi-hot 或 embedding bag                                                                                       | 菜系内容信号；覆盖 cold-start item                                                                                                                                                               |
| `avg_rating`                               | Numeric                                   | `business.stars`                                               | Bayesian smoothed rating: $\tilde{r} = \frac{C \cdot \mu_{global} + \sum r_i}{C + n}$，其中 $C=10$（先验强度），$\mu_{global}$ 为全局均值，$n$ 为评论数 | 消除低评论数商家（n<10）的噪声均值；C=10 意为"等价于 10 条评论的先验质量"（H3）                                                                                                                                        |
| `review_count_log`                         | Numeric                                   | `business.review_count`                                        | log1p(x)                                                                                                                            | 人气度特征；与 avg_rating 联合使用 (H3)                                                                                                                                                            |
| `price_level`                              | Ordinal (1-4)                             | `business.attributes.RestaurantsPriceRange2`                   | bucketize → 4-category embedding                                                                                                    | 价格分档是常见过滤维度                                                                                                                                                                             |
| `is_open`                                  | Binary                                    | `business.is_open`                                             | 1/0 直接使用                                                                                                                            | 排除已关闭商家（候选生成时可做硬过滤）                                                                                                                                                                     |
| `has_outdoor_seating`                      | Binary                                    | `business.attributes.OutdoorSeating`                           | parse string "True"/"False" → 1/0                                                                                                   | 旅行场景常见偏好（天气好时权重更高）                                                                                                                                                                      |
| `photo_count`                              | Numeric                                   | 从 `photos.json` 统计，或 business 元数据估算                            | log1p(x); 缺失时填 0                                                                                                                    | 图片越多，UI 展示越好；也是商家活跃度代理                                                                                                                                                                  |
| `city_id`                                  | Embedding (cardinality ~30 target cities) | `business.city`                                                | 查表 embedding, dim=4                                                                                                                 | 跨城市推荐的城市偏差修正                                                                                                                                                                            |
| **— Context Features (9, v2 从 6 扩展至 9) —** |                                           |                                                                |                                                                                                                                     |                                                                                                                                                                                         |
| `distance_from_user_km_log`                | Numeric                                   | 用户当前 lat/lon（demo 中用 IP 或手动输入）vs `business.latitude/longitude` | Haversine → km → log1p(x)                                                                                                           | 地理距离是核心 ranking factor (H2)                                                                                                                                                             |
| `hour_bucket`                              | Cyclic Embedding                          | 当前小时 (0-23)                                                    | sin/cos 编码（2 维）+ 3-bucket 粗粒化（早 6-11 / 午 11-17 / 晚 17-23）                                                                           | 时段影响候选集 (H4)；cyclic 编码保留连续性                                                                                                                                                             |
| `day_of_week`                              | Categorical (7)                           | 当前日期 weekday                                                   | one-hot 或 embedding (dim=4)                                                                                                         | 周末 vs 工作日行为不同                                                                                                                                                                           |
| `is_weekend`                               | Binary                                    | 从 day_of_week 派生                                               | 1=Sat/Sun                                                                                                                           | 粗粒化版本，与 day_of_week 互补                                                                                                                                                                  |
| `trip_day_index`                           | Numeric                                   | 用户行程第几天（由 chatbot 对话解析或用户输入）                                   | 归一化到 [0,1]（假设行程 ≤ 14 天）；缺失时填 0                                                                                                      | trip-context 核心特征 (H5)；体现行程进度对偏好的影响                                                                                                                                                     |
| `region_cluster_id`                        | Embedding (cardinality=k, k≈8)            | 从 `business.latitude/longitude` k-means 聚类                     | 查表 embedding, dim=4                                                                                                                 | 同城内区域化推荐；确保 trip plan 的地理紧凑性                                                                                                                                                            |
| **`period_id`** ⭐ NEW                      | Categorical (3 levels)                    | F2 行程 period 标签（早晨 / 中午 / 晚上），由 LLM trip planner 生成            | 3-level embedding, dim=4（morning=0 / afternoon=1 / evening=2）                                                                       | 时段直接影响候选集（早餐 vs 晚餐 cuisine 分布完全不同）；比 `hour_bucket` 粒度更粗、与 F2 UI period 直接对应                                                                                                             |
| **`activity_emb`** ⭐ NEW                   | Numeric vector (32-dim)                   | F2 行程 activity 描述文本（如"参观费城美术馆，欣赏欧洲艺术收藏"），由 LLM trip planner 生成  | sentence-transformer（`sentence-transformers/all-MiniLM-L6-v2`，768-dim）→ PCA / lightweight autoencoder → 32-dim                      | H9——activity 语义与餐厅 category 的对齐信号；32-dim 是 DeepFM concat 维度的合理 trade-off（选 sentence-transformer 而非 LLM embedding 出于 class demo 预算考虑，单次约 ~5ms GPU / ~30-50ms CPU，batch 离线预计算 + 缓存后线上零延迟） |
| **`prior_meals_cuisines`** ⭐ NEW           | Multi-hot vector (top-30 cuisines)        | F2 当前 trip state——同 trip 已选餐厅的 cuisine 列表（跨日 + 同日早于当前时段的已选）    | multi-hot over top-30 cuisine categories（来自 Q3 EDA 的 top-30 列表）                                                                     | 跨日/同日多样性约束的"入模"信号；模型学到"前两餐都意餐 → 这餐应避开意餐"（H10 的隐式监督）；与 MMR 层互补：模型层偏好多样性，MMR 层强制多样性                                                                                                       |

**特征缺失处理规则**：
- 数值型缺失 → 填充全局中位数（不填 0，避免 log-transform 偏移）
- 类别型缺失 → 独立的 `<UNK>` embedding（不共享其他类别的向量）
- `trip_day_index` 缺失（非行程场景）→ 填 0，模型学习"0 = 普通单次访问"语义
- `period_id` 缺失（非 Trip 场景，如 F1 Chat 流）→ 填 `<UNK>` embedding，训练时 F1 样本不传此特征
- `activity_emb` 缺失（F1 场景）→ 填全零向量（32-dim zeros），与 `period_id` 缺失逻辑配套
- `prior_meals_cuisines` 缺失（trip 第一餐）→ 填全零 multi-hot（"尚无已选菜系"）
- **Deploy 阶段新 user_id（Yelp 训练集外）→ 见 §3.3.0.5「User Features 部署时 fallback 速查表」**。训练时模型预留 `<NEW_USER>` OOV 槽位，1-3% 训练样本随机注入该索引以学习冷启动 fallback 表征——这一规则**仅 inference 阶段对 Taste hunter 真实用户生效**，与上述 6 条训练时缺失处理正交。

---

#### §3.3.4 模型方案 + 过拟合/欠拟合检查 (rubric criterion 5)

##### DeepFM 架构

DeepFM（Guo et al., 2017，华为）将 Factorization Machine 的二阶交叉建模能力与 Deep Neural Network 的高阶非线性建模能力**并联**，关键创新在于 FM 端和 DNN 端**共享同一套 embedding**——这意味着 embedding 的梯度同时来自 FM 的内积监督和 DNN 的深层监督，训练效率高于 Wide & Deep 的独立参数。在我们的场景下，FM 端学习 cuisine × hour_bucket、distance × price_level 等二阶交叉，DNN 端学习更复杂的高阶用户-商家-上下文组合。最终输出为 sigmoid 激活的 CTR 估计值，对应"用户喜欢这家餐厅"的概率。

```
                ┌──────────────────────────────────────────────────┐
                │              Sparse Input Features               │
                │  [user_id, business_id, cuisine, hour_bucket,    │
                │   distance_log, price_level, trip_day_index,     │
                │   period_id, activity_emb, prior_meals_cuisines] │
                └───────────────────┬──────────────────────────────┘
                                    │
                        ┌───────────▼───────────┐
                        │  Embedding Lookup      │
                        │  (shared, dim=8 each)  │
                        └───┬───────────────┬───┘
                            │               │
              ┌─────────────▼──┐     ┌──────▼──────────────┐
              │   FM Branch    │     │    DNN Branch        │
              │                │     │                      │
              │  Order-1:      │     │  Flatten embeddings  │
              │  Σ w_i * x_i   │     │  → concat → dense    │
              │                │     │                      │
              │  Order-2:      │     │  FC 256 → ReLU       │
              │  Σ<v_i,v_j>    │     │  FC 128 → ReLU       │
              │  * x_i * x_j   │     │  FC  64 → ReLU       │
              └────────┬───────┘     └───────┬──────────────┘
                       │                     │
                       └─────────┬───────────┘
                                 │  (element-wise add / concat)
                        ┌────────▼────────┐
                        │    Output Layer  │
                        │  Linear → Sigmoid│
                        └────────┬─────────┘
                                 │
                            CTR ∈ [0, 1]
                    ("like" probability for this user-item-context)
```

**参考实现**：`deepctr-torch` 库的 `DeepFM` 类（PyTorch），支持稀疏 + 稠密特征混合输入，与本方案特征设计直接对应。备选：RecBole framework（对超参数管理更友好）。

##### DeepFM 数学形式（Guo et al. 2017）

设输入为 m 个 field 的稀疏向量 $\mathbf{x}$，每个 field $i$ 对应 embedding 向量 $\mathbf{v}_i \in \mathbb{R}^k$（$k$ = embedding_dim）。

**FM Branch**（覆盖 order-1 + order-2 交叉）：

$$\hat{y}_{FM} = w_0 + \sum_{i=1}^{m} w_i x_i + \sum_{i=1}^{m} \sum_{j=i+1}^{m} \langle \mathbf{v}_i, \mathbf{v}_j \rangle \cdot x_i x_j$$

其中 $\langle \mathbf{v}_i, \mathbf{v}_j \rangle = \sum_{l=1}^{k} v_{il} \cdot v_{jl}$。利用等式化简后，order-2 项计算复杂度从 $O(m^2 k)$ 降至 $O(mk)$。

**DNN Branch**（高阶非线性）：

$$a^{(0)} = [\mathbf{v}_1, \mathbf{v}_2, \ldots, \mathbf{v}_m] \quad \text{(flatten)}$$
$$a^{(l)} = \text{ReLU}(W^{(l)} a^{(l-1)} + b^{(l)}), \quad l = 1, 2, 3$$
$$\hat{y}_{DNN} = \sigma(W^{(out)} a^{(3)} + b^{(out)})$$

**共享 Embedding 的关键意义**：FM Branch 和 DNN Branch 使用同一套 $\{\mathbf{v}_i\}$。这意味着反向传播时每个 embedding 向量同时接受来自 FM（二阶内积监督）和 DNN（多层非线性监督）的梯度，使 embedding 编码的语义既保留"相似特征内积大"的 FM 属性，又蕴含 DNN 学到的高阶关系。这是 DeepFM 相比 Wide & Deep 的核心差异（Wide & Deep 的 wide 端和 deep 端参数互相独立）。

**最终输出**（两路求和后 sigmoid）：

$$\hat{y} = \sigma(\hat{y}_{FM} + \hat{y}_{DNN}) \in [0, 1]$$

##### 为何选 DeepFM 而非 Wide & Deep / DCN-v2

Wide & Deep（Google 2016）需要在 Wide 端手工构造交叉特征（例如显式写出"cuisine × hour_bucket"作为输入），工程成本高且需要领域知识指导——适合有海量历史数据 + 专职特征工程师的工业场景。DeepFM 把 Wide 端替换为 FM，由模型自动学习所有 field pair 的二阶交叉，对我们 26 个特征的项目而言更合适。DCN-v2（Wang et al. 2020）是 DeepFM 的有力竞争者，Cross Network 能显式学高阶交叉，在多个 benchmark 上略优于 DeepFM——但 deepctr-torch 两者均有实现，若时间允许可作为 stretch goal 做对比实验（见消融 baseline 表 xDeepFM/DCN-v2 行）。**选择 DeepFM 的首要理由是课程对齐**：Class 3 直接讲 FM，DeepFM 是其 DL 扩展，老师期望看到这条路径。

##### 消融 Baseline 模型

| 模型 | 库 / 实现 | 角色 | 对应 Criterion |
|---|---|---|---|
| **MF（Matrix Factorization）** | `surprise.SVD` 或 `surprise.NMF` | 纯协同过滤基线，无 side feature | Criterion 5 ablation anchor |
| **FM（Factorization Machine）** | `xLearn` (C++ 后端，快) 或 `pyfm` | FM 基线，有 side feature 但无 DNN 高阶项 | Criterion 5 对比 DeepFM |
| **DeepFM（主模型）** | `deepctr-torch` | 主交付 | Criterion 5/6 主角 |
| **xDeepFM / DCN-v2（可选）** | `deepctr-torch` 均有实现 | Stretch goal，高阶交叉对比 | Criterion 5 附加加分项 |

**消融实验结果模板**（待 w7-w8 填充，最终报告 Criterion 5 展示）：

| 模型 | NDCG@10（val） | Recall@10（val） | AUC（val） | vs DeepFM 差距 | 备注 |
|---|---|---|---|---|---|
| MF（Surprise SVD） | TBD | TBD | TBD | — baseline | 纯协同过滤，无 side feature |
| FM（xLearn） | TBD | TBD | TBD | TBD | 有 side feature，无 DNN |
| **DeepFM（主模型）** | **TBD** | **TBD** | **TBD** | — | 主交付，粗体标注 |
| xDeepFM（可选） | TBD | TBD | TBD | TBD | Stretch goal |

> [!note] 消融实验写作要点
>
> Criterion 5 的评分关键在于**展示模型比较的递进逻辑**，不要把三个模型的结果并排扔出来。正确叙事：MF 是"只有协同过滤"的 anchor → FM 加入 side feature 后提升 X → DeepFM 加入 DNN 高阶项后再提升 Y。每一步提升都对应一个"假设得到验证"（H7：DeepFM ≥ MF + 3pp NDCG，H1：cuisine cross feature > median importance）。

##### 单模型双路召回架构：Push 路 + CRS 路 共享 DeepFM 精排（v2.2 最终版）

> [!success] ✅ v2.2 决策（2026-05-06）
>
> 系统采用**单 DeepFM 模型 + 双路召回**架构：
> - **S1 Push 路**（用户进入屏，无 utterance）：走 Two-Tower / DSSM dense retrieval 召回 top-200 → DeepFM 精排
> - **S2/S6 CRS 路**（用户对话/旅行规划，有 utterance）：LLM intent extraction → hard filter 召回 top-100 → 同一个 DeepFM 精排
>
> **不训练独立的搜索模型**。intent 在召回阶段作硬约束（cuisine match / price ≤ X / distance ≤ Y mi / dietary 兼容），不作为 DeepFM 输入特征——这是 Conversational Recommendation (Lei et al. 2020 / Sun & Zhang 2018) 学术范式标准做法。两路 share 同一个 DeepFM weight，单次训练全场景复用。

```
                  用户输入触发
                        │
              ┌─────────┴─────────┐
              │  是否带 utterance? │
              └─────────┬─────────┘
                        │
            ┌───────────┴────────────┐
            ▼                        ▼
    ┌───────────────┐       ┌──────────────────┐
    │ S1 Push 路     │       │ S2/S6 CRS 路      │
    │  (用户进入屏)  │       │ (对话 / 旅行规划) │
    └───────┬───────┘       └────────┬─────────┘
            │                         │
   ┌────────▼────────┐       ┌────────▼──────────┐
   │ Recall: Two-    │       │ Step 1: LLM intent │
   │ Tower DSSM      │       │  extraction        │
   │ ─────────────── │       │  → IntentJSON      │
   │ User Tower MLP  │       │ {cuisine, price,   │
   │ Item Tower MLP  │       │  dietary, dist,    │
   │ cosine + FAISS  │       │  time_window, ...} │
   │ ANN over 13K    │       │                    │
   │ → top-200       │       │ Step 2: Hard filter│
   │                 │       │  SQL-style WHERE   │
   │ (basic geo+time │       │  → top-100         │
   │  pre-filter)    │       │                    │
   └────────┬────────┘       └────────┬──────────┘
            │ 200                     │ 100
            └────────────┬────────────┘
                         ▼
            ┌────────────────────────────┐
            │  Shared DeepFM Ranker      │
            │  (单一训练, 双路复用)       │
            │  ──────────────────────    │
            │  26 features:              │
            │   • User (8)               │
            │   • Item (9)               │
            │   • Context (9, 含 trip)    │
            │  → CTR score per candidate │
            │  → top-50 (Trip) / top-10  │
            └────────────┬───────────────┘
                         │
              ┌──────────┴──────────┐
              │  Trip 场景? (F2)     │
              └──────────┬──────────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
              No (F1)          Yes (F2)
                │                 │
                │       ┌─────────▼──────────┐
                │       │ MMR Re-rank        │
                │       │ + Heuristic 约束   │
                │       │ (§3.3.4.5)         │
                │       │ → top-3 per period │
                │       └─────────┬──────────┘
                │                 │
                └────────┬────────┘
                         ▼
                ┌────────────────────┐
                │ LLM Agent          │
                │ Response Synthesis │
                │ → 前端渲染          │
                └────────────────────┘
```

**双路召回设计的核心价值**：

| 设计点 | 理由 |
|---|---|
| **DeepFM 共享 weight** | 评分对象单一（rubric 关键词「recommender system」），训练 / 评测 / writeup 集中 |
| **召回路径分离** | 不同场景信息源不同：S1 没 query 只能靠 dense retrieval；S2/S6 有 intent 可以 hard filter 高效切窄候选集 |
| **Intent 不作 ranker 特征** | 训练数据（Yelp review）没有 intent 字段，把 intent 注入特征会造成 train-serve skew；做 filter 反而避免这个问题 |
| **Two-Tower 仅用于 S1** | 缩小 Two-Tower 的影响范围——即使来不及训也只影响 push 路降级，CRS 路不受影响 |

**两层（甚至三层）架构的必要性**：Yelp 餐厅子集约 13K（已 city + restaurants 过滤）。S2/S6 走 hard filter 后通常只剩 50-200 候选，DeepFM 直接精排足够快（~50ms）。S1 没 query，需要从 13K 全量做 dense retrieval：单跑 DeepFM 13K forward pass ≈ 1.3 秒，仍可演示但偏慢；Two-Tower + FAISS ANN 在 < 50ms 内出 top-200，再过 DeepFM 精排，毫秒级完成。**Two-Tower 是 S1 的工程加速，不是评分核心**。

> [!warning] Demo 降级策略（更新）
>
> 若 Two-Tower 训练时间超预算（5/19 决策点），**S1 路降级为"地理 + 时间硬过滤"**（仅保留同 metro + 当前营业时段的商家，约 300-1500 候选），DeepFM 直接精排——延迟从 50ms 升到 100-300ms 仍可接受。**S2/S6 路完全不受影响**，因为它本来就走 LLM intent + hard filter，不依赖 Two-Tower。即使 Two-Tower 全部砍掉，3/3 评分场景照常 demo。

##### 过拟合检查清单

| 检查项 | 触发条件 | 处置方式 |
|---|---|---|
| Train AUC vs Val AUC gap | gap > 0.05 = 红灯；0.03-0.05 = 黄灯 | 增大 L2 正则 / 降 embedding dim / 增 dropout |
| Learning curve divergence | Val loss 在 epoch 5 后上升（train loss 仍下降） | Early stopping（patience=3）；检查 negative sampling ratio |
| Embedding norm | 某个 embedding 向量 L2 norm > 5.0 | 添加 embedding norm regularization（max_norm 参数）|
| Long-tail item overfit | 热门商家 Recall 远高于长尾商家 | 分层评估：按 item popularity 分 4 bucket，分别报告 Recall |
| Feature leakage check | Val AUC 异常高（> 0.85） | 检查 train/val split 是否时序正确；检查 user_id 是否泄露 |

##### 欠拟合检查清单

| 检查项 | 触发条件 | 处置方式 |
|---|---|---|
| Val AUC plateau 过低 | Val AUC < 0.65 且 training loss 不下降 | 增大 embedding dim（4→8→16→32）；增加 DNN 层数 |
| FM vs DeepFM 无差异 | NDCG@10 差距 < 0.005 | 检查 DNN 路径是否正确接入梯度；检查特征是否做了 sparse hash |
| Residual analysis | 某类 cuisine 的 predicted score 系统性偏低 | 检查该类 cuisine 的训练样本数；考虑 per-category calibration |

---

#### §3.3.4.5 Trip 场景的多样性重排 (MMR + Heuristic Constraint Layer)

> [!note] v2 新增节
>
> 本节针对 F2 Trip Plan 场景中"每段返回 top-3 候选"的新需求，规格化 MMR 重排算法和启发式约束层。F1 Chat 场景不涉及本节。

##### 问题陈述

Figma Make 原型审计（§4，TripPlan.tsx）揭示：F2 每个 period（早晨 / 中午 / 晚上）需向用户展示 **3 个候选餐厅**，用户用 ‹ › 按钮切换，确保切换有意义（而非同质化选项）。纯 DeepFM score-greedy 排序在实测中容易输出 3 家同 cuisine / 相似价位的餐厅（H10 假设的反面场景）——尤其是某 cuisine 在 activity 语义上高度匹配时，前 3 名可能全是意餐或全是寿司。单纯依赖 `prior_meals_cuisines` 模型特征不足以保证 **per-period top-3 的即时多样性**，需要在精排后加一个确定性重排层。

##### 解法 — MMR (Maximal Marginal Relevance)

MMR（Carbonell & Goldstein, 1998）的经典思路：每次选下一个候选时，在"得分高"和"与已选候选不相似"之间取 trade-off。标准重排公式：

$$\text{MMR}(d_i) = \lambda \cdot \text{Score}(d_i) - (1-\lambda) \cdot \max_{d_j \in S} \text{sim}(d_i, d_j)$$

其中：
- $\text{Score}(d_i)$ = DeepFM 输出的 ranking score（sigmoid CTR 估计，∈ [0,1]）
- $\text{sim}(d_i, d_j)$ = 候选 $d_i$ 与已选集合中 $d_j$ 的联合相似度：$\text{sim} = \text{cosine}(\mathbf{m}_i, \mathbf{m}_j)$，其中 $\mathbf{m}$ 为以下三维属性的 multi-hot 拼接向量：cuisine category（top-30 one-hot）+ price_level（4-dim one-hot）+ region_cluster_id（k-dim one-hot）
- $S$ = 已选候选集合（初始为空，每轮迭代后更新）
- $\lambda \in [0.5, 0.8]$ — relevance vs diversity 的 trade-off 参数（扫描范围见 §3.3.5）

**迭代算法**（从 DeepFM top-50 中选 3）：

```
input:  candidates = DeepFM top-50 for (user, period, activity)
output: final_top3 = []

S = []   # 已选集合
for k in range(3):
    best = argmax over c in (candidates \ S):
        λ * Score(c) - (1-λ) * max(sim(c, s) for s in S)
        # 当 S 为空时，第一轮退化为纯 Score 排序
    final_top3.append(best)
    S.append(best)

return final_top3
```

时间复杂度：$O(|C|^2)$，其中 $|C|=50$，per-period 运行时间 < 1ms，可忽略不计。

##### 启发式约束层（post-MMR）

MMR 完成 top-3 选择后，通过以下硬规则进行二次校验或替换：

| 约束类型 | 规则内容 | 强度 | 实装状态 |
|---|---|---|---|
| **Day-level cuisine 去重** | 同 day 三个 period 之间，不允许同一 cuisine 出现超过 2 次（如早午晚都是意餐 → 强制替换晚餐候选中的意餐选项） | 强制（hard filter） | ✅ demo 实装 |
| **同段地理紧凑性** | per-period 3 候选的 lat/lon 均在 activity 描述地点 ±2 mi 半径内（使用 Haversine + business coordinates） | 强制（hard filter） | ✅ demo 实装 |
| **Trip-level cuisine 跨日多样性** | 同 trip 内同一 cuisine 不超过 2 餐（跨 day 统计） | 软约束（best-effort，MMR + prior_meals_cuisines 模型特征共同实现） | ⏳ Future Work |
| **价位 distribution** | 同 day 三餐不全 $$$ 或全 $（避免极端预算天） | 软约束 | ⏳ Future Work |

> [!success] ✅ 决策 — class demo 实装范围
>
> 时间紧张，demo 仅实装 MMR 重排 + 两个 day-level 强制约束（cuisine 去重 + 地理紧凑性）。Trip-level 跨日 cuisine 多样性 + 价位 distribution 作为 §6 Future Work 列项。MMR 已能保证 per-period top-3 的即时多样性（H10 验证目标：cuisine diversity ≥ 0.66）；day-level cuisine 约束处理跨段退化边界情况。

##### 端到端架构（Trip 场景）

```
  用户发起 Trip Plan 请求
  └─ "我要去 Philadelphia 玩 3 天"
         │
  ┌──────▼──────────────────────────────────────────┐
  │  LLM: Itinerary Parsing + Activity Generator    │
  │  → destination / days / regions                 │
  │  → 9 activity 描述（3 days × 3 periods）        │
  └──────┬──────────────────────────────────────────┘
         │ 对每个 (day, period) 循环执行以下流程
         │
  ┌──────▼──────────────────────────────────────────┐
  │  Two-Tower Retrieval                            │
  │  输入: user_ctx + period_id + activity_emb      │
  │  输出: top-200 candidates                       │
  └──────┬──────────────────────────────────────────┘
         │ 200 candidates
  ┌──────▼──────────────────────────────────────────┐
  │  DeepFM Ranker                                  │
  │  输入: 26-feature vector (含 activity_emb,      │
  │         period_id, prior_meals_cuisines)        │
  │  输出: CTR score per candidate → top-50         │
  └──────┬──────────────────────────────────────────┘
         │ top-50
  ┌──────▼──────────────────────────────────────────┐
  │  MMR Re-rank (§3.3.4.5)                        │
  │  λ ∈ [0.5, 0.8]，iterative top-3 selection    │
  │  sim = cosine(cuisine + price + region mhot)   │
  │  输出: top-3 (diversity-aware)                 │
  └──────┬──────────────────────────────────────────┘
         │ top-3
  ┌──────▼──────────────────────────────────────────┐
  │  Heuristic Constraint Layer                     │
  │  ✅ Day-level cuisine 去重（硬过滤）             │
  │  ✅ 地理紧凑性 ±2 mi（硬过滤）                  │
  │  ⏳ Trip-level / 价位（Future Work）            │
  └──────┬──────────────────────────────────────────┘
         │ final top-3 per period
  ┌──────▼──────────────────────────────────────────┐
  │  前端 F2 TripPlanRender                         │
  │  period 内 3 候选 ‹ › 切换 + indicator dots    │
  └─────────────────────────────────────────────────┘
```

---

#### §3.3.5 选型 + 正则化 (rubric criterion 6)

> [!success] ✅ 决策：选用 DeepFM — deepctr-torch 实现
>
> 理由：（1）直接命中教授 rubric "hybrid or factorization machine"；（2）deepctr-torch 原生支持稀疏特征 + embedding，与我们的 26 个 feature schema 直接对应，无需手写 forward pass；（3）在 Yelp 量级（~7M reviews 下采样至 1M）单卡 T4 训练时间可控（约 1h/epoch）。

##### 正则化扫描协议

所有超参通过 **grid search**（不用 Bayesian，保持 reproducible + 简单可汇报）在 val NDCG@10 上选择，每组配置跑 10 个 epoch，选最优 val checkpoint。

| 扫描参数 | 扫描范围 | 扫描粒度 | 选定依据 |
|---|---|---|---|
| `embedding_dim` | {4, 8, 16, 32} | 4 个值，依次增大 | val NDCG@10 最高且 train-val gap < 0.04 |
| `dropout` (DNN 层) | {0.1, 0.2, 0.3, 0.4, 0.5} | 5 个值 | val NDCG@10 最高；dropout > 0.4 时通常欠拟合 |
| `L2` weight (embedding) | {1e-5, 1e-4, 5e-4, 1e-3} | 4 个值，log scale | val AUC 最高且 embedding norm 分布合理 |
| `negative_sampling_ratio` | {1:1, 1:2, 1:4} | 3 个值 | Precision@10 vs Recall@10 的 tradeoff |
| **`MMR λ`** ⭐ NEW | {0.5, 0.6, 0.7, 0.8} | 4 个值（Trip 场景专用） | per-period top-3 cuisine diversity ≥ 0.66 且 NDCG@3 下降 < 0.005（H10 验证标准）；λ 越大越偏 relevance，越小越偏 diversity |
| `early_stopping` patience | 3 epoch（固定不扫） | — | 防止 epoch 数无效延长训练时间 |
| `batch_size` | 1024（固定）| — | 显存利用率 ~80%（T4 16GB），不扫 |
| `learning_rate` | 1e-3（固定，Adam）| — | 推荐系统 Adam 默认值，不扫 |

##### 最终配置表（待 w8 实验填充）

| 超参 | 候选值 | 选定值（TBD） | val NDCG@10（TBD） | 备注 |
|---|---|---|---|---|
| `embedding_dim` | {4, 8, 16, 32} | TBD | TBD | 预期 8 或 16 最优 |
| `dropout` | {0.1, 0.2, 0.3, 0.4, 0.5} | TBD | TBD | 预期 0.2-0.3 区间 |
| `L2` | {1e-5, 1e-4, 5e-4, 1e-3} | TBD | TBD | — |
| `negative_sampling_ratio` | {1:1, 1:2, 1:4} | TBD | TBD | — |
| **`MMR λ`** | {0.5, 0.6, 0.7, 0.8} | TBD | TBD (NDCG@3 + diversity) | Trip 场景评测；预期 0.6-0.7 在多样性和质量间平衡 |

> [!note] 汇报建议
>
> Criterion 6 要求写清楚"如何做 model selection"，不需要最优结果本身——即使 TBD 都填完，**超参扫描协议的完整性本身就是得分点**。Bose 想看到的是"你知道正则化有哪些 knob、怎么系统地调"。把上面这张表放进最终报告，配一张 val NDCG@10 vs dropout / L2 的折线图 + 一张 MMR λ vs cuisine diversity / NDCG@3 的双轴折线图，Criterion 6 稳 4/5 分。

##### 正则化原理 + 数学形式

**L2 正则化**。完整训练目标为：

$$\mathcal{L}_{total} = \mathcal{L}_{BCE} + \lambda \|\mathbf{V}\|_F^2$$

其中 $\mathbf{V} = [\mathbf{v}_1, \ldots, \mathbf{v}_m]$ 为所有 embedding 矩阵，$\lambda$ 为 L2 weight（扫描范围 1e-5 → 1e-3）。L2 正则等价于给 embedding 向量施加 Gaussian prior $p(\mathbf{v}_i) \sim \mathcal{N}(0, \sigma^2)$，使稀疏 ID 的 embedding 向 0 收缩，防止高 cardinality 特征（user_id ~2M / business_id ~150K）对少量训练样本过拟合。embedding_dim 越大，$\|\mathbf{V}\|_F^2$ 越大，L2 压力越强——因此高维 embedding 通常需要更大的 $\lambda$。

**Dropout**。在 DNN 每个隐层的 forward pass 中：

$$h_l' = h_l \odot \frac{\text{Bernoulli}(1-p)}{1-p}$$

除以 $(1-p)$ 是 inverted dropout 的标准做法：train 时 scale up 保留的激活，使 test 时（$p=0$，即不 dropout）无需修改权重，期望输出不变。dropout 本质是对 $2^n$（$n$=神经元数）个子网络的隐式集成，强迫每个神经元不依赖特定伙伴，是过拟合的有效抑制手段。

**Early Stopping**。相比 AUC（关注全局 pair 排序），NDCG@10 仅关注 top-10 位置的质量，与生产推荐场景直接对齐（用户只看前几个结果）。用 NDCG@10 作为 stopping criterion，可以避免"AUC 仍在涨但 top-10 quality 已饱和"的无效训练。

$$\text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}, \quad \text{DCG@K} = \sum_{i=1}^{K} \frac{2^{r_i} - 1}{\log_2(i+1)}$$

其中 $r_i$ 为第 $i$ 位置的 relevance（本项目中 = binary label 0/1），IDCG@K 为理想排序的 DCG 上界。

---

#### §3.3.6 训练 Protocol

##### 数据集划分

| 集合 | 划分方式 | 占比 | 用途 |
|---|---|---|---|
| Train | review date < P70 分位（时序最早 70%） | 70% | 模型参数更新 |
| Validation | review date 在 P70-P80 区间 | 10% | 超参选择 / early stopping |
| Test | review date > P80 分位（最新 20%） | 20% | 最终评测，一次性使用 |

> [!warning] 为什么用时序划分而非随机划分
>
> 随机划分会让 validation/test 集包含训练期间的交互信息（同一 user-item pair 的历史 review 可能出现在 train 中），导致 AUC 虚高（时序泄露 temporal leakage）。时序划分模拟生产部署场景：模型在历史数据上训练，在未来时间点做推断。这是评测离线 ranking 模型的工业标准做法。

**Positive label 定义**：`rating ≥ 4.0` → label=1（"like"），`rating < 4.0` → label=0。Yelp 评分高度右偏（大量 5 星），4.0 为合理的高满意度分割点，与 H3 的 prior 假设一致。

##### 损失函数与评测指标

**训练 loss — Binary Cross-Entropy**：

$$\mathcal{L}_{BCE} = -\frac{1}{N}\sum_{i=1}^{N} \bigl[y_i \log \hat{y}_i + (1 - y_i)\log(1 - \hat{y}_i)\bigr]$$

其中 $N$ 为 batch 内样本数（batch_size=1024），$y_i \in \{0, 1\}$ 为 label，$\hat{y}_i \in [0,1]$ 为 DeepFM sigmoid 输出。

**离线评测指标**（报告 Criterion 7 用）：

| 指标 | 公式/说明 | 用途 |
|---|---|---|
| AUC | ROC 曲线下面积；pair-wise ranking 指标 | 模型整体区分能力；主要用于 train/val gap 监控 |
| NDCG@10 | 见 §3.3.5 公式；top-10 排序质量 | 主指标，用于超参选择 + 模型对比 |
| Recall@10 | 测试集中 positive item 有多少出现在预测 top-10 内 | 衡量召回能力，对冷启动分析有用 |
| Precision@10 | top-10 预测中有多少是 positive | 与 Recall@10 共同构成 trade-off 视角 |
| **NDCG@3** ⭐ NEW | top-3 排序质量（Trip 场景专用） | H10 验证 + MMR λ 选择的主要评测指标 |
| **Per-period cuisine diversity** ⭐ NEW | per-period top-3 内 unique cuisine 数 / 3；均值 ≥ 0.66 | H9/H10 验证；与 NDCG@3 共同评估 MMR 效果 |

全部指标在 test 集上**只计算一次**（最终报告用），val 集用于超参选择（Criterion 6）。

##### 训练配置

| 配置项 | 值 | 备注 |
|---|---|---|
| Loss function | Binary Cross-Entropy (BCE) | 二分类 like/dislike |
| Optimizer | Adam, lr=1e-3, β1=0.9, β2=0.999 | 推荐系统默认 |
| Batch size | 1024 | T4 16GB 显存利用率 ~80% |
| Epochs | 最多 20，early stopping patience=3 | 实际预计 8-12 epoch 收敛 |
| Negative sampling | 每个正样本采样 N 个负样本（N=1 default，sweep 包含 1:2 / 1:4） | 从同城商家中随机采样负样本 |
| 数据规模 | 从 Yelp ~7M reviews 中按 target 3 城市 + 时序过滤，预计 1M 样本 | 单卡训练约 1h/epoch |

##### 硬件与日志

| 项目 | 规格 |
|---|---|
| 训练硬件 | Google Colab T4（free tier，16GB VRAM）或本地 MacBook M3 Pro（MPS backend，统一内存 36GB） |
| 预估训练时间 | 1M 样本 × 1 epoch ≈ 45-90 min（T4）；M3 Pro 约慢 2× 但可后台跑 |
| 日志方案 | Option A：W&B（Weights & Biases free tier，自动绘图）；Option B：CSV log → matplotlib 手绘 learning curve + NDCG@10 折线图 |
| 实验复现 | 固定 `random_seed=42`；所有配置写入 `config.yaml`，训练脚本从 yaml 读取；git tag 每个 checkpoint 对应的 commit |
| 输出产物 | `model_deepfm.pt`（PyTorch state dict）+ `feature_spec.json`（特征编码 schema）+ `metrics_summary.csv` |

---

#### §3.3.7 已知风险与限制

| # | 风险/限制 | 影响范围 | 缓解策略 |
|---|---|---|---|
| L1 | **Yelp 数据无原生 trip-context 标签**。H5 的行程 context features（`trip_day_index` / `region_cluster_id`）依赖将同一用户在 ±3 天内的评论聚合为"伪行程 session"，这是人工合成，不是真实 trip 意图。 | §3.3.1 H5 假设的验证可信度 | 在报告 Limitation 段明确说明合成方法；NDCG gain < 0.003 时将 H5 降级为"未能验证"而非"假设错误"；真实行程数据可走 Foursquare / Google Timeline API（Future Work） |
| L2 | **Yelp 地理覆盖不均衡**。Yelp Open Dataset 在 Philadelphia + Tucson + Tampa 以外的城市数据稀疏，直接影响 Two-Tower 召回质量和 DeepFM 的城市 embedding 学习。 | Demo 覆盖城市范围 | Demo 硬限制 3 城市；在 EDA 中可视化各城市数据量，若某城市 < 5K 商家则移出 demo 城市列表 |
| L3 | **Two-Tower 训练进度风险（仅影响 S1 路径）**。v2.2 双路召回架构下，Two-Tower 仅用于 S1 push 路（用户进入屏无 utterance）。若 5/19 决策点 Two-Tower 未跑通，S1 降级为"地理+时间硬过滤"（同 metro + 当前营业时段，~300-1500 候选）DeepFM 直精排，延迟 100-300ms 仍可演示。**S2/S6 CRS 路完全不受影响**——它本来走 LLM intent + hard filter，不依赖 Two-Tower。 | 仅 S1 demo 延迟 / 视觉流畅度 | Two-Tower 列入 P2（stretch），不影响评分关键路径；S2/S6 demo 质量保底；报告写"双路召回架构已设计，S1 dense retrieval 待完成（Future Work）" |
| L4 | **Photos.json（5GB）下载未决定**。F1 卡片需要餐厅图片；若不下载 photos.json，UI 全程显示 `#DCDDE8` placeholder，影响演示视觉效果，但不影响任何评分维度。 | Demo 视觉质量（非评分） | 待评审决定；若决定不下载，EDA 中用 photo_count 元数据字段估算覆盖率（L2 EDA 问题 7 已预设）；UI placeholder 已在 figma_make_prompt.md 中设计好 |
| L5 | **单 GPU 训练时间 vs 超参扫描**。embedding_dim × dropout × L2 的全量 grid search 共 4×5×4=80 组配置，每组 ~1h，总计 80h，超出可用算力。 | Criterion 6 超参扫描完整性 | 分两阶段：先对 `embedding_dim` 做 4 点扫描（4h）确定维度，再固定维度对 dropout × L2 做 5×4=20 点扫描（20h）；总计 ~24h，可接受。或用 Colab Pro 多 session 并行（每 session 一组配置） |
| L6 | **Rating ≥ 4.0 作为 positive label 的分类假设**。Yelp 评分高度右偏（约 70% review 为 4-5 星），正负样本比约 7:3，不严重；但若改为 ≥ 4.5，正负比变为约 4:6，训练分布改变。 | H7 假设的边界条件 | 固定 ≥ 4.0 作为 positive 定义，并在报告中写明；sensitivity analysis 可在 Future Work 中提：不同 threshold（4.0 / 4.5 / implicit feedback）对 NDCG 的影响 |
| **L7** ⭐ NEW | **`activity_emb` pipeline 依赖 sentence-transformer，需要离线预计算**。Demo 中只有 27 条 activity 候选库（3 days × 3 periods × 3 candidates）；离线预算几乎为 0。但线上场景 activity 是 LLM **实时生成**的文本，每次生成后需即时调用 sentence-transformer 编码，引入额外 ~30-50ms 延迟（本地 CPU inference；GPU 可压缩至 ~5ms）。 | H9 验证可行性；线上延迟预算 | 缓解：(a) 对已知 activity 模板库离线预计算 + 缓存 embedding；(b) LLM 生成 activity 后批量调用 sentence-transformer（一次 trip 生成 9 条 activity，batch inference ~80ms，可接受）；(c) 若延迟不可接受，退化为 activity 关键词抽取 → bag-of-words 后查预计算 category 近邻 |
| **L8** ⭐ NEW | **MMR λ 参数灵敏度未在 v1 grid search 中**。不同 λ 值对 per-period cuisine diversity 和 NDCG@3 的影响尚未实测；λ 选错可能导致"too greedy"（lambda=0.8，top-3 仍同 cuisine）或"too diverse"（lambda=0.5，NDCG@3 显著下降）。 | H10 假设的验证可信度；F2 demo 候选质量 | 新增 λ sweep：λ ∈ {0.5, 0.6, 0.7, 0.8}，在 demo 的 27 餐厅 × 9 period 上评测 per-period top-3 cuisine diversity 和 NDCG@3 变化；选 diversity ≥ 0.66 且 NDCG@3 下降最小的 λ 作为 demo 默认值。详见 §3.3.5 超参扫描表 MMR λ 行。 |

---

#### §3.3 节内交叉引用速查

本节各子段向 PRD 其他章节输出的接口：

| 本节输出 | 下游消费方 | 说明 |
|---|---|---|
| §3.3.1 假设表（H1-H10） | §3.4 评测系统 | 每条假设对应一个离线验证实验；评测系统的 case 设计要对齐假设；H9/H10 对应 §3.4 中 per-period diversity + activity-restaurant semantic match 两个新维度 |
| §3.3.1 H9/H10 | §3.4 新增评测维度 | 对应 figma_make_audit §8 中的 "Activity-Restaurant semantic match" + "Per-period candidate diversity" 两个新度量 |
| §3.3.2 EDA 结论（Zimeng+Cindy）| §3.3.3 特征工程 | cold-start 比例（Q6）决定内容特征权重；类目分布（Q3）决定 multi-hot 维度；**Q11 activity text 可用性结论** 决定 `activity_emb` 的计算来源 |
| §3.3.3 特征表（26 个特征） | §3.3.4 模型方案 | DeepFM 的 input schema 直接来自本表；`feature_spec.json` 在 §3.3.6 中输出；`activity_emb` 的维度（32-dim）决定 sentence-transformer PCA 压缩目标 |
| §3.3.4.5 MMR 重排算法 | §3.3.5 超参 / §3.3.7 L8 | MMR λ 的扫描范围 + 评测标准在 §3.3.5 定义；实际风险和延迟分析在 §3.3.7 L7/L8 |
| §3.3.5 最终配置表（含 MMR λ 选定值） | §3.4 评测系统 / 报告 Criterion 6 | 选定配置 = 最终上报 Bose 的模型规格；MMR λ 选定值配套 diversity 评测结果展示 |
| §3.3.6 训练 Protocol | §5 实施计划 | 每 epoch 1h 的估算是排期的基础；checkpoint 产物是 demo 部署的输入 |
| §3.3.7 风险表（L1-L8） | §6 开放问题 / Future Work | L1（trip context 合成）+ L2（城市覆盖）直接对应 Criterion 8 Future Work 素材；**L7（activity embedding pipeline）+ L8（MMR λ 灵敏度）** 为 v2 新增 Future Work 素材 |

<!-- §3.3 v2 完成 · Sib C2 · 2026-05-04 -->
