# Recommender Training Explainer — Taste hunter

> **创建**：2026-05-05
> **定位**：独立 reference / 信息文档，不在 PRD 主体里。供团队回顾"无真实用户数据如何训练推荐系统"这一核心方法学问题用。
> **链接到**：`PRD_v1_section3.3_Model_v2.md` §3.3.0.5（PRD 里只放 1 段 stub，详细讨论全部在这里）。
> **读者前置背景假设**：熟悉搜索产品的 ranking pipeline（双塔 / 倒排拉链 / LTR）；本文用搜索域 mental model 桥接到推荐场景。

---

## 0. 一句话答案

**我们用 Yelp Open Dataset 的 ~199 万历史用户 + 699 万 review + 15 万商家作为训练 population——这就是我们的"训练样本"。Taste hunter 应用本身不需要任何真实用户数据即可完成 ML2 评分要求的所有 metric**。Yelp 历史用户在训练阶段扮演"代理用户"（proxy users）的角色，DeepFM 在他们身上学协同信号 + 内容信号；**关键是模型学到的是"具有 X 类 user features 的用户偏好 Y 类 items"这种可迁移 pattern，不是绑定到具体 user_id 的口味记忆**。部署到 Taste hunter 时，新用户走 OOV / 冷启动路径——`user_id` 走 OOV mean，其他 user_features 从对话累积或默认值重建，复用训练好的交互 weight。详见 §2.5。

剩下的 10 节把这个一句话答案彻底拆开（实际数据来源已 ground-truth 验证：`Yelp JSON 2/yelp_dataset.tar` 已下载到工作目录）。

---

## 1. 用搜索域的语言理解推荐训练

### 1.1 搜索 vs 推荐：本质是同一个 ranking 问题，监督信号来源不同

| 维度                | 搜索系统                                                 | 推荐系统（我们的）                                                                                 |
| ----------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **输入**            | Query × Doc                                          | User × Item × Context                                                                     |
| **输出**            | Relevance score → docs ranked list                   | Like probability → items ranked list                                                      |
| **Layer 1 召回**    | 倒排拉链（inverted index）从 query terms → candidate doc 集合 | **双塔模型 (Two-Tower / DSSM)**：User Tower + Item Tower 各自 embed，cosine 相似度匹配，FAISS ANN 做近邻检索 |
| **Layer 2 精排**    | LTR 模型（pointwise / pairwise / listwise）              | **DeepFM**（FM 二阶交叉 + DNN 高阶交叉，共享 embedding）                                               |
| **训练样本来源**        | 用户 query → click / dwell / conversion 日志             | 用户 review / rating（Yelp）→ rating ≥ 4 = positive                                           |
| **正样本**           | clicked doc（或 dwell time > N 秒）                      | rating ≥ 4 的 (user, business) pair                                                        |
| **负样本**           | unclicked impression（或 negative sampling）            | rating < 4 + negative sampling（同城未访问商家）                                                   |
| **Hold-out 评测**   | 时序切分 query 流量，评 NDCG / MRR                           | 时序切分 review，评 AUC / NDCG@10 / Recall@10                                                   |
| **Online metric** | CTR / 转化率 / 留存                                       | 点击率 / 停留 / thumbs-up 比例                                                                   |

**关键映射**：

> 你在搜索里熟悉的 query→click 日志 = 我们这里的 user→review (rating≥4) 日志。
> 倒排拉链召回 candidate docs = 双塔模型召回 candidate restaurants。
> 你的 LTR ranker = 我们的 DeepFM ranker。

唯一的区别：搜索是 query-driven（query 是即时输入），推荐是 user-driven（user 自身就是 context）。但 ranking 模型的训练方法学完全一致——都是从 historical interaction logs 学 user-item relevance。

### 1.2 两阶段架构（与搜索完全平行）

```
                  ┌──────────────────────────┐
                  │  User × Context Request   │
                  │  (user_id or <NEW_USER>,  │
                  │   lat/lon, hour, period)  │
                  └────────────┬─────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Layer 1 — 召回 (Retrieval)   │
                │  Two-Tower / DSSM             │
                │                               │
                │  User Tower MLP → user_emb    │
                │  Item Tower MLP → item_emb    │
                │  cosine(u, v) → top-200       │
                │                               │
                │  ⇄ FAISS ANN 索引 over 150K   │
                │     Yelp businesses           │
                └──────────────┬──────────────┘
                               │ 200 candidates
                ┌──────────────▼──────────────┐
                │  Layer 2 — 精排 (Ranking)     │
                │  DeepFM                       │
                │                               │
                │  Full feature set             │
                │  (26 features, see §3.3.3)   │
                │  → CTR score per candidate    │
                │  → top-10 ranked              │
                └──────────────┬──────────────┘
                               │ 10 ranked
                ┌──────────────▼──────────────┐
                │  Layer 3 (Trip only) — MMR    │
                │  + Heuristic Constraint       │
                │  → top-3 per period           │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  LLM Agent → Frontend        │
                │  (F1 cards / F1.1 detail /   │
                │   F2 trip plan)               │
                └─────────────────────────────┘
```

