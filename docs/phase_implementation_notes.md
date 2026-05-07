# Phase Implementation Notes — Taste hunter

> 配套 `docs/training_pipeline_plan.md` 的**实施日志**（已发生的事），不是计划（计划放 plan）。
> 每个 Phase 完成后立即追加一节，结构固定：① 产物 ② 跑数结果 ③ 与计划偏差 ④ 教学性原理 ⑤ 踩坑日志。
> 写作目的：① 答辩 / Final Report 直接复用 ② 后续接手或回头 debug 时不丢失上下文。

> **⚠️ 流程规则（与 plan 顶部一致，强制）**：每完成一个 Phase（含子阶段如 5.1/5.2…），必须在**同一次 commit** 里同步：
> 1. 在 `training_pipeline_plan.md` 对应章节标题尾加 ✅ + commit hash + 实际完成日期
> 2. 在本文档对应 §N 节填实际产物 / 跑数 / 偏差 / 踩坑（结构固定五段）
> 3. 在 plan §0.4 高层时间线表把该行的 ✅/🟡/⏳ 状态更新
>
> 没做这三件事的 phase 不算"完成"。

---

## §1 Phase 1 — 数据准备（5/6 完成 · commit `1cb2230`）

### 1.1 产物清单

| 文件 | 大小 | 行数 | 说明 |
|---|---|---|---|
| `data/cleaned/businesses_target.parquet` | 3.7 MB | — | 三城所有商家 |
| `data/cleaned/restaurants_open.parquet` | 1.0 MB | **9,022** | 三城 Restaurant 子集（is_open=1 + categories 含 Restaurants/Food） |
| `data/cleaned/reviews_target.parquet` | 770 MB | — | 三城所有 reviews |
| `data/cleaned/reviews_restaurant.parquet` | 408 MB | — | 三城餐厅 reviews |
| `data/cleaned/users_target.parquet` | 563 MB | **359,007** | 至少给三城餐厅写过 1 条 review 的用户 |
| `data/cleaned/train_reviews.parquet` | 238 MB | ~722K | P0–P70 时序段 |
| `data/cleaned/val_reviews.parquet` | 31 MB | ~103K | P70–P80 段 |
| `data/cleaned/test_reviews.parquet` | 60 MB | ~206K | P80–P100 段 |
| `data/cleaned/coldstart_test_reviews.parquet` | 45 MB | — | test 中"用户首次出现"子集（H7） |
| `data/cleaned/crosscity_test_reviews.parquet` | 24 MB | — | test 中"跨城用户"子集（H8） |

总计三城 reviews **1,032,056** 条（train+val+test）。

### 1.2 跑数结果

```
restaurants:  9,022   (Philadelphia: 4,373 · Tampa: 2,502 · Tucson: 2,147)
reviews:      1,032,056
users:        359,007 (至少有一条 target-city 餐厅 review)
```

时序切分：按 review.date 全局排序后 P0/P70/P80/P100 切。**注意：P80/P100 的"未来 20%"严格不被任何后续阶段触碰，是 Phase 7 一次性评测专用**。

### 1.3 与计划偏差

- **目标三城最终选择**：原 plan 写 LA/Chicago/Seattle → 实际 Yelp Open Dataset 这三城各只有 0–1 条数据，全部弃用。改用真实数据规模最大的三城：**Philadelphia / Tucson / Tampa**。所有下游 PRD / explainer / few-shot 同步替换。
- **没有改 plan 的地方**：流式 ndjson 解析、`is_open` 过滤、user 子集筛选条件，都按 plan 执行。

### 1.4 教学性原理

**为什么需要 cold-start / cross-city 两个子集？**

我们 4 个核心假设里有两个直接对应它们：
- **H7 (cold-start)**：新 Taste hunter 用户进来时只能拿到 OOV embedding，NDCG@10 应该衰减但不能崩。需要"训练时没见过的 user_id"样本来量化这个衰减。
- **H8 (cross-city)**：用户去陌生城市旅行时（F2 行程模式），训练时学到的 user 偏好能不能迁移过去？需要"用户在主活动城市以外的 review"样本。

