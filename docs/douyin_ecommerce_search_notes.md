# 抖音电商搜索 业务思考（Haobo 前业务沉淀）

> **来源**：Haobo 在前抖音电商工作期间对搜索系统业务侧的笔记。截图分享于 2026-05-05，作为 ML2 期末项目（Taste hunter）方法学讨论的背景材料——证明 Haobo 对 search 范式有第一手经验。
>
> **本文档定位**：reference / 背景资料。不是 PRD 主体内容，但澄清了"搜索 vs 推荐"在工业上是两种独立成熟的 pipeline，**Taste hunter 项目 ML2 评分语境下我们走推荐路径（FM/DeepFM）**，但 Haobo 提的"我们 chatbot 主流是搜索"洞察来自此处的真实业务背景。
>
> **转录说明**：原始为 Notion 长截图，部分小字号段落分辨率受限，标 `[?]` 处表示推测，需 Haobo 校对补全。

---

## 1. 目标用户场景

> 用户在抖音电商进行购物时的典型场景

- 有意识 / 无意识的购物消费场景区分
- 看了直播 / 短视频被"种草" → 触发搜索
- 主动搜索某个具体商品 / 类目
- 价格敏感型 vs 品牌敏感型用户区分 `[?]`
- 货架式逛 vs 精准搜索两种模式

## 2. 搜索行为痛点

- 大量品类选择困难
- 搜索词模糊（描述性而非精确商品名）
- 关键词不准确，结果不相关
- 用户期望和搜索结果之间的 gap
- 多模态意图（看了视频想买类似的）`[?]`

## 3. 大方向：看起来需要做什么？

- 提高搜索效率
- 用户场景理解（购物意图分类）
- 搜索意图识别（搜索词 → 真实想买的）
- 个性化排序（结合用户历史）
- 多模态信号融合 `[?]`

## 4. 看起来你需要更准 ⭐

> [!info] 核心痛点 highlighted
>
> 关键词搜索结果不准 → 需要更精确的语义匹配 → embedding-based retrieval

- 显式 query 不准（用户表达和商品 title 不一致）
- 关键词组多查 + 高权重
- 商品搜索：类目维度 + 商品维度双重处理

## 5. 建模上，我们要做什么 ——「大模型时代」

### 5.1 Embedding 层

```
Query 侧:                   Doc 侧:
用户输入 query              商品类目 + 商品文字描述
   ↓                            ↓
Word2Vec / Sentence Encoder  Doc2Vec / BERT / Sentence Encoder
   ↓                            ↓
   query_emb                    doc_emb
```

#### Word2Vec (Static Embedding)
- Word level：word → vector
- Sentence level：句子嵌入
- 分布式假设（distributional hypothesis）：上下文相似的词语义相似
- CBOW / Skip-gram 两种训练方式

#### Doc2Vec / FastText (Static Embedding)
- 文档级别 embedding
- FastText：subword n-gram，处理 OOV 友好
- 适合短 query / 商品标题

### 5.2 经典三阶段架构（搜索系统标准 pipeline）

#### 第一步：召回 (Recall)

**业务目标**：从全量商品库（千万级）缩小到候选集（万级）

| 召回方式 | 适用场景 |
|---|---|
| 倒排索引（lexical match）| 关键词精确匹配 |
| **DSSM (Deep Structured Semantic Model) 双塔** | 语义召回 |
| Embedding 检索 + cosine similarity | 向量召回 |
| ANN (Approximate Nearest Neighbor，FAISS / HNSW) | 向量检索加速 |

**关键架构**：DSSM 是双塔模型经典——query tower + doc tower 各自 MLP encode，cosine 相似度匹配。**双塔在搜索场景的标准应用**。

#### 第二步：粗排 (Pre-Ranking)

**业务目标**：召回 (~10,000) → 粗排 (~1,000)，进一步缩小候选池

- 模型选型：轻量化 ranker（线性模型 / 浅层 MLP）
- 输入特征：query 特征 + doc 特征 + 简单交叉特征
- 优化目标：粗排 NDCG 与精排接近，但延迟 << 精排 `[?]`

#### 第三步：精排 (Ranking)

**业务目标**：粗排 (1,000) → 精排 top-K (10-100) 展示给用户

- 模型选型：DeepFM / Wide&Deep / DCN / xDeepFM
- 输入特征：完整 user × query × doc × context 特征
- 优化目标：业务 metric（CTR / CVR / GMV）`[?]`

### 5.3 重排 (Re-ranking)

精排之后还有重排层，处理：
- 多样性约束（同类目商品不扎堆）
- 业务规则（运营 boost / 黑名单）
- 个性化策略 `[?]`

---

## 6. 数据 / 输入特征

### 6.1 用户侧特征
- 用户画像（性别 / 年龄 / 城市 / 消费等级）
- 历史行为（点击 / 加购 / 购买序列）
- 当前 session 行为（实时点击）

### 6.2 商品侧特征
- 类目 / 品牌 / 价格 / 销量
- 商品标题 + 描述 embedding
- 商品图 embedding `[?]`
- 评分 / 评论数

### 6.3 Query 侧特征
- Query 关键词
- Query embedding
- Query 类目预测
- Query 历史行为统计 `[?]`

### 6.4 Context 特征
- 时间（小时 / 星期 / 节假日）
- 地理（lat/lon）
- 设备 / 网络类型 `[?]`

---