**搜索域类比**：你的搜索系统里 Layer 1 是倒排拉链给 1000 candidate docs，Layer 2 是 LTR 给 final ranked top-10——结构完全一样。我们只是把 Layer 1 的"倒排拉链"换成了"双塔 ANN 检索"，因为推荐场景没有 query terms 作为索引锚点，必须用 dense embedding。

---

## 2. 训练数据：Yelp Open Dataset 怎么变成模型样本

### 2.1 Yelp Open Dataset 数据结构

Yelp 公开发布的数据集（最新 2022-01 版，原始 tar 4.0GB / 解压后 ~9GB），核心 5 张表（JSON Lines 格式）：

| 表名 | 实际行数 ✅ | 关键字段 | 在我们模型里的角色 |
|---|---|---|---|
| `yelp_academic_dataset_business.json` | **150,346** | business_id / name / city / state / postal_code / latitude / longitude / stars / review_count / is_open / attributes (dict) / categories (CSV string) / hours | 推荐的 **item 池**——所有候选商家来自这里 |
| `yelp_academic_dataset_user.json` | **1,987,897** | user_id / name / review_count / yelping_since / useful / funny / cool / elite (year CSV) / friends (user_id CSV) / fans / average_stars / 11 个 compliment_* (hot/more/profile/cute/list/note/plain/cool/funny/writer/photos) | 训练阶段的 **代理用户池**（22 字段全部可 lookup）|
| `yelp_academic_dataset_review.json` | **6,990,280** | review_id / user_id / business_id / stars (1-5 float) / useful / funny / cool / text / date | **核心训练样本来源**——每条 review 是一条 (user, business, rating, time) 监督信号 |
| `yelp_academic_dataset_tip.json` | ~908K | user_id / business_id / text / compliment_count / date | 可选辅助：短评论，可作 implicit feedback |
| `yelp_academic_dataset_checkin.json` | ~131K | business_id / date (CSV string of timestamps) | 可选辅助：商家热度时序信号 |

我们项目主战场是 `review.json`：每行是一个 (user_id, business_id, stars, date) tuple，用来构造监督信号。**已下载到 `canvas/ml2/project/Yelp JSON 2/`**，行数已通过 `wc -l` 实测验证（2026-05-05）。

> [!info] User.json 完整 schema（22 字段实测）
>
> 以下 22 字段中，我们的 §3.3.3 8 个 User Features 直接派生 6 个（user_id / average_stars → avg_rating_given / review_count → review_count_log / yelping_since → days_active / elite → elite_flag），另外 2 个（mean_distance_traveled / fav_cuisine_emb）需要从 review.json 历史聚合计算（详见 §2.2 伪代码）。`compliment_*` 11 个字段我们暂不使用，可作 future work（衡量用户社交活跃度的辅助信号）。
>
> ```
> user_id, name, review_count, yelping_since, useful, funny, cool,
> elite, friends, fans, average_stars,
> compliment_hot, compliment_more, compliment_profile, compliment_cute,
> compliment_list, compliment_note, compliment_plain, compliment_cool,
> compliment_funny, compliment_writer, compliment_photos
> ```

### 2.2 一条 review 怎么变成一条训练样本

伪代码层面：

```python
# 输入：一条 Yelp review
review = {
    "user_id": "abc123",
    "business_id": "xyz789",
    "stars": 5,           # 用户评分 1-5
    "date": "2018-07-15"
}

# Step 1: 构造 label
# rating ≥ 4 = positive (user "liked" this restaurant)
# rating < 4 = negative (or weak signal)
label = 1 if review["stars"] >= 4 else 0

# Step 2: 拉 user features (从 user.json 查 abc123)
user_features = lookup_user(review["user_id"])
# {avg_rating_given: 4.2, review_count: 87, fav_cuisine_emb: [...], ...}

# Step 3: 拉 item features (从 business.json 查 xyz789)
item_features = lookup_business(review["business_id"])
# {categories: ["Japanese", "Ramen"], price_level: 2, rating: 4.5, ...}

# Step 4: 构造 context features (从 review.date 派生)
context_features = derive_context(review["date"], user_features, item_features)
# {distance: 1.2km, hour_bucket: "evening", day_of_week: "Saturday",
#  trip_day_index: 0,  # 不是 trip 场景
#  period_id: <UNK>,   # 不是 trip 场景
#  activity_emb: zeros,
#  prior_meals_cuisines: zeros}

# Step 5: 拼成模型输入
sample = {
    "features": {**user_features, **item_features, **context_features},
    "label": label
}
```

**这就是一条训练样本**。6.5M reviews → 6.5M positive labels（其中 ~70% rating ≥ 4 → ~4.5M positive，~2M weak/negative）。

### 2.3 正负样本定义

**Explicit positive**：rating ≥ 4 的 review pair。约 4.5M。

**Explicit negative**：rating < 4 的 review pair（用户去了但评分低 → "明确不喜欢"）。约 2M。

**Implicit negative（负采样）**：对每个 explicit positive (user_u, business_b)，从 user_u 所在城市内**未访问过的商家**中随机采样 N 个作为 implicit negative。N 是超参数，通常 1:1 / 1:2 / 1:4。我们项目固定 1:4。