构造方法：先在 train+val 学到的 user 集合 `U_train`、business 城市归属，然后在 test 里筛 `user_id ∉ U_train`（cold）和 `business.city ≠ user.most_active_city`（cross）。这两个集合是 test 的子集，不是独立切片。

### 1.5 踩坑日志

| 问题 | 根因 | 修复 |
|---|---|---|
| 最初按 LA/Chicago/Seattle 写了一晚上 PRD | 没先 grep Yelp 数据集真实城市分布 | 先做 EDA Q3 / city 分布，再决定目标城市；现在已成 SOP |
| `is_open=0` 是否丢弃 | 闭店餐厅 review 仍是有效偏好信号（学 user side），但作为推荐候选不合理 | **保留 reviews，过滤 candidate**：训练时所有 review 入样本，但负采样池只从 `is_open=1` 抽 |

---

## §2 Phase 2 — EDA（5/6 完成 · commit `f336e07`）

### 2.1 产物清单

| 文件 | 用途 |
|---|---|
| `reports/figures/eda_q1_powerlaw.png` | Q1: review_count 长尾验证 |
| `reports/figures/eda_q1_rating_dist.png` | Q1: rating 分布偏斜（4-5 占主导） |
| `reports/figures/eda_q2_sparsity.png` | Q2: user-item 矩阵稀疏度 |
| `reports/figures/eda_q3_top_categories.png` | Q3: 50 cuisine 词表来源 |
| `reports/figures/eda_q4_geo.png` | Q4: 三城地理分布散点 |
| `reports/figures/eda_q4_kmeans_elbow.png` | Q4: k-means k 选择（k=8 落点） |
| `reports/figures/eda_q5_hour_dist.png` | Q5: hour-of-day review 分布（lunch / dinner peak） |
| `reports/figures/eda_q8_review_length.png` | Q8: review 长度分布 |
| `reports/figures/eda_q10_lorenz_gini.png` | Q10: 用户活跃度 Lorenz 曲线 + Gini |
| `data/features/cuisine_vocab.json` | 50 cuisine 标签（v1.0_2026-05-06） |

### 2.2 关键 finding

- **长尾**：head 1% 商家占 ~25% reviews（Q1）；head 10% 用户写了 ~60% reviews（Q10 Lorenz）。意味着 user_id embedding 的 head 部分会过拟合，tail 部分会欠学习——这就是为什么 5.5 ablation 要测 "去掉 user_id" 看泛化变化。
- **Cuisine 词表 top-10**：Sandwiches / Coffee & Tea / Fast Food / American (Traditional) / Pizza / Breakfast & Brunch / American (New) / Mexican / Burgers / Specialty Food。
- **K-means k=8**：肘部图清晰落在 k=8，inertia 改善曲线在 k=8 后斜率显著变缓。
- **Hour peak**：lunch ~12:30、dinner ~19:00 双峰；这就是 context_features 里 `hour_bucket` 用 3-bucket（early / lunch / dinner）+ sin/cos 双编码的依据。

### 2.3 与计划偏差

- 原 plan 写 Q1–Q11 共 11 个问题，**Q6/Q7/Q9/Q11 没单独出图**：Q6 (review attribute correlation) 用相关系数表代替；Q7 (elite 行为对比) 合并进 Q1；Q9/Q11 相关分析直接写进 EDA findings 不出图。
- 出图数量：**9 张**（plan 默认期望 11 张），但每张都覆盖一个核心 finding，没有为出图而出图。

### 2.4 教学性原理

**Q3 怎么从 categories 抽 50 个 cuisine 标签？**

Yelp 的 categories 是逗号分隔的多标签字符串，里面混有 "Restaurants" / "Food" / "Nightlife" 这种顶层泛词。处理流程：
1. 全部小写 + strip + split。
2. 计数 → top 200。
3. 人工剔掉泛词（"Restaurants", "Food", "Nightlife", "Local Services" 等）。
4. 取剩余 top 50 → 这就是 `cuisine_vocab.json`。