## 7. 大模型时代的搜索（衍生讨论）

### 7.1 BERT / Transformer 在搜索的应用

- Query 理解：BERT 做 query intent 分类
- 双塔升级：BERT-based query/doc encoder（如 ColBERT）
- Cross-encoder 精排：query × doc 拼接喂 BERT，输出 relevance score
- 大模型时代：GPT 类生成式查询理解 / 重写

### 7.2 Pre-trained Model 的优势

- 预训练在大规模文本上，捕获通用语义
- Few-shot 适配下游任务
- 多语言 / 跨域迁移能力 `[?]`

### 7.3 部署考量

- 双塔可离线预计算 doc embedding，线上只需 query encode + ANN 检索 → 毫秒级
- Cross-encoder 在线推理慢，只用在精排 top-100
- 大模型成本：用蒸馏 / 量化压缩 `[?]`

---

## 8. Transformer 架构原理（背景）

> 这部分可能是 Haobo 的学习笔记延伸，记录 Transformer 在搜索场景的实战要点

- Self-attention：每个 token 关注全序列其他 token
- Multi-head attention：不同 head 关注不同语义层面
- Position encoding：注入位置信息
- 编码器 / 解码器结构 `[?]`

### 8.1 BERT (Bidirectional Encoder Representations from Transformers)

- 预训练任务：MLM (Masked Language Model) + NSP (Next Sentence Prediction)
- 下游适配：[CLS] token 分类 / [SEP] 分隔
- 用法：
  - Query encoder（替代 Word2Vec）
  - Cross-encoder 精排
  - Query intent 分类

### 8.2 GPT 类生成式

- Causal LM 自回归生成
- 用法：
  - Query 改写 / 扩展
  - 生成式搜索结果摘要
  - 对话式搜索 `[?]`

---

## 9. 业务挑战 / 反思

> 这部分疑似是 Haobo 在抖音电商实际遇到过的问题汇总，部分小字读不清

- **类目跨界问题**：query 横跨多个类目时（如"运动鞋"既是男装也是女装），召回如何分配 `[?]`
- **冷启动商品**：新上架 SKU 没有历史点击数据，召回排名劣势
- **Long tail query**：低频 query 索引覆盖率低
- **多模态融合**：视频 / 直播触发的 query 如何利用视频内容信息 `[?]`

---

## 10. 这份笔记跟 ML2 Taste hunter 项目的关系

> [!success] 关键澄清——为什么 Haobo 反对把 Taste hunter 定位成"搜索"
>
> 1. **Haobo 有一手搜索业务经验**——上面这套抖音电商三阶段（召回 / 粗排 / 精排）+ DSSM 双塔 + BERT query 理解 + 重排是工业标准搜索 pipeline
> 2. **搜索系统的核心范式是 "用户给 explicit query → 系统返回相关 docs"**——抖音电商搜索就是这个，每个 user 行为都从输入 query 框开始
> 3. **Taste hunter 不是这个范式**——主屏 F1 进入时用户**没有打字**，系统主动推送基于 user features × context 的卡片，这就是 push recommendation
> 4. **F1 chatbot 对话流（S2/S6）是 conversational recommendation (CRS)**，不是搜索——区别在于 CRS 多轮对话累积偏好，搜索是单 query 单结果
> 5. **ML2 课程语境是 recsys 范式**（FM/DeepFM 是 Bose 课程明确点名工具，Bose rubric 也写 "recommender system (hybrid or factorization machine)"）；搜索 / IR 不在 ML2 课程内容范围
>
> **结论**：Taste hunter 项目正确定位为 **DeepFM-based Conversational Recommender System (CRS)**——recsys 关键词 + deep learning 关键词同时命中 rubric。架构上虽然跟搜索 pipeline 有相似元素（双塔召回 / 精排 / 重排），但术语不写"搜索"，写"hybrid recommender"。

### 架构上能从抖音搜索 pipeline 借鉴的部分

| 抖音搜索 pipeline 阶段 | Taste hunter 对应模块 | 备注 |
|---|---|---|
| Query 理解（BERT intent 分类）| LLM intent extraction（Sonnet）| §3.2 v2 S2 |
| 召回（DSSM 双塔 + ANN）| Two-Tower (DSSM) 召回 | §3.3.4 v2 stretch goal，仅用于 S1 push recsys 路径 |
| 粗排（轻量 ranker）| ❌ 不需要——候选池只有 ~13K 餐厅，DeepFM 直接精排 | Yelp 商家数 << 抖音 SKU 数 |
| 精排（DeepFM）| DeepFM 精排 | §3.3.4 主交付 |
| 重排（多样性 boost）| MMR 重排 | §3.3.4.5 v2，用于 F2 trip plan per-period top-3 多样性 |

### 不借鉴的部分

| 抖音搜索元素 | 不借鉴的原因 |
|---|---|
| BM25 / 倒排索引 | Yelp 餐厅没有大量 text 字段；query 也是 LLM 抽出的 structured intent 不是关键词 |
| Cross-encoder 精排 | DeepFM 已足够，cross-encoder 是 search 大模型方案，跟 ML2 recsys 关键词不对齐 |
| Query 改写 / 扩展 | LLM 已替代这一步，不需要单独 query expansion 模块 |

---

<!-- douyin_ecommerce_search_notes · 2026-05-05 · 转录自 Haobo 截图 · 部分段落 [?] 待补 -->