**为什么需要负采样**：纯 explicit negative 数量不够（且 rating < 4 的 review 偏少），且模型需要学习"user_u 不会选某些餐厅"的信号——unobserved interactions 是天然的弱负样本。

最终训练集结构：

| 样本类型 | 数量（估算）| label |
|---|---|---|
| Explicit positive | ~4.5M | 1 |
| Explicit negative | ~2M | 0 |
| Implicit negative (1:4 sampling) | ~18M | 0 |
| **总计** | ~24.5M | — |

正负比约 1 : 4.4。

### 2.4 数据规模和算力预算

完整 7M reviews 训练 1 epoch 在 Colab T4（free tier，16GB）需要约 4-6 小时。**为了让 sweep 实验可控，我们对 reviews 做下采样**：

- **Sub-sampling 策略**：保留 3 个 target 城市（Philadelphia + Tucson + Tampa）的全部 review，其他城市每用户随机采 5 条 → 估计降到 ~1M reviews
- **训练时间目标**：1M sample × 1 epoch ≈ 45-90 min on T4，约 8-12 epoch 收敛 → 单次完整训练 ≈ 6-12 小时
- **正则化 sweep**：`embedding_dim` × `dropout` × `L2` × `MMR_λ` × `negative_ratio` 全网格扫描 80+ 组配置不可能跑完，分阶段先选 dim 再 sweep dropout/L2（详见 §3.3.5）

---

### 2.5 等等——我们用不了 Yelp 用户账号，训练 user_features 还有意义吗？

> [!warning] ⚠️ 核心质疑
>
> "就算 `lookup_user(review.user_id)` 工程上做得到，我们部署时根本拿不到 Yelp 用户账号，新用户进来 user_id 完全对不上。那训练时引入这些 user features 不就白费了吗？"
>
> 这个反驳看似切中要害，实际上指向了推荐系统训练的一个**核心误解**——以为模型学的是"特定用户喜欢什么"。**真相**：模型学的是"什么样的用户特征组合 → 偏好什么样的 items"。后者完全可迁移。

#### 2.5.1 训练 DeepFM 学到的信号分三层（按可迁移性梯度）

| 信号层 | 内容 | Taste hunter 部署可迁移？ | 例子 |
|---|---|---|---|
| **A. Item × Context 交互** | 餐厅属性 × 时间 / 地理 / 时段如何影响 ranking——**与"哪个用户"完全无关** | ✅ **完全可迁移** | "早午餐时段 brunch 类餐厅升权" / "1 mi 内的店在距离敏感场景下得分高" / "高 rating + 高 review_count 商家整体可信度高" |
| **B. User_features × Item 交互** | 具有 X 类 user feature pattern 的用户偏好 Y 类 items——**学的是"怎样的用户喜欢怎样的店"，不是"特定用户喜欢什么"** | ✅ **可迁移**（通过对话累积偏好重建用户特征向量） | "review_count 高的活跃 foodie 愿意尝试小众 cuisine" / "average_stars 低的严格评分者偏好 fine dining" / "fav_cuisine 偏 Asian 的用户对寿司店升权" |
| **C. User_id 特异性 embedding** | `qVc8ODYU` 这个具体 Yelp 用户的随机口味记忆——绑定其真实 Yelp 账号 | ❌ **不可迁移**——新用户用 OOV mean 兜底 | "user_id=qVc8ODYU 这个具体的人喜欢绿色装修 / 习惯周二去某家店" 这类个人随机噪声 |

**核心论点**：DeepFM 学到的 80% 是 (A) + (B) 两层，**(C) 在新用户上让 user_id embedding 退化为 OOV mean，损失的 signal 不大**。这就是 H6 假设（"冷启动用户内容特征 > 协同特征"）的理论支撑——从 (A)+(B) 角度看，没有 user_id 信号也不会崩。

#### 2.5.2 部署时如何"重建" user_features？

`lookup_user` 训练时学到的 user feature × item 交互，部署时**通过对话累积偏好或合理默认值**填进同一组 features 槽位。下表是新用户每个 user feature 的"重建路径"：

| 训练时 user_feature        | 训练时获取方式      | Yelp 训练来源                                                                                              | 部署时 Taste hunter 新用户怎么得到                                                         |
| -------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `user_id` (cardinality 2M) | ✅ **直接**          | `user.user_id`（key 字段）                                                                                | `<NEW_USER>` OOV embedding（**唯一不可重建**，弃 C 层信号）                                   |
| `avg_rating_given`         | ✅ **直接**          | `user.average_stars / 5.0`（归一化）                                                                       | 对话推断："我评分挑剔" → 3.0；"啥都给好评" → 4.5；缺失 → 全局中位数 3.8                                  |
| `review_count_log`         | ✅ **直接**          | `log1p(user.review_count)`                                                                            | 对话推断："吃过上百家" → log(100)=4.6；新手 / 缺失 → 0                                          |
| `days_active`              | ✅ **直接**          | `log1p((today - user.yelping_since).days)`                                                            | 0（新平台用户必为 0）                                                                     |
| `elite_flag`               | ✅ **直接**          | `1 if user.elite != "" else 0`                                                                        | 0（永远，Yelp Elite 是 Yelp 平台资格不可迁移）                                                 |
| `mean_distance_traveled`   | ⚠️ **聚合预计算**   | join `review.user_id` × `business.{lat, lon}` → pairwise haversine 距离均值（实测 lat/lon **100% 覆盖** ✅）           | 对话推断："常出差" → 高值；"宅家附近" → 低值；缺失 → 全局中位数                                          |
| `fav_cuisine_emb`          | ⚠️ **聚合预计算**   | join `review.user_id` × `business.categories` → top-3 cuisine pooling（实测 categories **99.9% 覆盖** ✅）         | 对话提取："想吃日料 / 辣的" → 即时合成 cuisine vector；缺失 → 全局 prior（top-5 popular cuisines avg） |
| `price_tolerance_avg`      | ⚠️ **聚合预计算**   | join `review.user_id` × `business.attributes.RestaurantsPriceRange2` → 均值（实测餐厅子集 **84.8% 覆盖**；缺失行丢弃；用户全部商家都缺失 → fallback 0.5） | 对话提取："人均 30 以下" → 0.3；"无所谓" → 0.5；缺失 → 0.5                                       |