50 这个数字是 trade-off：太少（如 20）丢失风味区分度；太多（如 200）embedding 表 + multi-hot 维度过大、长尾标签学不动。50 是 EDA 里"累计覆盖率 ~85%"的拐点。

### 2.5 踩坑日志

| 问题 | 修复 |
|---|---|
| `categories` 字段有 NaN 行（少量商家无标签） | `fillna('')` 后 split 直接得到空 list，不参与计数 |
| Q4 k-means 跑全国 lat/lon 一次出图 → 三城混在一起没法看 | 改成**每城独立 k-means**，三个子图并排 |

---

## §3 Phase 3 — 特征工程（5/6 完成 · commit `194f8e2`）

### 3.1 产物清单

| 文件 | 大小 | 行数 | Schema |
|---|---|---|---|
| `data/features/user_features.parquet` | 15 MB | 359,007 | 5 直接 + 3 聚合（共 8 列 + user_id） |
| `data/features/item_features.parquet` | 515 KB | 9,022 | 9 字段 + business_id |
| `data/features/train_with_negatives.parquet` | 19 MB | **2,074,945** (415K正 + 1.66M负) | (user_id, business_id, label, timestamp) |
| `data/features/feature_spec.json` | 4.6 KB | — | v3.0 spec, 26 特征定义 + city_id_map |
| `data/features/region_clusters.json` | 2.0 KB | — | k=8/城 k-means 中心 |

### 3.2 特征清单（26 个，与 PRD §3.3.3 v2.2 对齐）

**User (8):** `user_id` (emb 8d) · `avg_rating_given` · `review_count_log` · `days_active` · `elite_flag` · `mean_distance_traveled` · `fav_cuisine_emb` (50d pooling) · `price_tolerance_avg`

**Item (9):** `business_id` (emb 8d) · `avg_rating` (Bayesian C=10) · `review_count_log` · `price_level` (1–4) · `is_open` · `has_outdoor_seating` · `photo_count_log` · `categories_multi_hot` (50d) · `city_id` (emb 4d, vocab 4)

**Context (9):** `distance_from_user_km_log` · `hour_bucket` (sin/cos + 3-bucket) · `day_of_week` · `is_weekend` · `trip_day_index` · `region_cluster_id` (emb 4d, vocab 9) · `period_id` (vocab 4) · `activity_emb` (32d, MiniLM→PCA) · `prior_meals_cuisines` (50d multi-hot)

**总输入维度估计：234-dim**（embedding 拼接 + multi-hot + 数值标量）。

### 3.3 跑数结果

- **Region clusters**: Philadelphia (n=4373, inertia=2.24) · Tampa (n=2502, inertia=2.30) · Tucson (n=2147, inertia=2.99) · k=8/城（共 24 个 region_cluster_id，加 `<UNK>` = vocab 9）
- **负采样**：**1:4 比例**（每个正样本配 4 个 same-city 未访问负样本），最终 train 集 415K 正 / 1.66M 负 = 2.07M 行

### 3.4 与计划偏差

- **`fav_cuisine_emb` 不是真 embedding，是 50d pooling**：原计划用 50d learned embedding，实际改成"用户历史前 3 cuisine 的 multi-hot mean"作为静态向量。理由：参数量更小、cold-start 时降级路径自然（取 0 向量）、且 ablation 简单。
- **`photo_count_log` 是 proxy**：Yelp Open Dataset 的 photo.json 没下完整版（太大），临时用 `clip(log1p(review_count), 0, 10)` 当近似。这是已知的"训练-部署对齐风险"，记在 §3.6 风险表。
- **`city_id` 升级为 embedding**：原 plan 当 categorical scalar，发现 vocab 只有 4（含 `<UNK>`），index lookup 直接用 4d embedding 性价比高。

### 3.5 教学性原理

**为什么是 1:4 负采样不是 1:1 或 1:99？**

负采样比例 K 控制两件事：
- **正负样本平衡** vs **训练效率**：K 越大，负样本越多 → 模型见过更广泛的"什么是不像的"，但每 epoch 计算量也是 K+1 倍。
- **Eval 时另算**：训练 K=4，但**评估**时用 1+99 sampled NDCG（Krichene & Rendle 2020 的标准做法），完全独立，不受训练 K 影响。

