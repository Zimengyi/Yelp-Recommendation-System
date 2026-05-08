# Training Pipeline 实施计划 — Taste hunter

> **创建**：2026-05-05 · **Owner**：Haobo（model）+ Zimeng + Cindy（EDA）
> **关联**：`PRD_v1_section3.3_Model_v2.md` §3.3.6 训练 Protocol / `recommender_training_explainer.md` §2 训练数据 / `phase_implementation_notes.md` 实施日志
> **截稿**：2026-05-23（周六）· **总工期 18 天**

> **⚠️ 流程规则（强制）**：每完成一个 Phase（含子阶段如 5.1/5.2…），必须在**同一次 commit** 里同步：
> 1. 在本 plan 对应章节标题尾加 ✅ + commit hash + 实际完成日期
> 2. 在 `docs/phase_implementation_notes.md` 对应 §N 节填实际产物 / 跑数 / 偏差 / 踩坑
> 3. 在 §0.4 高层时间线表里把该行的 ✅/🟡/⏳ 状态更新
>
> 没做这三件事的 phase 不算"完成"。

---

## §0 计划元信息

### 0.1 目标

把 §3.3 v2 规划的 DeepFM 推荐器从纸面 PRD 跑到 ML2 期末提交可演示状态：3 个 baseline（MF / FM / DeepFM）+ 离线 metric 全套（AUC / NDCG@10 / Recall@10 / Cold-start AUC / Coverage）+ hyperparam sweep 报告 + Persona demo + 8-criterion rubric writeup。

**架构定位（v2.2 单模型双路召回）**：单 DeepFM 精排模型 + 双路召回——S2/S6 CRS 路（LLM intent + hard filter）是必交付，S1 push 路（Two-Tower / DSSM）是 stretch goal。即使 Two-Tower 来不及，CRS 路 demo 仍可保底（详见 §3.3.4 v2.2 + §3.3.7 L3）。

**Stretch goals**：Two-Tower 召回（S1 路加速）+ MMR 重排（F2 Trip 多样性）+ F2 Trip Plan 完整流。

### 0.2 资源 & 工具栈

| 维度 | 配置 |
|---|---|
| **算力** | Google Colab T4（free tier 16GB VRAM）+ 本地 MacBook M3 Pro（36GB unified memory，MPS backend）|
| **数据** | `Yelp JSON 2/` 已下载（business 150K / user 2M / review 7M 行）|
| **核心库** | `pandas` / `polars`（聚合）/ `surprise`（MF）/ `xLearn` 或 `pyfm`（FM）/ `deepctr-torch`（DeepFM）/ `faiss-cpu`（双塔 ANN）/ `sentence-transformers`（activity_emb）|
| **LLM** | Anthropic SDK + `claude-sonnet-4-6`（agent 层 + AI Overview 子调用）|
| **前端 demo** | Streamlit（轻量 demo，1.5d 预算）|
| **实验跟踪** | CSV log + matplotlib（不上 W&B 避免学习成本）|
| **代码托管** | 工作目录直接写 `notebooks/` + `scripts/`，不开远程 repo（class project 范围）|

### 0.3 工作目录结构

```
canvas/ml2/project/
├── Yelp JSON 2/                  # 原始数据（已有）
├── data/
│   ├── cleaned/                  # Phase 1 输出：filter 后的 parquet
│   └── features/                 # Phase 3 输出：feature 表 + cuisine_vocab
├── notebooks/                    # 探索性分析 + sweep result 可视化
├── scripts/                      # 可重复运行的训练 / 评测脚本
├── models/                       # 训练 checkpoint（.pt / .pkl）
├── reports/
│   ├── figures/                  # learning curve / sweep heatmap / ablation
│   └── final_report.md           # Phase 9 输出
└── training_pipeline_plan.md     # 本文件
```

### 0.4 高层时间线

| Phase                                        | 日期范围               | 主要交付                                        | Owner                  | 工期   |
| -------------------------------------------- | ------------------ | ------------------------------------------- | ---------------------- | ---- |
| **0. 同步对齐** ✅                               | 5/5 周二             | 团队对齐 PRD v2 + 本计划（已完成，PRD v2.2 锁定 5/6）       | All                    | 1d   |
| **1. 数据准备** ✅                               | 5/6 – 5/8          | filter 后的 parquet（user / business / review）（已完成：9K 餐厅 / 1M reviews / 359K users，Phase 1 commit 1cb2230） | Haobo                  | 3d   |
| **2. EDA** ✅                                | 5/6 – 5/11（与 1 并行） | 9 张图 + cuisine_vocab.json（已完成 5/6 commit f336e07） | Zimeng + Cindy         | 6d   |
| **3. 特征工程** ✅                              | 5/9 – 5/11         | 26 features + 234-dim 输入 + 2.07M 训练样本 (1:4 负采样)（已完成 5/6 commit 194f8e2） | Haobo                  | 3d   |
| **4. Baseline 模型** ✅                       | 5/12 – 5/13        | MF (AUC 0.785) + FM (AUC 0.830)（已完成 5/7 commit 1a12f23） | Haobo                  | 2d   |
| **5. DeepFM 主训练 + sweep** 🟡               | 5/14 – 5/16        | 5.1 sanity ✅ (NDCG 0.318 / Recall 0.540) commit 6354456；5.2 emb_dim sweep 后台跑中；5.3/5.4/5.5 待跑 | Haobo                  | 3d   |
| **6. Two-Tower (S1 加速) + MMR (F2)**（stretch）⏳ | 5/17 – 5/18        | DSSM 召回（仅 S1 路）+ MMR 重排（F2 trip）            | Haobo                  | 2d   |
| **7. 评测** ⏳                                 | 5/19               | Test split 一次性 metric + 4 个 trip metric     | Haobo                  | 1d   |
| **8. Agent 集成 + Demo** ⏳                    | 5/20 – 5/21        | Streamlit demo 端到端跑通                        | Haobo + All（Likert 打分） | 2d   |
| **9. Writeup + Rubric 自检** ⏳                | 5/22               | final_report.md + 提交所需 PDF/notebook         | Haobo                  | 1d   |
| **10. 提交** ⏳                                | 5/23               | Canvas 提交                                   | Haobo                  | 0.5d |

**关键 Checkpoint**：5/12 周二中段同步 / 5/19 Two-Tower 进度判定 / 5/22 交稿前 rubric 全绿。