**8 个 user features 拆分**：5 直接字段（O(1) dict lookup） + 3 聚合预计算（开训前一次性扫数据建表）。**6 个能从对话或合理默认值"重建"**，1 个（user_id）走 OOV，1 个（elite_flag）天然为 0。

> [!info] 聚合预计算的实际成本（实测分布支撑）
>
> User review_count 实测：均值 133.5，中位数 41，P90=335，P99=1,326，最大 17,473。**1.1% 用户只有 1 条 review**——pairwise 距离无解，`mean_distance_traveled` fallback 为 0；**6.3% 用户 review<5**——构成 §3.3.1 H6 cold-start 子集，聚合信号弱，模型走内容特征兜底路径。
>
> 对应 §2.4 训练数据规模：以 3 target 城市 + 时序过滤后约 1M reviews 计算，预计算 user features 表（含 3 聚合字段）pandas 单机约 1-2 小时；用 polars / duckdb 可压到 ~10-15 min；输出 ~500MB pickle，训练阶段 dict lookup O(1)。

> [!success] ✅ 数据可行性结论（实测验证 2026-05-05）
>
> 三个聚合字段所需 Yelp 字段实测覆盖率均达标——`mean_distance_traveled` 和 `fav_cuisine_emb` 几乎完美（餐厅子集 lat/lon 100% / categories 99.9%），`price_tolerance_avg` 在餐厅子集 84.8% 覆盖也够用（fallback 简单）。**Yelp Open Dataset 完全支持 §3.3.3 8 个 user features 的预计算**，无需引入外部数据源。


#### 2.5.3 user.json lookup 的真正价值

不是为了 deploy 时"查到这个 Yelp 用户的偏好"——这部分价值在我们部署场景里**用不上**。`lookup_user(user_id)` 的真正价值在于：

1. **训练阶段构造监督信号**：每条 review 训练样本都带上发起者的 user_features，让 DeepFM 学到 user_features × item_features 的二阶交叉
2. **学到可迁移的 pattern**：FM 二阶项 + DNN 高阶项捕捉"什么样的用户特征组合 → 什么样的偏好"——不绑定到具体 user_id
3. **部署时通过对话填进同一组 features 槽位**，复用训练好的 weight matrix

**类比你做搜索时的经验**：搜索训练时也用 `user_id` / `user_history` features，**不是为了在生产中找回同一个用户**——而是为了让模型学到"怎样的用户类型 + 什么 query → 偏好哪类 doc"这种 generalizable pattern。同样的方法学，搜索叫 personalization；推荐叫 collaborative + content。

> [!success] ✅ 一句话总结
>
> **`lookup_user` 是有意义的，但它的意义在 user features 的 *pattern*，不在 specific user identity**。Yelp 用户账号本身我们用不了，但 Yelp 用户的特征分布教会了模型 "怎样的用户偏好怎样的店"——这个知识在新用户上可通过对话推断 user features 来复用。

#### 2.5.4 这意味着 v2 §3.3.3 user features 表需要升级

v2 §3.3.3 user features 表当前只写了"训练时数据来源（Yelp 字段路径）"。v3 应升级为双列：
- **训练时来源**：Yelp 字段路径（已有）
- **部署时 fallback / 对话推断路径**：参见上方 2.5.2 表

落地点：考虑在下一轮 §3.3 v3 时把 fallback 列直接合并进 §3.3.3 主特征表里，避免 §9 fallback 速查表（详见末尾）和主表分离造成的"两处真相"问题。

---

## 3. 训练 / 验证 / 测试 切分

### 3.1 Temporal hold-out（时序切分）

按 `review.date` 分位数切：

| 集合 | 时间窗 | 占比 | 用途 |
|---|---|---|---|
| Train | date < P70 分位（最早 70%）| 70% | DeepFM 参数更新 |
| Validation | date 在 P70-P80 区间 | 10% | 超参选择 / early stopping |
| Test | date > P80 分位（最新 20%）| 20% | 最终一次性评测 |