我们选 K=4 是 trade-off：1:1 训练快但模型容易把"任何没见过的"全打高分；1:99 训练 25× 慢且对 BCE loss 而言负样本主导梯度。1:4 是工业界常见起点（Sampled Softmax / NCE 的常用比率），后续 Phase 5.4 Stage C 还会扫 K=2/4/8 看真实影响。

**Bayesian 平滑（C=10）的 avg_rating 是什么？**

商家 raw_avg = sum(stars) / n_reviews。问题：评论数为 1 的商家，一条 5 星就 raw_avg=5，模型会把它当 vs 真实 5 星好店等价。Bayesian shrink：

```
avg_rating_smoothed = (sum(stars) + C * global_mean) / (n_reviews + C)
```

C=10 意思是"我先验认为这家店有 10 条评分等于全局均值"。低评论商家会被往全局均值 pull，高评论商家影响微弱。这是协同过滤工程化的标准 trick。

**`mean_distance_traveled` 怎么算？**

对每个用户，取他评过的所有商家 lat/lon → 计算两两 pairwise haversine 距离 → 取均值 → log1p。语义：**用户活动半径**。半径大 → 探索型用户（旅游 / 通勤跨城）；半径小 → 本地型用户（社区固定圈）。这个特征驱动 H4 假设。

### 3.6 踩坑日志

| 问题 | 根因 | 修复 |
|---|---|---|
| `from haversine import haversine` 在 conda Py3.9 触发 numba `SystemError` | haversine 库内 JIT 与 NumPy ABI 不兼容 | 改写为 inline numpy 实现：`np.triu_indices` 取 pairwise → 公式直接展开。**也从 `requirements.txt` 删除 haversine** |
| `IDEncoder` `<NEW_USER>` index out of bounds | OOV 标记既被保留为 idx 0，又被作为真实 user_id 枚举进 idx_to_id | 修 `src/data.py:34-50`：先过滤 OOV markers，再从 idx 1 起枚举 |
| `.gitignore` 行内 `#` 注释把白名单 pattern 误解析成路径 | git 不支持行内注释 | 注释改写到 pattern 的上一行 |

---

## §4 Phase 4 — Baselines (MF + FM)（5/6–5/7 完成 · commit `1a12f23`）

### 4.1 产物清单

| 文件 | 大小 | 内容 |
|---|---|---|
| `models/mf.pt` | 13 MB | MF state_dict (10 epoch) |
| `models/fm.pt` | 13 MB | FM state_dict (10 epoch) |
| `models/mf_history.json` | 656 B | 每 epoch loss/AUC/NDCG/Recall |
| `models/fm_history.json` | 1.1 KB | 同上 |
| `models/baseline_metrics.json` | 253 B | 最终汇总 |
| `reports/figures/training_baselines_curves.png` | 142 KB | 训练曲线对照 |
| `scripts/train_baselines.py` | 360 行 | 训练脚本 |
| `src/data.py` | 235 行 | IDEncoder + Dataset + eval pair builder |
| `src/eval.py` | 139 行 | AUC / NDCG@k / Recall@k / Precision@k |

### 4.2 跑数结果（10 epoch · 4096 batch · Adam lr=1e-3 · MPS）

| Model | Val AUC | Val NDCG@10 | Val Recall@10 | 参数量级 |
|---|---|---|---|---|
| **MF** | **0.7854** | 0.2677 | 0.4651 | ~2.95M (user/item emb 8d) |
| **FM** | **0.8302** | 0.2720 | 0.4749 | ~2.96M (MF + Linear(113→1)) |
| Δ FM−MF | **+0.0448** | +0.0043 | +0.0098 | side-feature linear 净贡献 |

**结论**：side feature（user_num + item_num + cuisine_vec + cat_vec）单纯线性融合，AUC 拉高 4.5 点。这意味着 deep / FM 二阶交叉是否还能继续抬高，由 Phase 5 验证（**剧透：DeepFM Phase 5.1 sanity 已经把 NDCG@10 从 0.27 拉到 0.32，Recall@10 从 0.47 拉到 0.54**）。