---

## §1 Phase 1 — 数据准备（5/6 – 5/8） ✅ 完成 2026-05-06 · commit `1cb2230`

> **实施日志**：见 `phase_implementation_notes.md` §1（产物 9,022 餐厅 / 1,032,056 reviews / 359,007 users）。

**Owner**：Haobo · **工期**：3 天 · **前置依赖**：无

### 1.1 解压 + 城市过滤

| 步骤 | 详细 |
|---|---|
| **1.1.1** | 从 `Yelp JSON 2/yelp_dataset.tar` 解压 5 个 JSON（已部分完成，验证齐全）|
| **1.1.2** | 写 `scripts/prepare_data.py`：流式读 `business.json`（150K 行），筛 `state ∈ {CA, NV, NY, IL, PA, FL, AZ}` 并按 `city` 聚类 |
| **1.1.3** | 选定 3 target 城市：**Philadelphia + Tucson + Tampa**（Haobo 所在地）。导出 `target_business_ids.txt` |
| **1.1.4** | 流式 filter `review.json`：只保留 `business_id ∈ target_business_ids` 的 review；输出 `data/cleaned/reviews_target.parquet` |

**输入**：`Yelp JSON 2/*.json`
**输出**：
- `data/cleaned/businesses_target.parquet`（餐厅子集 ≈ 30K 行）
- `data/cleaned/reviews_target.parquet`（target 城市 review ≈ 1.5M 行预估）
**工具**：`pandas` + `pyarrow`
**时间预估**：4-6 小时（streaming + filter + parquet 写入）
**验收标准**：
- [ ] target_business 数 ≥ 25K
- [ ] target reviews 数 ≥ 1M
- [ ] 3 个城市均有 ≥ 3K 餐厅
- [ ] parquet 文件总大小 ≤ 1GB

### 1.2 餐厅子集再过滤（categories 含 Restaurants/Food）

| 步骤 | 详细 |
|---|---|
| **1.2.1** | 在 1.1.4 基础上，进一步过滤 business 的 `categories` 字段 |
| **1.2.2** | 保留 `categories` 包含 "Restaurants" 或 "Food" 的商家（实测覆盖 43.1%）|
| **1.2.3** | 过滤 `is_open == 1` 的商家（排除已关闭店）|

**输出**：
- `data/cleaned/restaurants_open.parquet`（≈ 13K 行）
- 对应 reviews 链上过滤：`data/cleaned/reviews_restaurant.parquet`
**时间预估**：1-2 小时
**验收标准**：
- [ ] 3 城市开门餐厅数均 ≥ 1.5K
- [ ] 关联 reviews 数仍 ≥ 800K

### 1.3 User 子集 + Train/Val/Test 时序切分

| 步骤 | 详细 |
|---|---|
| **1.3.1** | 从 1.2 输出反查 `unique user_id`，从 `user.json` 抽对应行 → `data/cleaned/users_target.parquet` |
| **1.3.2** | 按 `review.date` 分位数切：≤ P70 → train / P70-P80 → val / > P80 → test |
| **1.3.3** | 写出 `data/cleaned/{train,val,test}_reviews.parquet` 三个文件 |
| **1.3.4** | 单独抽 cold-start subset：`review_count < 5` 的 user → `data/cleaned/coldstart_test_reviews.parquet`（这些用户的所有 review 都不进 train）|
| **1.3.5** | 单独抽 cross-city subset：在 ≥ 2 个城市有 review 的用户 → `data/cleaned/crosscity_test_reviews.parquet` |

**输出**：5 个 parquet 文件覆盖训练 / 验证 / 测试 / cold-start / cross-city
**时间预估**：2-3 小时
**验收标准**：
- [ ] train/val/test 比例约 70/10/20
- [ ] cold-start subset ≥ 30K reviews
- [ ] cross-city subset ≥ 10K reviews
- [ ] 没有 user_id 同时出现在 train + cold-start subset（无泄漏）

### 1.4 Phase 1 风险 / Fallback

| 风险 | 触发 | Fallback |
|---|---|---|
| 3 城市数据量不均（如某城市 reviews < 50K）| 某城市 reviews < 50K | 启用 §11 R3 fallback：从 Top-11 备选中挑替代城市（Indianapolis / Nashville / New Orleans 等）|
| Parquet 写入内存爆 | 7M reviews 一次性 load 失败 | 用 polars streaming `scan_ndjson` 或 chunked pandas |
| 时序切分后 test 太小 | test reviews < 100K | 调整 P70/P80 → P60/P75（缩短 train 提供更多 test）|

---

## §2 Phase 2 — EDA（5/6 – 5/11，与 Phase 1 并行） ✅ 完成 2026-05-06 · commit `f336e07`

> **实施日志**：见 `phase_implementation_notes.md` §2（9 张图 + cuisine_vocab.json 50 标签）。

**Owner**：Zimeng + Cindy · **工期**：6 天 · **前置依赖**：Phase 1.1 完成（提供 target_business 列表）

EDA 主要回答 §3.3.2 列出的 11 个 Q（含 v2 新增的 Q11 activity 数据可用性）。Zimeng + Cindy 用 Jupyter notebook 各分担一半 Q，最终合并到 `notebooks/01_eda.ipynb`。

| Q | 主题 | Owner | 期望产出 | 报告章节 |
|---|---|---|---|---|
| Q1 | 评分分布 + power-law | Zimeng | rating 直方图 + log-log scatter | §3.3.2 图 1/2 |
| Q2 | User-Item 稀疏度 heatmap | Zimeng | 1K×1K density matrix | §3.3.2 图 3 |
| Q3 | Top-30 categories 频次 | Zimeng | 条形图 + cuisine_vocab 输出 | §3.3.2 图 4 + `data/features/cuisine_vocab.json` |
| Q4 | 地理分布 + k-means k 选择 | Cindy | 3 城市散点图 + 肘部曲线 | §3.3.2 图 5 |
| Q5 | 时段分布（合成 trip context 依据） | Cindy | 小时分布图（用 check-in 数据）| §3.3.2 图 6 |
| Q6 | 冷启动用户比例 | Cindy | 饼图 + 数字 | §3.3.2 文字 |
| Q7 | 照片覆盖率 | Cindy | photo_count 直方图 | §3.3.2 文字 |
| Q8 | Review 长度分布（AI Overview cap）| Zimeng | 箱线图 P25/50/75/90/99 | §3.3.2 图 7 |
| Q9 | 跨城市流动率 | Zimeng | 单一统计数字 | §3.3.2 文字 |
| Q10 | 人气偏差（Lorenz / Gini）| Zimeng | Lorenz 曲线 + Gini 系数 | §3.3.2 图 8 |
| **Q11** | Activity text 数据可用性（v2 新增）| Cindy | 路径对比表 + 推荐方案 | §3.3.2 文字 |