**举例**：如果 review 时间范围是 2010-01-01 到 2022-12-31（约 13 年），P70 ≈ 2019-04-01，P80 ≈ 2020-08-01。即 2010-2019 的 review 训练，2019-2020 的 review 验证，2020-2022 的 review 测试。

### 3.2 为什么不用 random split？

**Temporal leakage 风险**：random split 会把同一个 user 的早期 + 晚期 review 同时分到 train / test，导致测试时模型已经"见过"这个 user 的偏好，AUC 虚高。这是推荐系统离线评测的经典坑——你在搜索里也熟悉，搜索 click log 的 hold-out 切分也必须按 query timestamp 切。

**Production 模拟**：temporal split 模拟了生产部署场景——模型在过去数据上训练，在未来时间点做推断。如果你 random split，evaluation 结果对生产无指导意义。

### 3.3 子集评测（Cold-start / Cross-city）

除了 main test split，单独切两个 sub-set 用于专门验证假设：

- **Cold-start 子集**：从 train 中**整体抽出** review_count < 5 的 user_id（约 ~600K user 中的 30%-40%），他们的全部 review 都不进 train，专门用于评 Cold-start AUC（验证 H6）
- **Cross-city 子集**：训练时只用 Philadelphia reviews，测试时在 Tampa held-out users 上评——验证模型的城市迁移能力

---

## 4. 模型架构（与你搜索经验对应）

### 4.1 Layer 1 召回：双塔（Two-Tower / DSSM）

**目的**：从 150K 商家中快速找到 top-200 候选，避免对全量商家跑 DeepFM forward pass（O(150K) 太慢）。

**架构**：

```
┌──────────────────────┐         ┌──────────────────────┐
│   User Tower          │         │   Item Tower          │
│                       │         │                       │
│  user_id emb (8d)     │         │  business_id emb (8d) │
│  + avg_rating_given   │         │  + categories multi   │
│  + review_count_log   │         │  + price_level        │
│  + fav_cuisine_emb    │         │  + city_id emb        │
│  + ...                │         │  + ...                │
│                       │         │                       │
│  → MLP [64, 32]       │         │  → MLP [64, 32]       │
│  → user_vec ∈ ℝ³²     │         │  → item_vec ∈ ℝ³²     │
└──────────┬───────────┘         └──────────┬───────────┘
           │                                  │
           └──────────────┬──────────────────┘
                          │
                  cosine(user_vec, item_vec)
                          │
                  → relevance score
```

**训练**：和 DeepFM 一样的 (user, business, label) tuple，loss = pairwise softmax 或 BCE。User/Item Tower **不共享参数**（这是双塔区别于 single-tower 的核心）。

**推断**：item embedding **离线预计算**所有 150K 商家的 item_vec，存入 FAISS ANN 索引（IVF / HNSW）。线上 user_vec 实时计算（只过一次 MLP），然后 ANN 搜 top-200。延迟 < 50ms。

**与倒排拉链的对应关系**：

| 倒排拉链 | 双塔 |
|---|---|
| Query terms → posting list | User vec → ANN search |
| Term-level lexical match | Dense embedding semantic match |
| Boolean / BM25 score | Cosine similarity |
| 召回精度高、覆盖窄 | 召回覆盖广、精度依赖 embedding 质量 |
| 易控、易解释 | 黑盒、需 ablation 验证 |

工业推荐里两塔已经替代了大部分 lexical 检索（除了 Spotify / 网易云某些 podcast 场景），原因是 user-item 交互天然是稠密 vector 而非稀疏 token 匹配。

### 4.2 Layer 2 精排：DeepFM

**目的**：在 200 candidates 上做精细排序，输出 top-10。

**架构**：详见 `PRD_v1_section3.3_Model_v2.md` §3.3.4。核心是 FM branch（学二阶交叉，如 cuisine × hour_bucket）+ DNN branch（学高阶交叉），共享 embedding。

**与搜索 LTR 的对应关系**：
- DeepFM ≈ 你搜索里见过的 GBDT + DNN 混合 ranker，或 Wide & Deep
- 输入 features: search 是 (query_features, doc_features, query×doc cross_features)；推荐是 (user_features, item_features, context_features)
- 训练目标都是 pointwise binary classification（loss = BCE on rating ≥ 4 / clicked）
- 线上每个 candidate 都过一遍 forward pass 拿 score

### 4.3 Layer 3 重排（Trip 场景独有）：MMR + Heuristic

详见 §3.3.4.5。核心是从 DeepFM top-10 中通过 MMR 公式选 top-3 candidates with diversity，再叠加规则约束（同日 cuisine 不重 / 地理紧凑）。

```
λ * Score(d_i) - (1-λ) * max_j sim(d_i, d_j)
```

这一层是 Trip 场景特有的"per-period 多 candidate"需求——chat-flow 不需要。

---

## 5. 评测：没有真实用户怎么看 metric？

这是你提到的最关键问题。

### 5.1 内测（offline metric）= 我们能做到的全部

**评测对象**：DeepFM 在 **Yelp temporal hold-out test 集**上的预测能力。