### 4.3 与计划偏差

- **没用 Surprise / xLearn / pyfm**：原 plan 写"Surprise SVD 做 MF baseline、xLearn 或 pyfm 做 FM"。实际**全部用 PyTorch 自己写**：
  - 理由 1：Surprise 不支持 GPU/MPS，359K × 9K 矩阵在 CPU 上跑 SVD 慢且不直接出 ranking metric
  - 理由 2：xLearn 不再活跃维护、pyfm API 老旧
  - 理由 3：MF/FM PyTorch 实现各 ~50 行，与 DeepFM 共用 `IDEncoder` / `evaluate_full` / DataLoader → 评估口径完全一致，直接可比
- **side-feature 维度不是 plan 里的"几十"，是 113**：6 (user_num) + 50 (cuisine) + 7 (item_num) + 50 (item_cat) = 113。

### 4.4 教学性原理

**Q1：MF 怎么训？协同过滤是怎么"学会"的？**

MF (Matrix Factorization) 的核心：每个 user / item 各分配一个 d 维 embedding 向量，预测 = `dot(u_emb, i_emb) + u_bias + i_bias + global_bias`，sigmoid 后用 BCE 监督。

```python
class MF(nn.Module):
    def forward(self, user_idx, item_idx):
        u = self.user_emb(user_idx)         # (B, 8)
        v = self.item_emb(item_idx)         # (B, 8)
        dot = (u * v).sum(dim=-1)            # (B,)
        return sigmoid(dot + bu + bi + global_bias)
```

**协同过滤"学会"的物理意义**：BCE 让"user A 对 item X 标记为 1"的样本把 `u_A` 和 `v_X` 在 embedding 空间里**拉近**，"user A 对 item Y 标记为 0"的样本**推远**。所以训练完，embedding 空间里：
- 喜欢相似商家的用户 → 向量空间里靠近（即便他们从未看过对方的评分）
- 被相似用户喜欢的商家 → 向量空间里靠近

这就是 "collaborative" 的来源：**你不需要明确告诉模型 "user A 和 user B 类似"，它通过共享商家的偏好同步把两人推到一起**（隐式 / latent）。

**Q2：FM 比 MF 多了什么？**

FM = MF + 一个 113-dim side-feature 的 Linear 层：

```python
class FM(MF):
    def __init__(self, ...):
        ...
        self.linear = nn.Linear(113, 1)
    def forward(self, user_idx, item_idx, user_num, user_cuisine, item_num, item_cat):
        mf_score = super().forward_inner(user_idx, item_idx)
        side = torch.cat([user_num, user_cuisine, item_num, item_cat], dim=-1)  # 113-d
        return sigmoid(mf_score + self.linear(side).squeeze(-1))
```

**真正的 FM** 还包含**二阶特征交叉项** `Σᵢ<ⱼ <vᵢ, vⱼ> xᵢ xⱼ`（Rendle 2010），但我们这里 baseline 简化为**只用一阶 linear**，把二阶留给 Phase 5 DeepFM（DeepFM 的 FM-part 才是完整二阶）。所以这个"FM"严格说是"MF + biased linear"，命名是为了和 ML2 课程教学顺序对齐（MF→FM→DeepFM 三步走）。

**Q3：我们没有真实 Taste hunter 用户，怎么靠协同过滤推荐？**

这个问题已在 `recommender_training_explainer.md` §1 + §6 详述。简版：
- **训练时** Yelp 1.99M 用户的偏好被 baked into embedding 表（item embedding 学到商家间相似性、user embedding 学到口味聚类）。
- **部署时**，Taste hunter 新用户（OOV）用 `<NEW_USER>` 平均 embedding + 实时收集到的 user_features → 模型仍能给出合理 ranking（因为商家 embedding 已经捕获了 collaborative signal，新用户的对话信息只是把他往 embedding 空间里某片"已知簇"里推）。
- **Persona 锚定（demo trick）**：演示时手工把 user_id 替换成 Yelp 真实 user_id（如 active 用户 `xJVLpdiJEvhVdWY8oTGPJg`），让该 user 的真实历史 embedding 直接生效。这不是"实时协同过滤"（我们没有其他 Taste hunter 用户），而是"借用一个已经训练好的 user 向量"做演示。