**输出**：
- `notebooks/01_eda.ipynb`（含全部 11 个 Q 的 cell + 图）
- `reports/figures/eda_*.png`（8 张图导出）
- `data/features/cuisine_vocab.json`（top-50 cuisine 列表，喂给 Phase 3 feature engineering）

**时间预估**：每人 ~10-12 小时（5/6-5/11 间分摊）
**关键里程碑**：
- 5/8 周五：Q1-Q4 完成（含 cuisine_vocab，Haobo Phase 3 启动依赖）
- 5/11 周一：全部 Q 完成 + 报告 placeholder 填好

**验收标准**：
- [ ] 8 张图清晰可读，分辨率 ≥ 200dpi
- [ ] cuisine_vocab.json 至少 50 项
- [ ] Q11 给出明确路径推荐（LLM 生成 vs 模板库）
- [ ] EDA 结论能为 §3.3.1 的 H1/H3/H6 假设提供支撑数字

---

## §3 Phase 3 — 特征工程（5/9 – 5/11） 🟡 v1 完成 2026-05-06 · commit `194f8e2`；v2 加 item_text_emb 进行中（2026-05-07）

> **v1 实施日志**：见 `phase_implementation_notes.md` §3（26 features / 234-dim / 2.07M 训练样本，1:4 负采样）。
> **v2 改动**：item_features 加第 10 列 `item_text_emb_pca32`（sentence-transformer + PCA32），同时进 Phase 5 DeepFM 精排和 Phase 6 Two-Tower 召回。Phase 3 重跑（~10 min）→ Phase 5.3 grid 直接用新 features，跳过 5.1/5.2（emb=32 最优结论已锁定）。

**Owner**：Haobo · **工期**：3 天 · **前置依赖**：Phase 1 + Phase 2 (Q3) 完成

按 §3.3.3 v2 的 26 个特征展开，分 User (8) / Item (9) / Context (9) 三组。

### 3.1 User Features 表（5 直接 + 3 聚合预计算）

| 步骤 | 详细 |
|---|---|
| **3.1.1** | 5 直接字段：`user_id` / `avg_rating_given` / `review_count_log` / `days_active` / `elite_flag` 直接从 `users_target.parquet` 派生 |
| **3.1.2** | `mean_distance_traveled`：join `reviews_restaurant` × `restaurants_open[lat, lon]` → 每 user pairwise haversine 均值 → `log1p` |
| **3.1.3** | `fav_cuisine_emb`：join `reviews_restaurant` × `restaurants_open[categories]` → top-3 cuisine pooling over `cuisine_vocab.json` |
| **3.1.4** | `price_tolerance_avg`：join `reviews_restaurant` × `restaurants_open[attributes.RestaurantsPriceRange2]` → 均值（缺失行丢弃；用户全缺失 → 0.5） |
| **3.1.5** | 输出 `data/features/user_features.parquet`（用 polars 聚合，~10-15 min）|
| **3.1.6** | 加 `<NEW_USER>` OOV 行：`user_id="<NEW_USER>"`，所有数值字段填全局中位数 / 0 / 0.5 |

**输出**：`data/features/user_features.parquet`（行数 ≈ target unique users + 1 OOV row）
**时间预估**：4-6 小时（含 polars 调试）
**验收标准**：
- [ ] 行数 = train + val + test 中 unique user_id 数 + 1（OOV）
- [ ] 8 字段无 NaN（缺失值已 fallback）
- [ ] 直方图检查：`avg_rating_given` 集中在 0.6-0.95（评分偏正向）；`review_count_log` 长尾形状

### 3.2 Item Features 表（10 字段，v2 加 text_emb）

| 步骤 | 详细 |
|---|---|
| **3.2.1** | 直接字段：`business_id` / `avg_rating`（Bayesian smoothed，C=10）/ `review_count_log` / `price_level` / `is_open` / `has_outdoor_seating` / `photo_count` / `city_id` |
| **3.2.2** | `categories_multi_hot`：把 categories CSV 字符串拆 → 对 cuisine_vocab top-50 做 multi-hot 编码 |
| **3.2.3** | 输出 `data/features/item_features.parquet`（行数 9,022 餐厅 + 1 OOV）|
| **3.2.4 (v2 新增)** | **`item_text_emb_pca32`**：用 `sentence-transformers/all-MiniLM-L6-v2` 编 `name + categories`（不用 review 文本，避免引入用户主观噪声）→ 384d → PCA 降到 32d，作为 ColBERT-light 语义表示 |

**时间预估**：3-4 小时
**验收标准**：
- [ ] 行数 ≥ 9K
- [ ] `categories_multi_hot` 每行非零位数 1-5（Yelp 餐厅平均 2-3 个 category）
- [ ] `item_text_emb_pca32` 每行 32 维 float32，cold-start item OOV 行用 zeros(32)

**v2 加 text_emb 的设计 rationale（2026-05-07）**：参考 Haobo 抖音电商笔记 §5.1 Doc 侧 sentence encoder + ColBERT 思路。Yelp 项目里 Query 侧 sentence encoder 被 Sonnet LLM 替代（更强），Doc 侧用 MiniLM 编餐厅文本。这个特征**同时进 Phase 5 DeepFM 精排和 Phase 6 Two-Tower 召回**，主要价值是 cold-start item（`<NEW_BUSINESS>` OOV）时仍有 32 维语义信号 fallback。

### 3.3 Context Features 派生函数（9 字段）

Context features 不预计算成静态表，而是写成函数 `build_context(review_row, biz_row, user_lat_lon, trip_state)` → 在训练 batch loader 里实时调：