**测什么**：
- AUC：模型能否把 test 集里的 explicit positive (rating≥4) 排在 implicit/explicit negative 之前。AUC=0.75 意味着随机选一个正例 + 一个负例，模型 75% 的概率把正例排得更高。
- NDCG@10：模型 top-10 推荐里，真正例（test 集中该 user 实际打 ≥4 星的商家）的位置加权得分。NDCG@10=0.30 是合理的推荐系统水平。
- Recall@10：top-10 推荐里覆盖了 test 集 user 的多少真实正例。Recall@10=0.20 = top-10 抓住了 20% 的"用户未来会喜欢的商家"。
- Cold-start AUC：限定 review_count < 5 的 user 子集，验证 H6 假设。
- Coverage@10：top-10 推荐覆盖了多少不同商家（衡量是否扎堆头部网红店）。

**这些指标是 ML2 评分的主战场**——Bose 的 rubric Criterion 7 要的就是 hold-out test 上的数字 + 学习曲线 + ablation。**不需要任何真实 Taste hunter 用户即可拿到全部 metric**。

### 5.2 外测（online metric）= 我们没有，且承认

**外测**包括：
- 真实用户点击率 / 转化率（CTR）
- A/B 实验 lift（DeepFM 推荐组 vs popularity baseline 组）
- 用户长期留存 / 复访率
- thumbs-up / down 比例（demo 中有 UI 但无数据）
- 业务 metric（订餐转化、广告分成）

**这些我们全部没有**，因为：
- 我们没有真实用户流量
- 即使有，A/B 实验需要数百到数千用户数据才统计显著，class demo 周期来不及
- 业务 metric 依赖商家合作（订餐 deeplink），完全 out of scope

### 5.3 ML2 课程评分要的是哪个？

**只要 offline metric**。Bose 的 rubric 8 项：

| Criterion | 需要 online metric？ | 需要 offline metric？ |
|---|---|---|
| 1. Problem Statement | ❌ | ❌ |
| 2. Hypotheses | ❌ | ❌ |
| 3. EDA | ❌ | ✅（Yelp 数据描述）|
| 4. Feature Engineering | ❌ | ❌ |
| 5. Approaches + overfit/underfit | ❌ | ✅（train/val 学习曲线）|
| 6. Solution + regularization | ❌ | ✅（hyperparam sweep on val NDCG@10）|
| **7. Results + Learnings** | ❌ | ✅（test 集 AUC / NDCG@10 / 消融）|
| 8. Future Work | ❌ | ❌ |

**没有任何一项要求 online metric**。这就是为什么 academic ML2 评分对我们 friendly——课程项目本身就是设计成"用 public dataset 训 + offline 评测 + 写报告"的格式。

### 5.4 Production 部署什么时候才能拿到 online metric？

**未来工作（Future Work / Criterion 8）**：

> Phase 1（本次交付）：Yelp 离线训练 + 离线评测 → ML2 grading 完成
> Phase 2（毕业后或下一阶段）：Beta launch with 50-100 真实 users → 收集 thumbs-up/down + 点击日志 → 重新评 thumbs-up rate / 点击率 → 比较 cold-start 和 persona-anchored 用户群体的差异
> Phase 3（产品化）：A/B 实验 DeepFM vs popularity baseline → online lift 数字进 case study

Phase 2/3 写进 §6 Future Work，作为对评分者展示"我们知道 production 还需要什么"的诚实表态。

---

## 6. 部署：Taste hunter 真实用户的三种状态

Demo 时每个打开 app 的用户都是 Yelp 训练词表外的新人。三种处理路径：

### 6.1 S0 完全冷启动

**触发**：首次打开，0 条对话，0 条历史交互。

**`user_id` 处理**：训练时必须**预留 OOV 槽位**——在 user_id 词表里加一个特殊索引 `<NEW_USER>`（例如 index=0 或最后一个）。训练阶段对 1-3% 的样本随机替换 user_id 为 `<NEW_USER>`，让模型学到"看到这个 ID 时退化为内容驱动 ranking"。

```python
# 训练时数据增广
if random.random() < 0.02:  # 2% 概率
    sample["user_id"] = "<NEW_USER>"  # 强制 OOV 学习
```

**部署时**：新用户 user_id 直接映射到 `<NEW_USER>` 索引 → 取该 embedding（接近 global mean）。

**所有 User Features 全 fallback**：
- avg_rating_given → 全局中位数 ≈ 3.8
- review_count_log → log1p(0) = 0
- fav_cuisine_emb → 全局 prior（top-5 popular cuisines avg pool）
- 等等

**排序信号**：完全靠 Item Features（rating / review_count / price）+ Context Features（geo / hour / day_of_week）。本质退化为"附近高分热门"推荐。

### 6.2 S1 对话偏好累积

**触发**：用户在对话中明示偏好（"想吃辣""人均 30 以下""带小孩""无葱蒜"）。

**关键决策**：偏好**不写回 user embedding**，而是注入 LLM intent → 作为 `recommend_restaurants` 的 filter / soft constraint。

为什么不写回 embedding？因为：
1. 单次对话偏好只是 intent，不是 stable preference
2. 写回 embedding 需要在线学习基础设施（gradient update + serving 一致性）
3. 对话中的偏好直接当 hard filter 更可控、更可解释

