### §3.4 评测系统

> **归属 Rubric 项**：Criterion 7 — Results + Learnings（5分）
> **Owner**：Haobo Yang · 本节覆盖 Layer A（离线模型评测）+ Layer B（Agent 层评测）+ Layer C（课程 rubric 自检）三层
> **状态**：结构 + 目标值 ✅ 完成；实际数字 ⏳ w8 末填入

> [!warning] v2 Update Note — 2026-05-04
>
> 本版本（v2）在 v1 基础上增补了 trip plan 流的全套评测规格，依据 `figma_make_audit.md` Section 8 的 ground truth。主要变化：§3.4.1 新增 4 个 trip-specific 离线指标（Trip Diversity / Geographic Compactness / Activity-Restaurant Semantic Match / Per-Period Candidate Diversity）；§3.4.2 新增 C9-C12 四个 trip 场景测试样例；§3.4.4 新增 Itinerary Parsing / Activity 文案合理性 / modify_trip_slot 三个 Agent 评测子维度；新增 §3.4.4b "Trip 场景独立评测协议"子节；§3.4.5 / §3.4.6 / §3.4.7 / §3.4.8 各有小幅扩充。v1 的全部 9 个子节结构完整保留，所有原有内容原样保持。

---

#### §3.4.0 评测目标

本项目评测体系分三个层次。**Layer A（模型层）** 在 Yelp Open Dataset 的离线 held-out split 上运行标准推荐评测指标（AUC、NDCG@10、Recall@10 等），是 Rubric Criterion 7 "Results" 的主要证据来源；所有数字在 w8 末 DeepFM 训练完成后回填，确保"比较有 baseline"的要求被满足。**Layer B（Agent 层）** 评测 LLM agent 包装层的意图提取准确率、工具分发正确率、响应合成质量与忠实度，保证"底层推荐器打出好分数"不被 agent 层噪声掩盖。**Layer C（课程 rubric 自检）** 是一张 8-criterion 进度表，用于在交稿前一周（5/22）做结构性 gap check，保证所有评分维度都有对应的 PRD 章节和可交付证据。三层共同构成可防御的评测叙事：从模型质量到端到端体验，从离线指标到课程评分点，全链路覆盖。

v2 在此基础上补充了 **Trip 场景独立评测协议**（§3.4.4b），专门度量 F1→F2 全链路的 trip plan 质量——包括跨日多样性、地理紧凑性、活动语义匹配、段内候选多样性四个维度——确保 Criterion 7 Results 中 trip plan 的 lift 有数字支撑，而不只是演示截图。

> [!success] 决策：thumbs-up / thumbs-down 是未来在线评测的数据入口
>
> F1 主屏 message-action 图标行（copy · thumbs-up · thumbs-down · refresh-ccw，见 `figma_make_prompt.md` §F1 §2d）中的点赞/踩按钮**不是纯 UX 装饰**——它们是架构上预留的在线用户反馈采集点。本次 Demo 不做 feedback 写入（out of scope），但接口槽位已在前端占住，未来接后端即可开启 RLHF 循环。在 Criterion 8 Future Work 中引用这一点。

---

#### §3.4.1 离线评测维度（Layer A）

> 评测粒度：全量 Yelp test split（90/10 random user split）。以下指标均在 held-out test 集上计算；训练集/验证集数字**不得**混入结果汇报（见 §3.4.8 陷阱清单）。