| 字段 | 计算方式 |
|---|---|
| `distance_from_user_km_log` | Haversine(user_lat_lon, biz.lat_lon) → log1p；训练时 user_lat_lon = user 历史 review 的均值 |
| `hour_bucket` | review.date 提取小时（Yelp 有时间），sin/cos 编码 |
| `day_of_week` | review.date 提取 weekday，one-hot |
| `is_weekend` | day_of_week ∈ {Sat, Sun} |
| `trip_day_index` | 训练 review 不在 trip 场景 → 全填 0 |
| `region_cluster_id` | 跑 k-means(8) on biz lat/lon → 每个 biz 一个 cluster_id（预计算）|
| `period_id` | 训练 review 默认填 `<UNK>`（因为非 trip 场景）|
| `activity_emb` | 训练默认 zeros(32)（非 trip） |
| `prior_meals_cuisines` | 训练默认 zeros(50)（非 trip） |

**输出**：
- `scripts/build_features.py`（含 `build_context` 函数 + region_cluster_id 预计算）
- `data/features/region_clusters.json`（k-means 模型 + cluster center）

**时间预估**：3-4 小时
**验收标准**：
- [ ] `build_context()` 单元测试通过：传一条 review → 输出 9 维正确
- [ ] region_cluster k-means 肘部图（来自 EDA Q4）确认 k=8 合理

### 3.4 Feature Spec JSON 落盘

```json
{
  "user_features": {
    "user_id": {"type": "embedding", "vocab_size": "<NEW_USER>+train_users", "dim": 8},
    "avg_rating_given": {"type": "numeric", "range": [0, 1]},
    ...
  },
  "item_features": {...},
  "context_features": {...},
  "total_dim": 26,
  "version": "v3.0_2026-05-11"
}
```

`data/features/feature_spec.json` 是 DeepFM 输入层的源代码——所有训练脚本读它构建模型。

**时间预估**：1-2 小时
**验收标准**：
- [ ] feature_spec.json 自验证：各字段 dim 加起来 = 模型 input dim

### 3.5 负采样表预计算

| 步骤 | 详细 |
|---|---|
| **3.5.1** | 对 train 中每条 positive (user, biz, rating≥4) 生成 4 条 negative：从同城 + 同 user 未访问商家中随机采 |
| **3.5.2** | 输出 `data/features/train_with_negatives.parquet`（行数 ≈ 1.05M positive × 5 = 5.25M）|

**时间预估**：2-3 小时
**验收标准**：
- [ ] 正负比 1:4
- [ ] 同 user 不重复采到访问过的 biz

### 3.6 Phase 3 风险 / Fallback

| 风险 | Fallback |
|---|---|
| polars 聚合内存爆 | 改 chunked pandas：按 city 分块聚合再合并 |
| EDA Q3 cuisine_vocab 没及时给 | Haobo 用 raw business.json 自己跑 top-50 cuisine 当临时 vocab |
| `mean_distance_traveled` 单店用户太多导致信号弱 | 数值不变（fallback 0），让模型从其他特征学 |

---

## §4 Phase 4 — Baseline 模型（5/12 – 5/13） ✅ 完成 2026-05-07 · commit `1a12f23`

> **实施日志**：见 `phase_implementation_notes.md` §4。
> **跑数**：MF AUC 0.7854 / NDCG@10 0.2677 / Recall@10 0.4651 · FM AUC 0.8302 / NDCG@10 0.2720 / Recall@10 0.4749。FM 在 AUC 上比 MF 提升 +4.5 点。

**Owner**：Haobo · **工期**：2 天 · **前置依赖**：Phase 3 完成

### 4.1 MF Baseline（Surprise SVD）

| 步骤 | 详细 |
|---|---|
| **4.1.1** | 写 `notebooks/03_baseline_mf.ipynb` |
| **4.1.2** | 用 `surprise.SVD`，在 train_with_negatives 上训练（factors=10, epochs=20, lr=0.005）|
| **4.1.3** | 在 val 集计算 AUC / NDCG@10 / Recall@10 |
| **4.1.4** | 在 cold-start subset 单独算 Cold-start AUC |
| **4.1.5** | 保存 model 到 `models/mf_svd.pkl` + 评测结果到 `models/mf_metrics.json` |

**时间预估**：4-6 小时
**期望数字**：AUC ≈ 0.65 / NDCG@10 ≈ 0.18 / Recall@10 ≈ 0.10
**验收标准**：
- [ ] AUC > 0.55（比随机好）
- [ ] cold-start AUC < non-cold AUC（验证 H6 方向）

### 4.2 FM Baseline（xLearn 或 pyfm）

| 步骤 | 详细 |
|---|---|
| **4.2.1** | 写 `notebooks/04_baseline_fm.ipynb` |
| **4.2.2** | 用 xLearn 或 pyfm 训练 FM（factor_dim=8, epochs=10, lr=0.01）|
| **4.2.3** | 输入特征：所有 26 个 feature 的 sparse hash 表示 |
| **4.2.4** | val 集 metric + cold-start AUC |
| **4.2.5** | 保存 `models/fm.pkl` + `models/fm_metrics.json` |

**时间预估**：6-8 小时（含 xLearn 安装调试）
**期望数字**：AUC ≈ 0.70 / NDCG@10 ≈ 0.24 / Recall@10 ≈ 0.15
**验收标准**：
- [ ] FM 比 MF 在 NDCG@10 上提升 ≥ 5pp
- [ ] FM 比 MF 在 cold-start 上提升 ≥ 3pp（验证 side feature 价值）

### 4.3 Phase 4 风险 / Fallback

| 风险 | Fallback |
|---|---|
| xLearn macOS M3 编译失败 | 改用 `pyfm`（pure Python，慢但兼容性好）|
| Surprise SVD 不支持 implicit feedback negative sampling | 改用 `surprise.NMF` 或自己写朴素 MF（PyTorch 几十行）|
| 时间不够 | MF + FM 至少留一个，优先保 FM（与 DeepFM 对比更直接）|

---

## §5 Phase 5 — DeepFM 主训练 + Hyperparam Sweep（5/14 – 5/16） 🟡 进行中