**实装**：
```python
# 对话累积到 JSON
user_ctx.accumulated_prefs = {
    "cuisine_likes": ["Spicy", "Sichuan"],
    "cuisine_dislikes": [],
    "dietary": ["no garlic"],
    "budget_range": "moderate"
}

# 调 recommender 时作为约束
recommend_restaurants(
    user_ctx=user_ctx,
    intent={"cuisine": ["Spicy"], "budget_range": "moderate"},
    filters={"hard": {"dietary": ["no_garlic_compatible"]}}
)
```

**fav_cuisine_emb 的特例处理**：可以从 `accumulated_prefs.cuisine_likes` 即时合成（取这些 cuisine 的 one-hot avg pooling），把"对话累积偏好"也喂给 DeepFM 的 user features。这是 S0 fallback 的升级版。

### 6.3 S2 隐式反馈累积

**触发**：用户使用 thumbs-up / thumbs-down / refresh + 点击卡片产生 dwell time（demo 中可手动模拟）。

**两条路径**：

| 路径 | 实装难度 | 何时触发 |
|---|---|---|
| (a) 在线增量更新 user_id embedding | 高（需要 streaming gradient + serving sync） | Production 阶段 |
| (b) 视为 S1 + 偏好 filter | 低（同 S1 实装） | **本次 Demo 用 (b)** |

例如用户 dislike 某个意餐 → 累积到 `accumulated_prefs.cuisine_dislikes.append("Italian")` → 后续 `recommend_restaurants` 调用排除 Italian。

### 6.4 OOV embedding 实装细节

**关键**：训练 DeepFM 之前，必须在 `user_id` 词表里**显式加 `<NEW_USER>` 索引**。否则部署时遇到新 user_id 直接 IndexError。

伪代码：

```python
# 1. 词表构建
unique_user_ids = list(set(reviews["user_id"]))
user_id_to_index = {"<NEW_USER>": 0}  # 预留索引 0
for i, uid in enumerate(unique_user_ids, start=1):
    user_id_to_index[uid] = i

# 2. Embedding 层
n_users = len(user_id_to_index)
user_embedding = nn.Embedding(n_users, dim=8)
# user_embedding(0) = <NEW_USER> 的向量

# 3. 训练时随机注入 OOV
def get_user_idx(uid):
    if random.random() < 0.02:
        return 0  # 强制 OOV
    return user_id_to_index.get(uid, 0)  # 查不到也用 OOV

# 4. 推断时（部署）
def get_user_idx_inference(uid):
    return user_id_to_index.get(uid, 0)  # 不在训练词表 → OOV
```

这是工业推荐 SOP（Pinterest / Spotify / Airbnb 都这么做），名字也叫 "OOV embedding" 或 "fallback user vector"。

---

## 7. Demo 演示策略：三帧编排

期末 5/22 演练 + 5/23 提交时，按这三帧演示：

### 演示帧 1（S0 — 完全冷启动）

**剧本**：演示者作为新用户首次打开 → 看到完全基于 Philadelphia 当前位置 + 周三上午时段的 popularity-driven 推荐（"附近高分早午餐"），reason chip 全是地理 + 时段类型，无个性化语言。

**话术**：「这位用户尚无任何历史，模型完全靠 location + time + Yelp popularity prior。这正是 H6 假设支撑的冷启动行为——内容特征足以给出合理推荐。」

### 演示帧 2（S1 — 对话偏好累积）

**剧本**：演示者输入"想吃辣的，人均 30 以下" → intent 抽取 `cuisine=["Spicy"], budget="moderate"` → recommender 加约束 → 给出辣味候选，reason chip 反映约束（"📍 距你 1 mi · 辣度匹配"）。

**话术**：「用户一句话就把偏好告诉系统了——不需要等到累积 20 条 review 才能个性化。这是 LLM agent + recommender 混合架构的核心价值：自然语言成为冷启动 user vector 的注入渠道。」

### 演示帧 3（Persona 锚定，⭐ 推荐压轴）

**剧本**：手工 persona "user, Philadelphia, brunch lover, $$, 类似 Yelp user_id=`xxx`（一个真实 Philadelphia brunch 重度用户）"——把 user embedding **手动锚定**到 Yelp 训练集中某个真实 user_id。演示"如果 Haobo 已经累积 3 个月数据后，模型给出的个性化推荐是什么样"。

**话术**：「这一帧诚实标注为「persona 模拟」——不掩盖我们冷启动的事实。但目的是让评分者理解：DeepFM 学到的协同信号是真实存在的，只是 demo 阶段没有真实数据触发它。production 部署后，每个真实用户用一个月就累积到这个状态。」

**不演示帧**（避免误导）：
- 实时在线学习的 dashboard——我们没有
- A/B 实验 lift 图——没有
- 真实用户 thumbs-up 率统计——没有

---

## 8. H6 假设的双重意义

H6（"冷启动用户内容特征 > 协同特征"）现在承担两层职责：

| 维度 | 验证场景 | 用途 |
|---|---|---|
| **学术验证** | 在 Yelp 测试集上，对 review_count < 5 的用户子集，去掉 user_id embedding 后 Recall@10 下降 < 0.01 | 验证 DeepFM 架构对冷启动的天然鲁棒性；写入 Criterion 5/7 |
| **部署理论基础** | H6 实验通过 = Taste hunter 真实新用户（S0/S1）冷启动路径的事前承诺 | 为 demo 策略 S0/S1 提供理论支撑；写入 Criterion 8 Future Work |