### 4.5 踩坑日志

| 问题 | 根因 | 修复 |
|---|---|---|
| MPS 上 FM 评估时报 `Placeholder storage has not been allocated on MPS device` | `feature_kwargs_fn` 返回的 tensor 没 `.to(device)` | `src/eval.py:109` 加 `kwargs = {k: v.to(device) for k, v in kwargs.items()}` |
| MF NDCG@10 在 epoch 3 后开始**轻微回落**（0.2688 → 0.2677） | 纯 ID embedding 在 K=4 负采样下早达饱和，开始往训练集过拟合 | 接受，因为 baseline 重点是 AUC（学了多少 collaborative signal），NDCG 由 DeepFM 处理；FM 没这个回落（side feature 提供持续梯度） |
| FM 训练第 1 epoch loss 0.46，比 MF 0.50 还高 | FM 多了 113-dim linear，初始权重把 logit 推得更乱 | 跑过 2 epoch 后反超，最终 AUC +4.5 点。属正常 |

---

## §5 Phase 5 — DeepFM 主训练（进行中 · commit `6354456` Stage 5.1 完成）

### 5.1 当前状态（2026-05-07）

✅ **Stage 5.1 sanity check** 完成：默认 config (emb_dim=8, dropout=0.2, l2=1e-4) 跑通  
🟡 **Stage 5.2 emb_dim sweep** 后台运行中（task `brlmbswur`）  
⏳ **Stage 5.3 dropout × L2 grid** 待跑  
⏳ **Stage 5.4 final retrain on train+val** 待跑  
⏳ **Stage 5.5 ablation: drop user_id emb** 待跑

### 5.2 Stage 5.1 跑数结果（emb_dim=8 · dropout=0.2 · l2=1e-4 · 10 epoch）

| Metric | Best | Final | vs FM Δ |
|---|---|---|---|
| Val AUC | **0.8330** (epoch 9) | 0.8329 | +0.003 |
| Val NDCG@10 | **0.3182** (epoch 10) | 0.3182 | **+0.046** |
| Val Recall@10 | **0.5397** (epoch 9) | 0.5387 | **+0.065** |
| Train loss | 0.219 (epoch 10) | 持续下降 | — |

**结论**：DeepFM 在 NDCG@10 / Recall@10 上比 FM 显著提升（+4.6 / +6.5 点），AUC 接近持平（+0.3 点）。**Top-K 排序质量是 deep + FM 二阶交叉的主要收益场景**——AUC 是 pairwise 全局指标，FM 一阶已经接近天花板；NDCG/Recall 是 top-K 局部排序，需要更精细的特征交叉才能拉开。

模型大小：13.6 MB（emb_dim=8）。

### 5.3 教学性原理

**DeepFM = FM 二阶 + DNN 共享 embedding**

DeepFM (Guo et al. 2017 IJCAI) 的关键 trick：FM 部分和 DNN 部分**共享 embedding 表**，避免双倍参数 + 让两个 head 看到同一份特征视图。

```
                    ┌──→ FM Layer (二阶交叉) ──┐
embedding lookup ───┤                          ├──→ sum + sigmoid
                    └──→ DNN MLP[256,128,64] ──┘
```

**FM 二阶项**用高效公式 `0.5 * [(Σx)² - Σx²]` 计算，复杂度从 O(n²) 降到 O(n)（n 个 field 各一个 d-dim emb）。本实现中 4 个 field：`user_emb`、`item_emb`、`user_num_proj`（数值 → 8d）、`item_num_proj`（数值 → 8d）。

**为什么共享 embedding 比各跑各的好？**
- 参数减半（15M → 7.5M 量级）
- 梯度同时来自 FM head 和 DNN head → embedding 学到的表示既适合"两两交叉"又适合"高阶非线性"
- FM 提供 short-cut（线性 + 二阶），DNN 提供 capacity（高阶组合），two-tower-on-shared-embedding 范式