> **当前状态**（2026-05-07）：
> - 5.1 Sanity ✅ commit `91b82cd` (arm64, emb=8 → AUC 0.8339 / NDCG 0.3201 / Recall 0.5398)
> - 5.2 emb_dim sweep ✅ commit `848dfe0` (arm64, best emb_dim=**32**: AUC 0.8436 / NDCG 0.3237 / Recall 0.5483)
> - 5.3 dropout × L2 grid 🟡 待跑（在 emb=32 + v2 item_text_emb 上跑 5×4=20 configs）
> - 5.4 final retrain on train+val ⏳
> - 5.5 ablation no_user_id ⏳
>
> **v2 改动（2026-05-07）**：从 5.3 起 DeepFM 输入新增 `item_text_emb_pca32` (32d sentence-transformer/PCA)，FM 二阶项扩到 5 个 field（user_emb / item_emb / user_num_proj / item_num_proj / item_text_proj），DNN 输入也带上。Cold-start item subset 评测时这个 feature 是主要鲁棒性来源。
>
> **跳过 5.1/5.2 重跑**：v2 只动 item-side input，emb=32 最优结论几乎不变（emb_dim 选择对 user-side 不敏感）；为节省 30 min 重训，5.1/5.2 保留 v1 数字作 baseline 参照。
>
> **实施日志**：见 `phase_implementation_notes.md` §5。

**Owner**：Haobo · **工期**：3 天 · **前置依赖**：Phase 4 完成（baseline 数字作对照锚点）

### 5.1 Sanity check：默认 config 跑通

| 步骤 | 详细 |
|---|---|
| **5.1.1** | 写 `scripts/train_deepfm.py` 用 `deepctr-torch` 的 `DeepFM` 类 |
| **5.1.2** | 默认 config：`embedding_dim=8, dnn_hidden=[256,128,64], dropout=0.2, l2=1e-4, lr=1e-3, batch=1024, epochs=10, neg_ratio=1:4` |
| **5.1.3** | 跑 1 个 epoch 看 loss 下降是否合理 |
| **5.1.4** | 跑 10 epoch + early stopping(patience=3)，记录 train/val AUC 学习曲线 |

**时间预估**：4-6 小时（含 deepctr-torch 接入调试）
**验收标准**：
- [ ] Train loss 单调下降
- [ ] Val AUC > FM baseline（≥ 0.70）
- [ ] 学习曲线无明显发散（train/val gap < 0.05）

### 5.2 Stage A：embedding_dim 扫描

| 步骤 | 详细 |
|---|---|
| **5.2.1** | 跑 4 组 config：`embedding_dim ∈ {4, 8, 16, 32}`，其他超参锁定 default |
| **5.2.2** | 每组训 10 epoch，取 val NDCG@10 最高的 checkpoint |
| **5.2.3** | 绘 NDCG@10 vs embedding_dim 折线图 |
| **5.2.4** | 选定 best dim（预期 8 或 16 最优）|

**时间预估**：6-8 小时（4 × 1.5h 训练 + 分析）
**验收标准**：
- [ ] 4 组数字均能 train/val gap < 0.06
- [ ] 选定 dim 在 val NDCG@10 上 ≥ FM baseline + 3pp

### 5.3 Stage B：dropout × L2 grid

| 步骤 | 详细 |
|---|---|
| **5.3.1** | 固定 5.2 选定的 best dim |
| **5.3.2** | 跑 5 × 4 = 20 组 config：`dropout ∈ {0.1, 0.2, 0.3, 0.4, 0.5}` × `L2 ∈ {1e-5, 1e-4, 5e-4, 1e-3}` |
| **5.3.3** | 每组训 10 epoch，记录 val NDCG@10 |
| **5.3.4** | 绘 5×4 heatmap，选 best |

**时间预估**：12-15 小时（20 × 0.6h 训练）。**这是 Phase 5 最长一步，可能跨晚上挂跑**
**验收标准**：
- [ ] heatmap 有清晰局部最优（不是平坦）
- [ ] best config 在 val NDCG@10 上 ≥ Stage A 最佳值（不退化）

### 5.4 Stage C：负采样比 + 最终重训

| 步骤 | 详细 |
|---|---|
| **5.4.1** | 固定 5.3 best dropout + L2，扫 `neg_ratio ∈ {1:1, 1:2, 1:4}` |
| **5.4.2** | 选定最终 config，在 train + val 合并集上重训 1 次（用更多数据获得更稳模型）|
| **5.4.3** | 输出 final checkpoint：`models/deepfm_final.pt` + `models/deepfm_config.json` |

**时间预估**：3-4 小时
**验收标准**：
- [ ] final config 写入 §3.3.5 最终配置表
- [ ] checkpoint 文件 < 200MB

### 5.5 Ablation：去掉 user_id embedding（验证 H6）

| 步骤 | 详细 |
|---|---|
| **5.5.1** | 用 final config，但把 `user_id` embedding 强制设为全零向量 |
| **5.5.2** | 在 cold-start subset 评测，对比"全特征" vs "无 user_id" 的 Recall@10 |
| **5.5.3** | 写入 §3.4.7 Learnings 第 1 项 |

**时间预估**：2-3 小时
**验收标准**：
- [ ] 两个数字差距 < 0.01（H6 通过）或 < 0.03（H6 弱通过）

### 5.6 Phase 5 风险 / Fallback

| 风险 | Fallback |
|---|---|
| 5.3 grid sweep 算力不够 | 砍到 3×3 = 9 组（dropout {0.2, 0.3, 0.4} × L2 {1e-4, 5e-4, 1e-3}） |
| Colab T4 中断 | 每个 epoch 都 save checkpoint；断了从最近 checkpoint 续 |
| Val 远低于 FM | 检查 feature pipeline（最常见 bug：embedding 输入错位 / negative sampling 没去重）|

---

## §6 Phase 6（Stretch）— Two-Tower (S1 加速) + MMR (F2 多样性)（5/17 – 5/18）

**Owner**：Haobo · **工期**：2 天 · **前置依赖**：Phase 5 完成

> [!info] v2.2 架构定位下 Phase 6 的范围
>
> 本 Phase 在**单 DeepFM 模型 + 双路召回**架构（§3.3.4 v2.2）下分两个独立 stretch 任务：
> - **6.1 Two-Tower / DSSM 召回**——仅服务 S1 push recsys 路径（用户进入屏无 utterance 时的 dense retrieval）。S2/S6 CRS 路走 LLM intent + hard filter，不依赖此项。
> - **6.2 MMR 重排**——仅服务 F2 Trip Plan 场景（per-period top-3 多样性）。F1 Chat 场景不需要。
>
> 两项可独立完成或独立放弃，互不依赖。