| 维度 | 公式 | 度量目标 | 用途 | 测量频率 |
|---|---|---|---|---|
| **AUC** | $\frac{\sum_{(u,i^+,i^-)} \mathbf{1}[\hat{r}_{ui^+} > \hat{r}_{ui^-}]}{|\text{pairs}|}$ | ≥ 0.75 | pairwise 排序质量；主要 baseline 对比指标 | 每次训练后，test split 一次 |
| **NDCG@10** | $\frac{1}{|U|}\sum_u \frac{\sum_{k=1}^{10} \frac{\text{rel}(k)}{\log_2(k+1)}}{\text{IDCG}@10}$ | ≥ 0.30 | top-K 位置折扣后的相关性；Rubric 7 核心汇报指标 | 每次训练后 |
| **Recall@10** | $\frac{1}{|U|}\sum_u \frac{|\hat{S}_u^{10} \cap R_u|}{|R_u|}$ | ≥ 0.20 | 真正例的 top-10 覆盖率；诊断漏召回 | 每次训练后 |
| **Precision@10** | $\frac{1}{|U|}\sum_u \frac{|\hat{S}_u^{10} \cap R_u|}{10}$ | ≥ 0.15 | top-10 推荐中相关结果密度 | 每次训练后 |
| **Coverage@10** | $\frac{|\bigcup_u \hat{S}_u^{10}|}{|I|}$ | ≥ 30% | 全目录中被推荐的商家占比；暴露长尾覆盖能力 | 每次训练后 |
| **Popularity Bias (Gini)** | 对所有商家的 impression 频次做 Gini 系数 | < 0.6（越低越平均） | 诊断模型是否严重扎堆热门；辅助 Criterion 7 fairness 讨论 | 每次训练后 |
| **Long-tail Recall@10** | 同 Recall@10，但 $R_u$ 限定为按 review 数排名后 80% 的"冷门"商家 | ≥ Recall@10 / 2 | 衡量 DeepFM 能否拉起冷门商家；非热门内容召回 | 每次训练后 |
| **Cold-start AUC** | AUC 限定在 review 数 < 5 的用户子集 | ≥ 0.65 | 冷启动场景排序能力；对 H3 假设的直接验证 | 每次训练后（cold-start 子集独立跑） |
| **Cross-city 泛化 AUC** | 在 Philadelphia review 上训练，在 Tampa held-out test 上测试的 AUC | AUC 降幅 < 5pp vs 同城 | 衡量城市迁移能力；支持 trip-context 设计合理性 | 一次性（跨城市实验） |

> **— Trip-specific Metrics（v2 新增）—** 以下 4 个维度专用于 F2 Trip Plan 场景评测，与 chat-flow 指标相互独立，须在报告中单独成节汇报（见 §3.4.8 陷阱清单）。