**写报告的两次引用**：
- Criterion 2（Hypotheses）：列出 H6
- Criterion 7（Results）：报告 H6 的实验结果（Recall@10 差距）
- Criterion 8（Future Work）：引用 H6 为 production launch 的"为什么我们对 cold-start 路径有信心"

---

## 9. User Features 部署时 fallback 速查表

| 特征 | 训练时来源（Yelp）| Deploy 新用户 fallback | 备注 |
|---|---|---|---|
| `user_id` | `review.user_id` | `<NEW_USER>` 特殊 embedding（全局均值，训练时预留 OOV）| 用户累积 ≥ 50 交互后可分配独立 ID（v2 范围外）|
| `avg_rating_given` | `user.average_stars` | 全局中位数 ≈ 3.8 | |
| `review_count_log` | `log1p(user.review_count)` | log1p(0) = 0 | 模型学习"0 = 新用户"语义 |
| `mean_distance_traveled` | 用户历史 review 聚合 | 全局中位数 | |
| `fav_cuisine_emb` | top-3 cuisine pooling | 优先：`accumulated_prefs.cuisine_likes` 即时合成；fallback：全局 prior | 与 §3.2.2 S2/S6 联动 |
| `price_tolerance_avg` | 用户历史均值 | 优先：`accumulated_prefs.budget_range` 派生；fallback：0.5 | |
| `days_active` | `yelping_since` 距今天数 | 0 | 同 review_count_log |
| `elite_flag` | `user.elite` 非空 | 0 | 新用户必非 elite |

---

## 10. FAQ

### Q: 我们没有用户数据，怎么训推荐？
A: 用 Yelp 1.5M 历史用户作为训练 proxy。每条 review (rating ≥ 4) 是一条 positive 监督信号，加 4× 同城未访问商家作 negative。训练 DeepFM 学协同 + 内容信号。**Yelp 历史用户在训练阶段=我们的"用户"**，Taste hunter 真实用户在部署时走冷启动 + 对话累积偏好路径。

### Q: 我们没有 online metric (没有真实点击日志)，怎么看模型好不好？
A: 看 offline metric on Yelp temporal hold-out test 集——AUC / NDCG@10 / Recall@10 / Cold-start AUC / Coverage@10。这 5 个数字对 ML2 评分 Criterion 7 完全够用。Bose rubric 没有要 online metric。

### Q: 你说的"外"是什么？我们有没有？
A: "外测" = online A/B test = 真实流量上的实验。**我们没有**，且未来 1 个月也不会有。承认这个事实，写进 §6 Future Work 作为下一阶段任务。

### Q: 为什么不直接用 GPT 做推荐？
A: GPT 没有 Yelp business 的 fine-grained context（实时距离 / 营业状态 / hour-cuisine 交互），且无法学习"这个具体用户的口味"。LLM agent 做意图抽取 + 文案合成，DeepFM 做精排——分工。这也是 ML2 评分要看的"deep learning recommender"主菜。

### Q: 双塔为什么要单独做？直接 DeepFM 不行吗？
A: 性能问题。150K 商家全跑 DeepFM forward pass 需要秒级延迟；双塔 ANN 检索 < 50ms。两层架构是工业标配。但 ML2 评分如果时间紧张，可以降级为"category + city 硬过滤"代替双塔（详见 §3.3.4 降级策略），不影响主分。

### Q: Persona demo 是不是作弊？
A: 不是——只要诚实标注。学术 demo 和 production deployment 是两回事，persona 锚定是合法的"如果未来有数据会怎么样"演示，本质和论文里的 case study 一样。**如果不标注、假装是真实用户，那是作弊**。

### Q: 我们部署时拿不到 Yelp 用户账号，那训练时 lookup user features 不就白费了吗？
A: **不白费。模型学的是"什么样的用户特征组合 → 偏好什么样的 items"这种可迁移 pattern，不是绑定到具体 user_id 的口味记忆**。8 个 user features 中 6 个（avg_rating_given / review_count_log / fav_cuisine_emb / price_tolerance_avg / mean_distance_traveled / days_active）可以从新用户对话或默认值"重建"，复用训练好的交互 weight；只有 `user_id` embedding 不可迁移（走 OOV mean）+ `elite_flag` 永远为 0。详细三层信号（A/B/C 可迁移性）拆解和重建路径表见 §2.5。

---

## 11. 一句话总结

> "训练用 Yelp ~2M 历史用户作 proxy，DeepFM 学协同 + 内容信号 → 离线评测在 Yelp temporal test 集上拿 AUC / NDCG@10 / Recall@10 → ML2 全部 5 个评分 Criterion（3/4/5/6/7）满足。Taste hunter 真实新用户走 S0/S1 冷启动路径——对话累积偏好 + 内容特征兜底。Demo 压轴用 persona 锚定 Yelp user_id 演示个性化能力，诚实标注「persona 模拟」。online A/B 测试归 Future Work。"

---

<!-- explainer · 2026-05-05 -->