> [!warning] Stretch goal — 5/19 决策点
>
> 5/19 周一上午 checkpoint：若 Phase 5 已稳出 DeepFM 数字 + writeup 大纲就绪，则启动；否则跳过，Two-Tower 写入 §6 Future Work（仅影响 S1 dense retrieval；S2/S6 CRS 路 demo 不受影响）。
>
> **优先级**：MMR (6.2) 优于 Two-Tower (6.1)——MMR 直接提升 F2 trip plan demo 视觉效果；Two-Tower 是 S1 工程加速，没做的话 S1 demo 也能跑（降级"地理+时间硬过滤"，~300-1500 候选 DeepFM 直精排 100-300ms 仍可演示）。

### 6.1 Two-Tower (DSSM) 召回（v2 加 ColBERT-light item text emb）

| 步骤 | 详细 |
|---|---|
| **6.1.1** | 写 `notebooks/06_two_tower.ipynb`，用 PyTorch 实现 User Tower + Item Tower（各 MLP[128,64,32]，输出 normalize 后 dot product score） |
| **6.1.2** | **Item tower 输入加 `item_text_emb_pca32` (v2)**——sentence-transformer 编 `name + categories` 后 PCA 降到 32d，对应 Haobo 抖音笔记 §5.1 Doc 侧 sentence encoder + ColBERT 思路 |
| **6.1.3** | 训练目标：BCE on 1:4 negatives（与 DeepFM 共用 train_with_negatives.parquet），dot(u, v) * temperature(10) 后 sigmoid |
| **6.1.4** | 离线预计算所有 9K 餐厅的 item_vec (numpy 矩阵 9K × 32) — 9K 体量太小，brute-force matmul 已 < 1ms，**不上 FAISS**（production 100K+ 才需要 HNSW；ML2 范围内 over-engineered） |
| **6.1.5** | 评测：Recall@10 / @50 / @100 / @200 / @500，对比 DeepFM 单层 NDCG@10；额外做 cold-start subset 单独评测（验证 ColBERT-light 鲁棒性） |
| **6.1.6** | Latency benchmark：100 trial 测 user_tower forward + matmul 耗时（应 < 10ms） |

**时间预估**：4-6 小时（含 v2 加 text_emb 改造）
**期望**：Recall@200 ≥ 0.90（v2 cold-start subset 应 ≥ 0.85）
**验收标准**：
- [ ] item_index.npy 9K × 32 落盘
- [ ] 召回 + DeepFM 精排的两层 NDCG@10 ≥ 单层 DeepFM NDCG@10（即不退化）
- [ ] Cold-start item subset Recall@200 ≥ 0.85（验证 ColBERT-light 收益）

### 6.2 MMR 重排（Trip 场景，per-period top-3）

| 步骤 | 详细 |
|---|---|
| **6.2.1** | 实现 §3.3.4.5 MMR 公式：`λ * Score(d_i) - (1-λ) * max_j sim(d_i, d_j)` |
| **6.2.2** | sim() 用 cuisine + price + region 联合 multi-hot cosine |
| **6.2.3** | 扫 `λ ∈ {0.5, 0.6, 0.7, 0.8}`，选 best by per-period top-3 cuisine diversity |
| **6.2.4** | 加启发式约束层：同日 cuisine 不重 / 地理紧凑 |

**时间预估**：4-6 小时
**期望**：per-period top-3 cuisine diversity ≥ 0.66
**验收标准**：
- [ ] MMR vs score-greedy ablation 显示 diversity 提升 ≥ 0.20，NDCG@3 下降 < 0.005

---

## §7 Phase 7 — 评测（5/19）

**Owner**：Haobo · **工期**：1 天 · **前置依赖**：Phase 5 + 6 完成

> **v2 评测增量（2026-05-07 加入）**：
> - 加 **Cold-start ITEM subset**（区分 USER cold-start vs ITEM cold-start，验证 ColBERT-light 真正卖点）
> - 加 **v1 vs v2 ablation**（DeepFM 加不加 `item_text_emb_pca32` 对比）
> - 加 **两阶段 retrieval+rerank 联合评测**（Two-Tower top-200 → DeepFM rerank vs DeepFM full 9K）
> - 加 **Sub-cohort breakdown**（NDCG@10 分用户活跃度 / cold-start / cross-city 切片）

### 7.1 Test Split 一次性评测（不可重复！）

| 步骤 | 详细 |
|---|---|
| **7.1.1** | 用 5.4.3 的 final config（v2，含 text_emb），在完全没碰过的 test split 上跑一次 |
| **7.1.2** | **v1 vs v2 ablation**：用 5.4.3 v1 config（没 text_emb）也跑一次，作为对照 |
| **7.1.3** | 计算 §3.4.1 的 9 维度指标：AUC / NDCG@10 / Recall@10 / Precision@10 / Coverage@10 / Gini / Long-tail Recall / Cold-start AUC / Cross-city AUC |
| **7.1.4** | 在 4 个 subset 上分别跑：(a) general test (b) cold-start USER subset (Phase 1 已抽出) (c) **cold-start ITEM subset** (test 里 train 没见过的 business_id，Phase 1 需要补抽) (d) cross-city subset |
| **7.1.5** | 数字写入 §3.4.6 占位表，**不可再调参**（否则 test 失去意义）|

**时间预估**：3-4 小时（v2 + v1 + 4 subsets × 2 models = 8 评测）
**验收标准**：
- [ ] General AUC ≥ 0.83 / NDCG@10 ≥ 0.32（基于 5.2 v1 emb=32 实测，v2 应该差不多或略高）
- [ ] Cold-start USER NDCG@10 衰减 ≤ 0.10（vs general）
- [ ] **Cold-start ITEM v2 NDCG@10 - v1 NDCG@10 ≥ +0.02**（验证 ColBERT-light 价值）
- [ ] Cross-city NDCG@10 衰减 ≤ 0.05（vs general，验证 H8）

### 7.2 (NEW) 两阶段 retrieval + rerank 联合评测

**目的**：验证 production 部署 pipeline（Two-Tower 召回 → DeepFM 精排）vs 直接 DeepFM full-pool brute-force 的精度损失 vs 延迟收益。

| 步骤 | 详细 |
|---|---|
| **7.2.1** | Pipeline A: DeepFM brute-force on 9K → top-10 → NDCG@10 / Recall@10 + latency |
| **7.2.2** | Pipeline B: Two-Tower top-200 → DeepFM rerank → top-10 → 同上 metrics |
| **7.2.3** | 画 Pareto 曲线：Recall@K (K∈{50, 100, 200, 500, 1000}) vs latency p50 |
| **7.2.4** | 报告 trade-off：Pipeline B 损失 X NDCG@10 换 Y× latency 加速 |