| 维度 | 公式 | 度量目标 | 用途 | 测量频率 |
|---|---|---|---|---|
| **Trip Diversity** (Simpson's index inverse) | $1 - \sum_c \left(\frac{n_c}{N}\right)^2$，其中 $n_c$ = 同 cuisine 餐厅数，$N$ = trip 总餐厅数 | ≥ 0.7 | 跨日跨段 cuisine 多样性；验证 Diversity Re-rank 启发式层的有效性 | 每次 trip plan 生成后；§3.4.4b 协议中对 12 个手工 case 全量计算 |
| **Geographic Compactness** | 平均 day 内三餐（morning / lunch / dinner 中选定餐厅）pairwise Haversine 距离（km） | < 5 km（Philadelphia / Tampa 场景） | 同日紧凑度；验证地理聚类启发式层的有效性 | 同上 |
| **Activity-Restaurant Semantic Match** | $\frac{1}{N_{\text{period}}} \sum_{\text{period}} \cos(\text{activity\_emb}, \text{category\_emb})$ | ≥ 0.4 | H9 — 活动文案与推荐餐厅类别的语义对齐程度；`activity_emb` 由 sentence-transformer 生成，`category_emb` 由 cuisine multi-hot → embedding 得到 | 同上 |
| **Per-Period Candidate Diversity** | 平均每 period top-3 内 unique cuisine count / 3 | ≥ 0.66（即 top-3 平均至少 2 个不同 cuisine） | H10 — MMR 重排有效性；确保 ‹ › 候选切换有真实选择价值 | 同上 |

> [!info] 负采样协议
>
> 对每条正例（用户评分 ≥ 4 的 (user, business) 对），在同城内随机采样 4 条未访问商家作为负例。负采样比 1:4 在 DeepFM 训练时固定；AUC 计算时同样基于此 pair 构造方式，确保训练与评测协议一致。Trip-specific metrics 不依赖 held-out pair，而是在手工构造的 12 个 trip case 上计算（见 §3.4.4b）。

---

#### §3.4.2 评测样例集

> [!warning] 状态说明：实际 top-3 列在 w8 末跑完 DeepFM 后回填，当前均为 `[TBD]`。C9-C12 为 v2 新增的 trip 场景样例。

| Case ID | user_ctx + intent | 期望 top-3 / 期望行为 | 实际 (TBD) | 通过否 |
|---|---|---|---|---|
| **C1** | Power user，LA，50+ 条 review，brunch 偏好，价位 $$，周末 10am | Moonlark's Dinette · Sqirl · Cofax | [TBD] | [TBD] |
| **C2** | Cold-start，Tampa tourist，0 条 review，晚餐，无明确偏好 | 热门 dim sum · Italian bistro · steakhouse（按 Tampa 周榜） | [TBD] | [TBD] |
| **C3** | 素食 + 无葱蒜饮食限制，SF，午餐，价位 $$- | Greens Restaurant · Shizen · Loving Hut | [TBD] | [TBD] |
| **C4** | Trip context：Philadelphia 行程第 3 天，前 2 天均吃意餐，当天晚餐 | 非意餐（cuisine 多样性惩罚生效）；期望日式/墨西哥/美式 top-3 | [TBD] | [TBD] |
| **C5** | 距离约束 < 1 mi，Redmond 郊区，任意时段 | 全部 top-3 距用户当前坐标 ≤ 1 mi（地理过滤生效） | [TBD] | [TBD] |
| **C6** | 小众需求：Ethiopian 料理，$$，Tucson | 正常返回 Ethiopian 候选（长尾 recall 非零，C6 与 §3.4.1 Long-tail Recall 联动） | [TBD] | [TBD] |
| **C7** | 时间窗口错配：用户早上 10am 问晚餐推荐（dinner at 10am） | Agent 不报错；降级返回早午餐推荐 + 提示"晚餐窗口从下午 5 点开始，先看看早午餐？" | [TBD] | [TBD] |
| **C8** | 跨城市：用户 Philadelphia 历史 review 丰富，当前位于 Tampa | Top-3 均为 Tampa 本地商家（不把 Philadelphia 历史 echo 成 Tampa 推荐）；city context override 生效 | [TBD] | [TBD] |

> **— Trip 场景样例（v2 新增 C9-C12）—**

| Case ID | user_ctx + intent | 期望行为 | 实际 (TBD) | 通过否 |
|---|---|---|---|---|
| **C9** | 全程素食 trip plan：用户输入 "我想去 Philadelphia 玩 3 天，全部素食" | 27 个候选（3 days × 3 periods × 3）全部 dietary 标注 vegetarian/vegan；Trip Diversity ≥ 0.7；至少 5 种不同 cuisine 出现在候选中 | [TBD] | [TBD] |
| **C10** | F2 in-trip modify：用户在 F2 input bar 输入 "把 day 2 lunch 换成日料" | 仅 (day=2, period=lunch) 的 3 个候选更换为 Japanese cuisine；其他 24 个 slot 的候选完全不变；reply_text 简短确认（≤ 30 字）；modify_trip_slot tool 被正确调用 | [TBD] | [TBD] |
| **C11** | F1.1 ‹ › 兄弟切换连贯性：用户在 F1.1 bottom nav 连续点击 ›（3次）再点 ‹（1次） | counter pill 显示 N of M 与 list index 同步无 off-by-one；位于第 1 张时 ‹ 按钮处于 disabled 态；位于末位时 › 按钮处于 disabled 态；每张新 detail 包含合理的 ai_overview（非 placeholder 空字符串） | [TBD] | [TBD] |
| **C12** | F2 export markdown 字段完整性：用户点击 F2 greeting block 右侧"导出"pill | 导出文本包含所有 9 段（3 days × 3 periods）的 activity 描述 + 每段 1 个选中 restaurant 名 + cuisine + address + reason chip 文案；格式可机器解析（Markdown 结构，每段有分隔符） | [TBD] | [TBD] |

> **评测判定标准**：C1/C2/C3/C6 以 DCG@3 ≥ 50% IDCG@3 为通过；C4/C5/C8 以约束条件满足率 = 100% 为通过（硬约束，任一违反即 fail）；C7 以 agent 不抛异常 + 返回有效替代推荐为通过；C9 以 dietary 满足率 = 100% + diversity ≥ 0.7 + cuisine 种类 ≥ 5 为通过；C10 以非目标 slot 零变动 + tool 正确调用为通过（binary，任一违反即 fail）；C11 以 counter 同步无 off-by-one + 边界 disabled 态正确为通过；C12 以字段完整率 = 100%（9 段全部包含 4 项字段）为通过。

---

#### §3.4.3 评测集来源

评测集由三部分叠加构成。主体为 Yelp Open Dataset 按用户随机 90/10 切分的 held-out test 用户集（约 17,000 名用户、300,000 条 review）；随机切分以用户为粒度，确保同一用户的所有 review 不会同时出现在训练集与测试集中，避免数据泄露。在此基础上，Haobo 在 w8 期间手工构造 30 条旅行场景 case（对应 §3.4.2 中 C4/C5/C7/C8 类型的变体），覆盖行程上下文、距离约束、时间窗口错配等在 Yelp 历史数据中难以自然采样的边界情况；手工 case 不用于模型训练，仅用于 demo 展示和 Agent 层（Layer B）评测。冷启动子集从 review 数 < 5 的用户中整体抽出，不参与训练，专用于 Cold-start AUC 的单独测量。跨城市子集为在 ≥2 个城市有 review 记录的用户，视作"旅行用户"代理，在 Philadelphia 训练完成后用 Tampa review 做测试，衡量 Cross-city 泛化能力。负采样协议同 §3.4.1 脚注：每正例在同城随机取 4 个未访问商家作为负例，训练与评测协议统一，不单独调节评测负采样比。

v2 在此基础上新增 **12 个手工 trip case**（Philadelphia + Tucson + Tampa 各 1-3 day，附加 1-2 个 dietary / budget 约束），专用于 §3.4.4b Trip 场景独立评测协议，不计入 Yelp held-out split 的统计数字。

---

#### §3.4.4 Agent 层评测（Layer B）

> Agent 层评测聚焦"LLM 包装是否正确理解用户意图并调用推荐器"，与 Layer A 的模型质量评测正交。Layer B 通过率低不影响 Criterion 7 打分，但会影响 Demo 质量。v2 在 v1 四个子维度基础上新增三个 trip-plan 专用子维度（见下表 trip 区块）。

| 子维度 | 度量方式 | 样本量 | 目标 | 测量者 |
|---|---|---|---|---|
| **意图提取准确率** | F1（macro）vs 手工标注 gold set；类别：cuisine / price / distance / time / dietary / trip-context / none | 50 条用户 utterance | F1 ≥ 0.85 | Haobo 标注，自动化脚本跑 |
| **工具分发正确率** | Exact match：模型选择的 tool name vs ground-truth tool（recommend_restaurants / plan_trip / get_info / handle_error） | 50 条 utterance | ≥ 0.90 | Haobo 标注 |
| **响应合成质量** | 5-point Likert × 5 维度（相关性 / 流畅度 / 事实性 / 有用性 / 简洁性）；三人平均分 | 30 个采样输出 | 各维度平均 ≥ 3.8 / 5 | Haobo + Zimeng + Cindy 各自独立打分后取均值 |
| **工具结果忠实度** | 人工 binary 判断：合成回复是否与工具返回的推荐列表矛盾（e.g. 推荐了列表外的商家、编造评分） | 30 个输出 | ≥ 95% faithful（≤ 1 个 fail） | Haobo |

> **— Trip Plan 专用 Agent 评测（v2 新增）—**

| 子维度 | 度量方式 | 样本量 | 目标 | 测量者 |
|---|---|---|---|---|
| **Itinerary Parsing 准确率** | F1 score 抽取 destination / days / regions / dietary-preferences vs 手工标注 gold；utterance 形如 "我要去 Philadelphia 玩 3 天，前两天市区，第三天Center City，全程不吃猪肉" | 30 条行程描述 utterance | F1 ≥ 0.85 | Haobo 标注 |
| **Activity 文案合理性** | 5-point Likert × 3 维度（景点真实可达性 / 时间合理性 / 与下一活动的接续性）；三人独立打分取均值 | 27 个 activity（3 days × 3 periods × 1 trip）中随机抽 9 个 | mean ≥ 4.0 / 5（每维度） | Haobo + Zimeng + Cindy |
| **modify_trip_slot 局部修改正确性** | Binary check：仅修改 (target day, target period) 的 3 个候选，其他 24 个候选完全不变；同时检查 reply_text 是否有简短确认 | 10 个 modify case（来自 §3.4.4b 协议中的 C10 变体） | 100% pass（0 tolerance） | Haobo |

> [!info] 评测时间规划
>
> Intent / tool-dispatch 标注工作量：约 2h（50 utterance × 2min/条）；质量 Likert 打分：三人各约 1h（30 output × 2min/条）。Trip-specific Agent 评测（Itinerary Parsing + Activity Likert + modify_trip_slot）：Haobo 额外约 3h，Zimeng + Cindy 各约 1h（Activity 打分）。建议在 w9 第一天完成，确保有时间在报告里写实际数字而非占位符。

---

#### §3.4.4b Trip 场景独立评测协议（v2 新增）

> [!success] 决策：Trip-specific metrics 单列成节
>
> v1 的评测体系完全聚焦 chat-flow 推荐（NDCG@10 等 single-shot ranking 指标）。v2 将 trip plan 的评测单列，以确保 Criterion 7 Results 中 trip plan 的 lift 可以用数字证明——不只是 demo 截图。这是必要的：NDCG@10 度量的是"单次请求下 top-10 排序质量"，而 trip plan 的核心质量维度是"跨日多样性 / 地理紧凑性 / 活动语义匹配"，两套指标互相不替代。

##### 评测协议描述

**手工 trip case 集**：准备 12 个手工构造的 trip case，覆盖：

| case # | 城市 | 天数 | 约束条件 |
|---|---|---|---|
| T1-T3 | Philadelphia | 1 / 2 / 3 天 | 无约束 / 素食 / 低价 $$ |
| T4-T6 | Tucson | 1 / 2 / 3 天 | 无约束 / 无麸质 / 高档 $$$+ |
| T7-T9 | Tampa | 1 / 2 / 3 天 | 无约束 / 素食 + 低价 / 海鲜偏好 |
| T10-T12 | Cross-city（Philadelphia → Tampa → Tucson） | 3 天 | 跨城市行程多样性测试 / 无 dietary 约束 / 价位混合 |

**全链路运行**：对每个 trip case，运行 F1（用户发起 trip plan 请求）→ S6（plan_trip 生成）→ F2（渲染结果）全链路，记录完整 `TripPlanRender`（27 候选餐厅 + 9 个 activity）。

**对每个 trip case 记录以下指标**：

| 指标类型 | 内容 |
|---|---|
| 离线 trip metrics | Trip Diversity、Geographic Compactness、Activity-Restaurant Semantic Match、Per-Period Candidate Diversity（见 §3.4.1 Trip-specific 区块公式） |
| Activity 可读性 | Haobo 主观打分（5-point，1 = 完全不合理，5 = 完全可执行）；对 9 个 activity 段各打一分，取均值 |
| 整体可执行性 | Haobo 5-point Likert："真实游客拿到这个 plan 能否照做？"（1 = 根本无法执行，5 = 可直接拿去旅行） |

##### 预期结果（TBD — w9 回填实测数字）

| 指标 | 目标值 | Baseline（无 MMR + score-greedy）| 预估提升 |
|---|---|---|---|
| Trip Diversity | ≥ 0.7 | ~0.45（估算） | +0.25 |
| Geographic Compactness | < 5 km | ~12 km（估算，无 geo heuristic 时跨区域选餐） | -7 km |
| Activity-Restaurant Semantic Match | ≥ 0.4 | ~0.25（估算，无 activity_emb 时 cuisine-agnostic） | +0.15 |
| Per-Period Candidate Diversity | ≥ 0.66 | ~0.40（估算，score-greedy 倾向同 cuisine） | +0.26 |

##### Ablation 设计

对应 §3.3.1 H10 的验证，设计 3 个 ablation 变体：

| Ablation | 去掉的组件 | 度量 | 与 Full 模型的边际 gain |
|---|---|---|---|
| No MMR | 去掉 MMR 重排，直接用 DeepFM score top-3 | Per-Period Candidate Diversity + Trip Diversity | 估计 diversity 下降 ~0.26 pp（见 baseline） |
| No activity_emb | 去掉 `activity_emb` feature，使用 cuisine-agnostic context | Activity-Restaurant Semantic Match | 估计 match 下降 ~0.15（H9 的直接验证） |
| No geo heuristic | 去掉地理紧凑性约束，允许跨区域选餐 | Geographic Compactness | 估计距离增加 ~7 km（回退到 baseline 水平） |

ablation 结果对应 §3.3.1 H10 假设验证（Per-Period Diversity ≥ 0.66 验证 MMR 重排有效性）和 H9 假设验证（Activity-Restaurant Match ≥ 0.4 验证 activity_emb 语义对齐）。若 ablation 边际 gain < 1pp，承认假设失败并在 §3.4.7 Learnings 中诚实说明原因。

> [!info] 协议执行时间规划
>
> 12 个 trip case 手工生成：约 30 min（用 Figma Make 原型或本地 mock 跑）；指标计算（4 个 metrics × 12 cases）：Python 脚本约 1h 编写 + 5 min 运行；Haobo 主观打分（Activity 可读性 + 整体可执行性 × 12 cases）：约 1h。建议在 w9 前两天完成，与 §3.4.4 的 Agent 评测并行推进。

---

#### §3.4.5 ML2 Rubric 8-criterion 自检（Layer C）

> 用途：**5/22 日交稿前最后一次 gap check**。每项找到对应 PRD 章节 + 实体证据后才能勾选 done。完成度自评是工作量信号，不是最终成绩预测。

| Criterion | 评分项 | PRD 对应章节 | 状态 | 证据类型 | Owner | 完成度（5/22 前）|
|---|---|---|---|---|---|---|
| 1 | Problem Statement | §1 Background | ✅ done | callout + Feature Result 图 + 范围表 | Haobo | 100% |
| 2 | Assumptions / Hypotheses | §3.3.1 模型假设（H1-H10） | 🔵 in-progress | hypothesis 表 + 可证伪条件（H9/H10 为 v2 新增） | Haobo | TBD |
| 3 | Exploratory Data Analysis | §3.3.2 EDA | 🔵 in-progress | rating 分布图 + sparsity heatmap + popularity bias 图 + 段落 | Zimeng + Cindy | TBD |
| 4 | Feature Engineering & Transformations | §3.3.3 特征工程 | 🟡 planned | feature 表（字段 × 类型 × 变换方式 × 原因，v2 增至 26 个特征含 activity_emb） | Haobo | TBD |
| 5 | Proposed Approaches + overfit/underfit | §3.3.4 模型方案 | 🟡 planned | model spec 表 + train/val AUC 学习曲线 + sweep 结果表 + **DeepFM + MMR ablation chart**（v2 新增） | Haobo | TBD |
| 6 | Proposed Solution + regularization | §3.3.5 选型 + 正则化 | 🟡 planned | hyperparam sweep 表 + 最终 config + dropout/L2 ablation | Haobo | TBD |
| 7 | Results + Learnings | §3.4（本节）+ §3.4.6 + §3.4.7 | 🟡 planned | 离线结果汇总表 + ablation 图 + Learnings 填写 + **trip-specific 4 metrics result table**（v2 新增） | Haobo | TBD |
| 8 | Future Work | §6 开放问题 / Future Work | 🟡 planned | bullet list（在线 feedback loop / GRU4Rec / xDeepFM / FFM）| Haobo | TBD |

> [!warning] 注意：Criterion 5 要求明确展示 overfitting / underfitting 检查
>
> 仅给出 test AUC 不够——Bose 的评分细则明确要"checks for overfitting/underfitting"。需要在 §3.3.4 里附 train vs val AUC 随 epoch 的学习曲线（折线图），并说明 early stopping 触发点。v2 额外要求提供 **DeepFM + MMR ablation chart**（对应 Criterion 5 中 MMR / Heuristic re-rank 的 "proposed approach" 验证）：去掉 MMR vs 完整模型的 Per-Period Diversity 折线图，一张图即可满足。如果没有可视化，这一项最多得 3/5。

---

#### §3.4.6 离线结果汇总占位

> [!warning] 结果数字在 w8 末（≈ 2026-05-16）跑完模型后回填。下表当前值为目标值，不是实测值。报告提交前必须替换为真实数字 + 置信区间。

| 模型 | AUC | NDCG@10 | Recall@10 | Coverage@10 | Cold-start AUC | 实现库 / 备注 |
|---|---|---|---|---|---|---|
| MF baseline | 0.65 | 0.18 | 0.10 | 5% | 0.55 | Surprise lib；纯协同过滤，无 side feature |
| FM | 0.70 | 0.24 | 0.15 | 12% | 0.60 | xLearn；加入 cuisine / price / city embedding |
| DeepFM（ours） | 0.75+ | 0.30+ | 0.20+ | 30%+ | 0.65+ | deepctr-torch；FM + DNN 共享 embedding |
| Two-Tower → DeepFM | 0.78+ | 0.33+ | 0.22+ | 35%+ | 0.68+ | Two-Tower 粗召回 top-200 → DeepFM 精排 |
| Two-Tower → DeepFM + MMR（trip mode） | 0.78+ | 0.33+ | 0.22+ | 35%+ | 0.68+ | 同上 + MMR 重排 + activity_emb feature + geo heuristic；**额外报告 Trip Diversity 0.72+ / Geo Compactness 4.5 km / Activity Match 0.42+ / Per-Period Div 0.70+** |

> **阅读提示**：从 MF → FM → DeepFM 的递进对比是 Criterion 7 叙事的主轴。每跨一层，需要说明 "lift 是否显著（paired t-test on per-user NDCG, α=0.05）"，而不只是列绝对数字。Two-Tower → DeepFM 的两阶段是 stretch goal；若时间不足，可在 Criterion 8 Future Work 里保留为 "已实验，结果见附录"。第 5 行（trip mode）的 4 个 trip-specific 指标在 §3.4.4b 协议中单独汇报，**不与前 4 行的 chat-flow 指标混写**。

---

#### §3.4.7 Learnings 框架（for Criterion 7 writeup）

> 以下 bullet shell 在 w9 拿到实验结果后填入。当前为结构占位，逻辑主线已锁定。

- **假设验证回溯（→ §3.3.1 H1-H10）**：哪几条假设被实验数据支持（例：H1 "用户偏好可通过 embedding 内积捕捉" ↔ FM 显著优于 MF），哪几条被推翻或不可验证。不可验证的假设（因 Yelp 数据无真实行程序列）需要诚实说明，不要沉默跳过。v2 新增 H9（activity-restaurant 语义对齐）和 H10（MMR 重排有效性）的验证结论需在此汇报。

- **DeepFM vs FM 的 lift 显著性**：用 per-user NDCG@10 做 paired t-test（α=0.05，双尾）；如果 p > 0.05，承认 DL 在当前数据量下未产生显著提升，并分析可能原因（数据太稀疏 / embedding dim 太小 / 特征工程不足）。不要把"不显著"写成"具有启发意义"。

- **Cold-start 表现 vs popularity baseline**：Popularity baseline = 永远推该城市 top-10 热门商家，zero personalization。对比 Cold-start AUC，计算 effect size（Cohen's d）；如果 effect size < 0.2，承认冷启动效果不及预期并讨论原因（<5 条 review 信号太弱，side features 未充分捕捉用户画像）。

- **Trip-context features 的边际 gain**：对比"有 trip-context 特征（day_of_trip / prior_cuisine_count / distance_constraint）"vs "无 trip-context 特征"的 ablation，记录 NDCG@10 差异。如果差异 < 1pp，诚实承认 H5（"行程上下文显著提升多样性"）失败，并给出合理解释（Yelp review 无真实行程序列，合成特征携带的信号有限）——这是预期内的诚实结论，Bose 在 Criterion 7 里明确给 "Learnings" 加分，不怕负结论。

- **MMR vs score-greedy 的 trade-off（v2 新增）**：λ=0.7 是否最优？报告中需给出 λ ∈ {0.5, 0.6, 0.7, 0.8} 的 Per-Period Candidate Diversity vs NDCG@3 的 trade-off 图。若 λ=0.5（更激进 diversity）使 NDCG@3 下降 > 2pp，说明 diversity 增益是以 ranking 质量为代价的，需在报告中诚实讨论。若 λ=0.8 的 diversity 指标不达目标（< 0.66），说明 MMR 参数需要重新调整。

- **Activity-aware ranking 的边际 gain（v2 新增）**：如果 `activity_emb` feature 的 ablation 显示 Activity-Restaurant Semantic Match 提升 < 1pp（H9 失败临界），承认 H9 失败并讨论原因——最可能的解释是 sentence-transformer 嵌入与 Yelp category multi-hot 的语义空间不对齐（sentence-transformer 在自然语言语料上训练，cuisine category 的语义位置与 activity 描述的语义位置之间存在 domain gap）。给出 Future Work 方向：用 Yelp Review text 微调 sentence-transformer，使 activity 描述和餐厅 review 的语义空间对齐。

---

#### §3.4.8 写报告时的常见陷阱（自警提醒）

以下是 Criterion 7 写作中高频翻车点，交稿前逐条对照检查：

- **只报 best 数字，不报 std / confidence interval**：Yelp 数据量大，标准差小，但仍需在结果表里给 mean ± std（或 95% CI）；否则读者无法判断数字是否 reproducible。

- **用 train metric 当 test metric 汇报**：学习曲线和调参可以看 val AUC，但 §3.4.6 汇总表的所有数字必须来自 **test split**，且 test split 只能看一次（最终结果揭盲）。

- **把 random split 写成 temporal split**：如果实际做了 random user split，不要在报告里写"时间序列切分"——会被助教注意到。如果做了 temporal（按 review 时间）split，需要在方法里明确说明并讨论其与 random split 的差异。

- **Ablation 缺 MF baseline，让读者无法判断 lift 大小**：DeepFM 的结果必须和 MF + FM 并排展示，否则"0.30 NDCG@10"这个数字没有参照系，评分者无法判断提升幅度。

- **把"DL 没有显著提升 baseline"的诚实结论 hedge 成"结果具有启发意义"**：Bose 的 rubric 对 Learnings 的评分包含"honest assessment"维度。如果 DeepFM 不显著优于 FM，直接写出来，然后分析原因，这比 hedge 更能拿到 Criterion 7 的高分。

- **遗漏 Criterion 5 要求的 overfitting check 可视化**：结果汇报不只是最终数字，还需要附 train vs val 学习曲线图（见 §3.4.5 中的 ⚠️ callout）。

- **Learnings 节点没有和 §3.3.1 Hypothesis 表形成闭环**：每条 Learning 都应该 map 到至少一个 H1-H10，否则"Assumptions / Hypotheses"和"Results + Learnings"就成了两个孤岛，白白浪费了 Criterion 2 埋下的铺垫。v2 新增 H9/H10，learnings 必须覆盖这两条。

- **用 chat-flow metrics（NDCG@10）评测 trip plan 质量（v2 新增）**：trip plan 的核心指标是 Trip Diversity / Geographic Compactness / Activity-Restaurant Match / Per-Period Candidate Diversity，不是 single-shot ranking 质量。这两套指标互相不替代，报告中要分两个 section 写：chat-flow 场景用 §3.4.1 前 9 个指标，trip plan 场景用 §3.4.1 后 4 个 trip-specific 指标 + §3.4.4b 协议结果。把 NDCG@10 拿来概括 trip plan 质量的说法会在 Criterion 7 评分时被识别为理解不到位。

---

<!-- §3.4 v2 完成 · Sib D2 · 2026-05-04 -->