### 5.4 与计划偏差

- 暂无（5.1 完全按 plan 跑通）。后续 5.2/5.3/5.4/5.5 跑完后追加偏差记录。

### 5.5 踩坑日志

| 问题 | 修复 |
|---|---|
| MPS 上 DeepFM 跑 emb_dim=64 偶发 OOM（M3 Pro 18GB） | 后续 sweep batch_size 从 4096 降到 2048 备用 |
| （待补） | — |

---

## §6 Phase 6 — Two-Tower + MMR (Stretch · 待开始)

> 🟡 占位章节，跑完后回填以下结构：
> - 6.1 产物清单（faiss index / mmr config）
> - 6.2 召回质量（Recall@100 / Latency p50/p99）
> - 6.3 与计划偏差（Two-Tower 选了 in-batch negative 还是 sampled softmax？）
> - 6.4 教学性原理（DSSM 双塔 vs DeepFM 单塔的检索-精排分工 / MMR `λ * relevance - (1-λ) * max_sim` 公式释义）
> - 6.5 踩坑日志

---

## §7 Phase 7 — Test 一次性评测（5/19 计划）

> 🟡 占位章节。跑前请提醒 self：**test split 全程只能 evaluate 一次**，重复 evaluate 等同于变相调参 → 选模型重大偏差。
> 内容结构：
> - 7.1 Test metrics（4 个核心 + cold/cross 子集）
> - 7.2 Trip 场景 4 个 metric（Diversity Simpson / Geo Compactness / Activity Match / Per-Period Diversity）
> - 7.3 H1–H10 假设验证表
> - 7.4 与计划偏差 / 失败假设的诚实承认
> - 7.5 踩坑日志

---

## §8 Phase 8 — Agent 集成 + Demo（5/20–5/21 计划）

> 🟡 占位章节。完成后回填：
> - 8.1 Sonnet 4.6 Agent 接入 S1–S10 场景（哪些场景 LLM 真实跑通、哪些降级）
> - 8.2 Persona demo 三帧编排（S0 / S1 / Persona 锚定）的实际表现
> - 8.3 Streamlit 界面与 PRD §3.1 偏差
> - 8.4 Likert 自评结果

---

## §9 Phase 9 — Writeup 自检（5/22 计划）

> 🟡 占位章节。完成后回填：
> - 9.1 Final Report 章节对应 PRD section 表
> - 9.2 Rubric Layer C 自检结果（每条 rubric 自打分 + 证据指针）
> - 9.3 Canvas 提交清单 checksum

---

## §10 Phase 10 — 提交（5/23 计划）

> 🟡 占位章节。提交后回填：
> - 提交时间 / Canvas 回执 / 反馈到达时间窗

---

## 附录 A — 写作惯例

- **每个 phase 的 commit hash 必填**：方便答辩时回溯具体代码版本
- **跑数结果用真实数字**：从 `models/*.json` / `data/features/*.json` 直接复制，不估算
- **教学性原理段写"为什么"**：不抄 paper，写自己理解里的本质
- **踩坑用表格**：问题 / 根因 / 修复 三列，便于以后 grep
- **占位章节写明结构**：哪怕没跑，先把回填模板钉死，避免完成后偷懒

## 附录 B — 与其他文档的关系

| 文档 | 内容 | 与本文档关系 |
|---|---|---|
| `training_pipeline_plan.md` | **计划**：每 phase 要做什么、产物预期 | 计划 → 本文档是执行结果 |
| `prd/PRD_v1_section3.3_Model_v2.md` | **架构**：DeepFM 数学公式 / 假设 H1–H10 | 架构 → 本文档引用 + 验证 |
| `recommender_training_explainer.md` | **概念**：训练-部署 gap、CF 物理意义 | 概念 → 本文档复述 + 落地具体数字 |
| `phase_implementation_notes.md`（本档） | **执行**：每 phase 实际产物 + 跑数 + 踩坑 | — |