**时间预估**：1-2 小时（已经训好的模型，只是 inference）
**验收标准**：
- [ ] Pipeline B NDCG@10 ≥ Pipeline A NDCG@10 - 0.03（损失 < 0.03）
- [ ] Pipeline B latency p50 ≤ Pipeline A latency / 30 (>30× 加速)

### 7.3 Trip 场景评测（4 个 metric，原 7.2）

| 步骤 | 详细 |
|---|---|
| **7.2.1** | 跑 §3.4.4b 的 12 个手工 trip case |
| **7.2.2** | 计算 Trip Diversity / Geographic Compactness / Activity-Restaurant Match / Per-Period Diversity |
| **7.2.3** | 数字填入 §3.4.6 第 5 行 |

**时间预估**：3-4 小时
**验收标准**：
- [ ] Trip Diversity ≥ 0.7
- [ ] Geographic Compactness < 5km
- [ ] Per-Period Diversity ≥ 0.66

### 7.4 (NEW) Sub-cohort breakdown

**目的**：不要只给一个全局 NDCG，按多个独立 cohort 切片，揭示模型在哪类用户/商家上表现好/差。给 Final Report 提供 qualitative analysis 素材。

> **设计 rationale（v2 修订 2026-05-07）**：之前混淆了"test split 内的 Q4 (rc=5-9)" 和 "cold-start (rc<5)"——这俩**不是同一拨人**。Phase 1 把 rc<5 用户**整段 hold out** 到 `coldstart_test_reviews.parquet`，他们**完全不在** `test_reviews.parquet` 里。所以 USER 维度有 4 个**真正独立**的 cohort（test 内 active / test 内 casual / cold-start / cross-city），不能合并成一个 quartile。

| Cohort | 来源 | 模型 user_id 见过？ | 揭示什么 |
|---|---|---|---|
| **7.4.1 test active 用户** (rc≥30) | `test_reviews.parquet` 里 rc≥30 子集 | ✅ train 里大量更新 | 模型上限——active 用户的 NDCG 是天花板 |
| **7.4.2 test casual 用户** (5≤rc<30) | `test_reviews.parquet` 里 rc=5-29 子集 | ✅ train 里少量更新 | active vs casual 差距 → user_id emb 长尾问题（关联 5.5 ablation） |
| **7.4.3 cold-start 用户** (rc<5) | `coldstart_test_reviews.parquet`（Phase 1 整段 hold out，119K 用户 / 141K reviews） | ❌ **从未在 train 见过 user_id**，emb 仍是初始值 | **H7 验证**：完全冷启动衰减多少 |
| **7.4.4 cross-city 旅行者** | `crosscity_test_reviews.parquet`（Phase 1 整段 hold out，5,250 用户 / 52K reviews） | ❌ 同上 | **H8 验证**：跨城泛化，决定 F2 trip mode 可行性 |
| **7.4.5 ITEM 活跃度（quartile）** | 按商家 `review_count` 分 Q1 (rc≥100) / Q2 (30–99) / Q3 (10–29) / Q4 (<10，cold-start ITEM) | — (这是 item 维度) | Q4 是 ColBERT-light 真正用武之地——**v2 vs v1 在 Q4 上的差距**是核心证据 |

**时间预估**：1-2 小时（同 7.1 的 inference 复用，多加切分 + 表格代码）
**输出**：5 行 breakdown 表 + 可选的 (USER cohort × ITEM quartile) 5×4 heatmap，整段 paragraph error analysis 可直接放进 Final Report

**关键比较**：
- 7.4.1 vs 7.4.2：揭示 user_id emb 在 head/tail 之间的过拟合差距
- 7.4.1 vs 7.4.3：揭示完全 OOV 时模型损失多少（H7 假设）
- 7.4.5 v1 vs v2：揭示 ColBERT-light 是不是真的救了 cold-start ITEM

### 7.5 图表生成（原 7.3）

| 图表 | 用途 |
|---|---|
| Learning curve（train/val AUC vs epoch）| Criterion 5（overfit/underfit check） |
| Hyperparam sweep heatmap（dropout × L2）| Criterion 6 |
| **v1 vs v2 ablation 对比表（含 cold-start ITEM 行）** | Criterion 7 — ColBERT-light 价值证据 |
| **Two-stage retrieval Pareto 曲线（Recall vs latency）** | Criterion 7 — 工业向 trade-off 卖点 |
| 5-row ablation 比较表（MF / FM / DeepFM v1 / DeepFM v2 / Two-Tower→DeepFM v3） | Criterion 7（对应 §3.4.6） |
| **Sub-cohort breakdown bar chart** | Criterion 7 — qualitative analysis |
| Trip Diversity 对比 score-greedy vs MMR | Criterion 7 / H10 |

**输出**：`reports/figures/*.png` 至少 7 张
**时间预估**：3-4 小时

---

## §8 Phase 8 — Agent 集成 + Demo（5/20 – 5/21）

**Owner**：Haobo（主） + Zimeng + Cindy（Likert 打分） · **工期**：2 天 · **前置依赖**：Phase 7 完成

### 8.1 LLM Agent 集成（按 §3.2 v2 S1-S10 场景）

| 步骤 | 详细 |
|---|---|
| **8.1.1** | 写 `scripts/agent.py`：实现 §3.2.2 的 3-step pipeline + 5 个 tool（recommend_restaurants / plan_trip / get_restaurant_detail / summarize_reviews_for_overview / modify_trip_slot）|
| **8.1.2** | 用 Anthropic SDK + claude-sonnet-4-6，按 §3.2.2 prompts 实装 |
| **8.1.3** | 单元测 S1-S10 场景至少各 1 个 case，确认输出 schema 正确 |

**时间预估**：8-10 小时
**验收标准**：
- [ ] 全 10 场景跑通无报错
- [ ] tool dispatch 准确率 ≥ 85%（手工 50 utterance 验证）

### 8.2 Persona Demo 数据准备

