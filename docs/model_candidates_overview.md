# Model Candidates Overview — for Zimeng + Cindy's scouting

**Goal**: 不是预设答案，是给一份"业界对推荐系统这件事都有哪些做法"的速览，让你们评估的时候有共同语言。**评估完了如果有更适合的候选，欢迎补充**。

**评估维度建议**:
1. 在 Yelp 数据上能不能跑通（user-item-rating 是基础，user/item meta 加分）
2. 能不能容纳"地理位置 + 行程 context"特征
3. 是否对得起 ML2 课的"deep learning"评分（纯线性方法可能扣分）
4. 实现成本（有现成 PyTorch/TF 实现 vs 自己撸）
5. 训练时间（Yelp ~7M reviews（实测 6,990,280），单卡 GPU 能否在 1 小时内跑完一个 epoch）

---

## A. 协同过滤基础族（Baseline 候选）

### A1. Matrix Factorization (MF) / SVD
- **本质**: user × item rating 矩阵分解成两个低维矩阵
- **优点**: 30 行代码搞定，sklearn/Surprise 库直接调用；一定要做这个当 baseline
- **缺点**: 不能用 side features（cuisine、地理、context 进不来）；冷启动差
- **角色**: 强制基线（写报告 criterion 5/6 时拿来对比）

### A2. Alternating Least Squares (ALS)
- **本质**: MF 的高效求解算法（implicit feedback 友好）
- **优点**: Spark MLlib 原生支持，能扛 Yelp 全量；implicit-feedback 拿手
- **缺点**: 同 MF，无 side features
- **角色**: 大数据场景 baseline，可选

### A3. Neural Collaborative Filtering (NCF)
- **论文**: He et al. 2017
- **本质**: 把 MF 里的内积换成 MLP 学交互
- **优点**: 第一个把 DL 引入 CF 的代表作；实现简单
- **缺点**: 比纯 MF 没显著优势的研究证据已有（"是否 deep 真的有用"是个争议）
- **角色**: 写报告时引用作为"DL-for-CF 的转折点"

---

## B. Factorization Machine 族 ⭐ 跟课程契合度最高

### B1. Factorization Machine (FM)
- **论文**: Rendle 2010
- **本质**: 把 LR 的二阶交叉项用 embedding 内积表示，自动学交互
- **优点**: Class 3 直接讲过，老师写在 rubric 里；可以塞任意 categorical feature
- **缺点**: 只到二阶，高阶交互需要 deep
- **角色**: FM 一定要做（baseline + 课程契合）

### B2. Field-aware FM (FFM)
- **论文**: Juan et al. 2016
- **本质**: 每个 feature 对每个 field 学一个 embedding（不像 FM 全局共享）
- **优点**: CTR 预估比赛常胜军（Criteo / Avazu）
- **缺点**: 内存开销 N_field 倍，调起来麻烦
- **角色**: 有时间再加，可放 future work

### B3. DeepFM ⭐ 推荐做主模型
- **论文**: Guo et al. 2017 (Huawei)
- **本质**: FM + DNN 并联，**共享 embedding**
- **优点**: 一行 import 就能跑（torch-rec 或 RecBole 或 deepctr-torch）；同时覆盖 FM（二阶）和 DNN（高阶）；Class 3 + Class 4 知识刚好覆盖
- **缺点**: 比纯 FM 重一些，但 Yelp 量级单卡完全够
- **角色**: **建议作为主交付模型**（rubric 5/6 主角）

### B4. xDeepFM
- **论文**: Lian et al. 2018 (KDD)
- **本质**: DeepFM 的升级版，用 CIN（Compressed Interaction Network）显式学高阶交互
- **优点**: 比 DeepFM 在多个 benchmark 上更强；学术深度好讲故事
- **缺点**: 实现复杂度上一个台阶
- **角色**: 可选 stretch goal

---

## C. 自动特征交叉族

### C1. Wide & Deep (Google 2016)
- **本质**: 线性模型（wide，需要手工交叉特征）+ DNN（deep，自动）并联
- **优点**: 工业级经典；Tensorflow 官方教程级实现
- **缺点**: Wide 端要人手做交叉特征，工作量大；近年被 DeepFM 取代
- **角色**: 写报告时引用为"DeepFM 的前身"

### C2. Deep & Cross Network (DCN / DCN-v2)
- **论文**: Wang et al. 2017 / 2020
- **本质**: 把 Wide 端换成 Cross Network（自动学高阶 cross feature，无需手工）
- **优点**: 自动 + 高效；Google 在 YouTube/Search 用
- **缺点**: PyTorch 实现要自己写或用 deepctr-torch
- **角色**: 跟 DeepFM 平级的 alternative，可做对比实验加分

---

## D. 双塔检索族（适合做 Layer 1 candidate generation）

### D1. Two-Tower / DSSM
- **本质**: User 塔 + Item 塔分别 embed，最后 cosine 相似度匹配
- **优点**: 训完 item embedding 离线建 ANN 索引，线上毫秒级召回；Yelp 150K 商家正合适
- **缺点**: 表达能力弱于 ranker（不能精排）
- **角色**: 跟 DeepFM 配合：Two-Tower 召回粗排 → DeepFM 精排（推荐两层架构）

### D2. YouTubeDNN
- **论文**: Covington et al. 2016
- **本质**: 大型工业双塔的代表作
- **优点**: 工业落地参考价值高
- **角色**: 可以引用为"Two-Tower 的代表实现"

---

## E. 序列 / 上下文感知族（如果想吃 Class 6 RNN 的红利）

### E1. GRU4Rec
- **论文**: Hidasi et al. 2016
- **本质**: 用 GRU 处理 session 内 click 序列
- **优点**: Class 6 RNN 直接对接
- **缺点**: 需要 session 数据；Yelp 是 review 数据，"session"要自己合成（按 user_id + 时间窗口）
- **角色**: 可作 ablation 模型（"加入序列建模 vs 不加"）

### E2. SASRec / BERT4Rec
- **论文**: Kang & McAuley 2018 / Sun et al. 2019
- **本质**: 用 self-attention / BERT 处理用户行为序列
- **优点**: Class 7 Transformers 红利；近 3 年 SOTA 推荐架构主流
- **缺点**: 数据量小容易过拟合
- **角色**: 等 Class 7 学完可以挑战；现在做略早

---

## F. 我的"如果我做"会选什么

如果让我从零起手且只能选一条路：

**Layer 1（候选召回）**: Two-Tower（D1）—— 用 user_id + city 召回 top-200 candidate
**Layer 2（精排）**: DeepFM（B3）—— 加入 cuisine / price / hour / distance / day_of_trip 等特征做 final ranking
**对照 baseline**: FM（B1）+ MF（A1）—— 写消融的素材

每加一层 model 复杂度，记得在报告里讨论：
- 有没有过拟合（train AUC vs val AUC gap）
- 有没有体现 deep 的价值（vs FM 的提升幅度）
- 有没有 cold-start 表现（新城市新用户）

---

## 你们调研时建议产出

每个候选写 5 行：
1. 一句话讲它做啥
2. Yelp 上能不能直接训（数据接口能不能映射）
3. 跟我们 travel-aware context 怎么结合
4. 实现路径（库、参考实现链接、训练成本估计）
5. 推荐 / 不推荐 + 一句理由

不限制必须从这份清单里选。如果你们发现了新的 SOTA / 觉得更适合的方向，加进调研即可。