| 步骤 | 详细 |
|---|---|
| **8.2.1** | 在 Yelp 训练集中找 3 个匹配 Haobo 偏好的 user_id（Philadelphia / brunch / $$）|
| **8.2.2** | 锚定这 3 个 user_id 作为 demo 帧 3 的 persona |
| **8.2.3** | 预计算这 3 个用户的 top-10 推荐输出 |

**时间预估**：2-3 小时

### 8.3 Streamlit Demo 集成

| 步骤 | 详细 |
|---|---|
| **8.3.1** | 写 `scripts/demo_app.py`：3 屏 F1 / F1.1 / F2 |
| **8.3.2** | F1 调 agent，渲染卡片；F1.1 调 get_restaurant_detail；F2 调 plan_trip |
| **8.3.3** | 录 3 帧 demo 视频（S0 / S1 / Persona）|

**时间预估**：8-12 小时
**验收标准**：
- [ ] Demo 端到端跑通无 crash
- [ ] 3 帧脚本流畅可视化

### 8.4 Agent Layer 评测（Likert 打分）

| 步骤 | 详细 |
|---|---|
| **8.4.1** | Haobo 标注 50 utterance 作 intent / tool 分发 gold |
| **8.4.2** | 自动跑 agent，对比 F1 / exact match |
| **8.4.3** | 抽 30 输出 → Haobo + Zimeng + Cindy 各自 5-point Likert 打分（5 维度）|
| **8.4.4** | 数字填入 §3.4.4 |

**时间预估**：每人 1-2 小时
**验收标准**：
- [ ] Intent F1 ≥ 0.85
- [ ] Tool dispatch ≥ 0.90
- [ ] Likert 各维度均值 ≥ 3.8

---

## §9 Phase 9 — Writeup + Rubric 自检（5/22）

**Owner**：Haobo · **工期**：1 天 · **前置依赖**：Phase 7 + 8 完成

### 9.1 Final Report 撰写

| 章节 | 来源 | 工时 |
|---|---|---|
| 1. Problem Statement | 抄 PRD §1 | 0.5h |
| 2. Hypotheses | 抄 PRD §3.3.1（10 条 H1-H10）+ 加实验结果 | 1h |
| 3. EDA | Zimeng+Cindy notebook 总结 + 8 张图 | 1.5h |
| 4. Feature Engineering | 抄 PRD §3.3.3 26 特征表 | 0.5h |
| 5. Approaches + overfit/underfit | DeepFM 架构 + sweep 结果 + 学习曲线 | 2h |
| 6. Solution + regularization | 最终 config 表 + dropout/L2 heatmap | 1h |
| 7. Results + Learnings | §3.4.6 5-row 比较表（MF/FM/DeepFM/Two-Tower→DeepFM/+MMR trip）+ ablation + 6 bullet learnings（含 H9/H10）| 2h |
| 8. Future Work | online A/B / GRU4Rec / xDeepFM / 真实 trip 数据 | 0.5h |
| **Total** | | **9h** |

**输出**：`reports/final_report.md`（用 pandoc 转 PDF）

### 9.2 Rubric Layer C 自检

按 §3.4.5 8-criterion 自检表逐项过：
- [ ] 1. Problem Statement — 100%
- [ ] 2. Hypotheses — 10 条 H1-H10 + 实验数字
- [ ] 3. EDA — 8 张图 + 段落
- [ ] 4. Feature Engineering — 26 特征表
- [ ] 5. Approaches + overfit/underfit — DeepFM + sweep + learning curve
- [ ] 6. Solution + regularization — final config + dropout/L2 heatmap
- [ ] 7. Results + Learnings — 5-row 比较表（§3.4.6）+ ablation + learnings（H9/H10 覆盖）
- [ ] 8. Future Work — bullet list

### 9.3 提交准备（5/22 晚）

| 物件 | 来源 |
|---|---|
| `final_report.pdf` | 9.1 输出 |
| `notebooks/*.ipynb` | 7 个 notebook 全部跑通无 error |
| `models/deepfm_final.pt` | Phase 5 输出 |
| `demo_video.mp4` | Phase 8 录制 |
| `README.md` | 简短说明 + 文件索引 |

---

## §10 Phase 10 — 提交（5/23 周六）

**Owner**：Haobo · **工期**：0.5 天

| 步骤 | 详细 |
|---|---|
| **10.1** | Canvas 上传 final_report.pdf + notebooks 压缩包 + demo 视频链接 |
| **10.2** | 二人交叉核对（Zimeng 或 Cindy）所有交付物在 Canvas 提交记录里 |
| **10.3** | Done. 庆祝 |

---

## §11 风险登记 + 应急预案

| # | 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|---|
| R1 | Colab T4 配额不够 sweep 全跑完 | 中 | 高 | 用本地 M3 Pro MPS 接续；或砍 sweep grid 到 3×3 |
| R2 | DeepFM 训练不收敛 | 低 | 高 | 检查 feature pipeline；fallback 用 FM-only |
| R3 | EDA 卡到 5/13 没出 cuisine_vocab | 中 | 中 | Haobo 自己跑 raw business.json top-50 当临时 vocab |
| R4 | Two-Tower 5/19 仍未跑通 | 高 | 低 | **影响范围限于 S1 push 路 demo 加速**——S1 降级走"地理+时间硬过滤"DeepFM 直精排（延迟 100-300ms 仍可演示）；S2/S6 CRS 路完全不受影响。Two-Tower 写入 §6 Future Work，不影响 ML2 评分主战场（rubric 评分对象是 DeepFM 精排，不评 Layer-1 召回方案）|
| R5 | Streamlit demo 5/21 没集成完 | 中 | 中 | 降级为 Jupyter notebook demo + 录屏 |
| R6 | LLM agent 成本爆 | 低 | 中 | 降级 Sonnet → Haiku（Step 1 intent 抽取） |
| R7 | Phase 5 sweep 实际跑了 30h（超预期）| 中 | 高 | 砍 Stage B grid 到 3×3 = 9 组；保 final config 训练时间 |

## §12 每日 checkpoint checklist

每天结束前过一遍：

- [ ] 今日 Phase 子任务完成？
- [ ] 输出文件落盘 + commit / 备份？
- [ ] 任何 blockers 记到 `notebooks/blockers.md`？
- [ ] 明日第一件事是什么？
- [ ] EDA / 模型训练有没有跑出超预期 / 反预期数字？（写进 §3.4.7 Learnings 草稿）

---

<!-- training pipeline plan · 2026-05-05 -->
