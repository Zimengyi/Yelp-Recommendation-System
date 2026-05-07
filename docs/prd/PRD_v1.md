# [PRD] Travel-aware Restaurant Recommender · ML2 Class Project `.draft`

> 状态：v1 草稿 · 2026-05-04 · 待 5/5 周二 12:00 同步会评审

---

## §0 Basic Info | 基础信息

| 字段            | 值                                                               |
| ------------- | --------------------------------------------------------------- |
| **文档标题**      | Travel-aware Restaurant Recommender — ADSP 31018 ML2 期末 Project |
| **状态**        | `.draft v1`                                                     |
| **课程**        | ADSP 31018 Machine Learning II（Spring 2026，Prof. Arnab Bose）    |
| **权重**        | 40% 期末成绩（40 分 / 8 项 × 5 分 rubric）                               |
| **Doc Owner** | Haobo Yang                                                      |
| **Reviewers** | Prof. Arnab Bose · Zimeng · Cindy                               |
| **分工**        | Haobo（PRD + 推荐模型）/ Zimeng + Cindy（EDA + 模型调研）                   |
| **Priority**  | P0（期末交付，单次机会）                                                   |
| **Deadline**  | **2026-05-23（周六）** · 距今 19 天                                       |

### Change Log

| Date | Description | 修改人 |
|---|---|---|
| 2026-05-04 | v1 初稿：Basic Info + Background + 章节骨架 | Haobo |
| 2026-05-04 | Deadline 锁定 2026-05-23（确认值，非估算） | Haobo |
| 2026-05-04 | §3 Requirement Details 全节合入（4-Sib 并行产出 + 合并体检）：§3.1 UI · §3.2 LLM · §3.3 推荐模型 · §3.4 评测系统 | Haobo |
| 2026-05-04 | §3 v2 升级（4-Sib 第二轮）：基于 Figma Make 原型 audit 重写 §3.1（F1.1 bottom-sheet + F2 day-tab）、§3.2 重组为 10 个产品场景 S1-S10、§3.3 加 H9/H10 + 3 新特征 + MMR 子节、§3.4 加 4 trip 维度 + Trip 独立评测协议 | Haobo |

### 关联文件

| 类型 | 文件 | 用途 |
|---|---|---|
| 评分规则 | `project_rubric.png` | 8-criterion rubric 原图 |
| 历史项目 | `past_projects.md` | 18 个历届 project 复盘 |
| 候选 proposal | `proposals.md` | 4 个备选方案对比（敲定 B） |
| 模型调研 | `model_candidates_overview.md` | 推荐系统候选模型速览 |
| 需求原文 | `requirements_log.md` | 用户语音需求 + 范围划定 |
| 原型设计 | `wireframe_v1.jpg` | chatbot UI 草图 v1 |
| 会议纪要 | `meeting_2026-05-01.md` | 5/1 同步会决策 |

### 范围声明（In / Out of Scope）

✅ **In scope（评分对象）**
- 推荐模型：DeepFM 主交付 + FM/MF baseline + 离线评测
- LLM Agent 包装：意图抽取 + tool calling + 响应合成
- Demo 前端：可端到端演示 F1 主屏推荐 + F2 Trip Plan

❌ **Out of scope（明确排除，避免评审纠结）**
- 生产级 UI / 移动端 / 登录系统 / 支付
- 真实 GPS / 真实用户行为日志 / 实时数据
- 多语言支持（仅英文 Yelp review）
- 推荐结果的合规审查 / 内容安全
- 数据库部署 / REST 服务 / 微服务拓扑（→ 不在 ML2 评分范围）

---

## §1 Background | 需求背景

> [!info] 💡 What we build
>
> 一个**旅行场景下的餐厅推荐 chatbot agent**：用户进入即看到基于地理位置 + 周榜的卡片流；通过自然语言对话表达偏好（"想吃辣""人均 $30 以内""带小孩""趁夕阳吃海鲜"），agent 抽取意图后调用底层 **DeepFM 推荐器**，返回排序后的餐厅卡片；用户也可上传多日行程，由系统按"日 × 区域 × 三餐"自动生成可执行的 trip-meal-plan。数据走 **Yelp Open Dataset**（自带商家 lat/lon + review + 类目，免去 Google Maps API 依赖）。

> [!tip] ⭐ Why build（4 个论点）
>
> 1. **Rubric 显式邀请** —— Bose 在评分细则里写明"deep learning **OR recommender system (hybrid or factorization machine)**"，并且 Class 3 单独讲了 FM。把 FM/DeepFM 做出来 = 把老师写在卷子上的关键词原样还给他。
> 2. **历史 18 个 project 里只有 1 个推荐器**（GoodReads Book Recommender），56% 是 CV 分类的同质化。**做推荐 = 不撞车 + 升级（DeepFM > vanilla CF）**。详见 `past_projects.md` 的 pattern read。
> 3. **课程契合度二连击** —— FM 命中 w3，DNN/dropout/L2 命中 w4，序列上下文（trip plan 时间轴）可挂 w6 RNN。一个 project 覆盖 3 周课程内容，rubric criterion 5/6（overfitting / regularization）有充足素材。
> 4. **Hybrid 架构是天然 showcase** —— LLM agent（对话/意图）+ DeepFM（推荐）+ Two-Tower（召回）三层，能一次性体现 deep learning 与 recommender 两条评分路径，比单跑模型更有"系统设计"感，criterion 7（learnings）和 8（future work）会更好写。

### Feature Result | 用户场景

![[wireframe_v1.jpg]]

> [!example] 用户旅程（对应 wireframe v1）
>
> **左图（F1 主屏）** —— 用户打开 chatbot，默认渲染卡片流：基于当前位置 + 周榜热度，给出当日推荐（例：上午 10 点 Moonlark's Dinette · 晚上 7 点 Water Grill）。每张卡片含图片 / 时间建议 / 名字 / 评分 / 类别 / 一句话描述。底部有持续输入框，可继续对话精化。
>
> **右图（F2 Trip Plan 视图）** —— 用户点顶部 "Trip plan" 按钮，输入多日行程（例：LA 3 天）。系统按日组织（DAY 3 · LA 市区 + 圣莫尼卡），每天 morning/lunch/dinner 各一家，区域内距离合理 + 跨日 cuisine 多样化。卡片右上 "Open route" 一键拉起地图导航 / "Copy" 复制行程文本。
>
> **关键差异化** —— 不是"列出附近餐厅"（Google Maps 已经能做），而是**理解用户对话上下文 + 行程结构后**给出受约束的推荐。约束维度：地理（同区域）、时段（早午晚匹配营业时间）、多样性（跨日不重 cuisine）、个人偏好（对话中累积）。这套约束注入到 DeepFM 的 ranking 阶段作为 context features。

### 与 ML2 8-Criterion Rubric 的章节映射

> [!success] ✅ 决策：PRD 章节直接映射 rubric，老师批卷可对号入座

| Rubric 项 | 评分项 | PRD 对应章节 |
|---|---|---|
| 1 | Problem Statement | §1 Background（本节） |
| 2 | Assumptions / Hypotheses | §3.3.1 模型假设 |
| 3 | Exploratory Data Analysis | §3.3.2 EDA（Zimeng+Cindy 主笔） |
| 4 | Feature Engineering & Transformations | §3.3.3 特征工程 |
| 5 | Proposed Approaches + overfit/underfit checks | §3.3.4 模型方案 + 过拟合检查 |
| 6 | Proposed Solution + regularization | §3.3.5 选型 + 正则化 |
| 7 | Results + Learnings | §3.4 评测系统 |
| 8 | Future Work | §6 开放问题 / Future Work |

> [!warning] ⚠️ 范围风险
>
> Agent 形态 + 前端 demo **不会被评分**（rubric 8 项里没有 UX/system design 维度）。它们的存在是为了让推荐模型有"真实使用场景"作为 EDA 和 future work 的素材。**精力分配：模型 70% / Agent 20% / 前端 10%**。如果时间紧张，砍前端保模型。

---

## §2 Success Metrics

> [!info] 占位 — v1 暂未展开
>
> §2 待写。计划 3 个 Key Result：
> - **K1 模型质量**：DeepFM 离线 NDCG@10 ≥ 0.30 · AUC ≥ 0.75 · Cold-start AUC ≥ 0.65（具体目标见 §3.4.1 离线评测维度表）
> - **K2 课程评分**：8-criterion rubric 全绿（每项 ≥ 4/5；目标总分 ≥ 36/40）
> - **K3 端到端 Demo**：F1 + F1.1 + F2 三屏可端到端演示（5/22 演练通过）

---

## §3 Requirement Details

> [!info] 📐 本章导航 — 占全文 60-80%
>
> §3 是 PRD 主体，按 elfen 模板四件套规则组织。本章经历 v1（4-Sib 并行产出）→ v2（基于 Figma Make 原型 audit 重写）两轮迭代，**当前 transclude 全部链接 v2 版本**：
>
> | 子节 | 主题 | v2 篇幅 | v2 关键变更 |
> |---|---|---|---|
> | **§3.1** | User Interaction & Design | 516 行 | F1.1 改为 **bottom-sheet modal + 底部中央 nav**；F2 改为 **day-tab + activity 描述 + 每段 3 候选 + indicator dots**；新增导出按钮；删除侧边浮动箭头 + 左轨时间标签 + Open route/Copy 双 pill |
> | **§3.2** | LLM Workflow | 1254 行 | 重组为 **10 个产品场景 S1-S10**（按 feature scenario 而非 abstract step），每场景含触发/输入/workflow/全 prompt/输出；新增 `summarize_reviews_for_overview` 和 `modify_trip_slot` 两 tool |
> | **§3.3** | 推荐模型 Spec | 559 行 | 新增 H9/H10 假设；新增 3 个 context 特征（period_id / activity_emb 32-dim sentence-transformer / prior_meals_cuisines）→ **特征数 23 → 26**；**新子节 §3.3.4.5 MMR 重排 + 启发式约束层**；新增 L7/L8 风险（**ML2 评分主战场**） |
> | **§3.4** | 评测系统 | 248 行 | 新增 **4 个 trip 评测维度**（Trip Diversity Simpson / Geographic Compactness / Activity-Restaurant Match / Per-Period Diversity）；新增 4 个 case C9-C12；**新子节 §3.4.4b Trip 独立评测协议**（12 手工 case + 3 ablation） |
>
> Mermaid 全章预算 1 张，已用于 §3.2.0 链路概览。
>
> **配套 reference 文件**：
> - [`figma_make_audit.md`](./figma_make_audit.md)（221 行）— v1→v2 重写依据，列出 Figma Make 原型与 v1 PRD 的所有偏差 + 10 个产品场景识别
> - [`figma_make_prompt.md`](./figma_make_prompt.md)（255 行）— 给 Figma Make 的 self-contained 英文 prompt
> - v1 各 section md 文件保留于目录（标注 deprecated），供差异回溯

---

<!-- ============================================================ -->
<!-- §3.1 — Sib A · User Interaction & Design                     -->
<!-- ============================================================ -->

### §3.1 User Interaction & Design

> [!info] 📐 本节定位
>
> §3.1 覆盖 Taste hunter 的全部前端交互规格。三个屏幕（F1 Chat Home / F1.1 Restaurant Detail Overlay / F2 Trip Plan）均已通过 Figma Make 高保真原型落地，设计源文件见 [Figma 设计稿](https://www.figma.com/design/QNag6s9bFw3eYiAWBohFK7)。本节每个子章遵循「视觉范例表 → 字段大表 → 决策 callout → 风险 callout」四件套结构（参照 Elfen PRD 标准模板 §3.4.1）。
>
> 重要边界：UI 在 ML2 rubric 的 8 项评分中不单独计分；其存在目的是为推荐模型提供端到端可演示的上下文，并为 EDA / future work 段提供数据流锚点。精力分配目标：模型 70% / Agent 20% / 前端 10%。

完整内容见独立文件 **v2**：[`PRD_v1_section3.1_UI_v2.md`](./PRD_v1_section3.1_UI_v2.md)（516 行；基于 Figma Make 原型 audit 重写，F1.1 改为 bottom-sheet + 底部中央 nav，F2 改为 day-tab + activity 描述 + 每段 3 候选）。v1 见 [`PRD_v1_section3.1_UI.md`](./PRD_v1_section3.1_UI.md)（已 deprecated）。

> 渲染时由 Markdown 工具链 inline transclude（Obsidian / Foam / mdx 均支持 `![[...]]` 或 `<embed>`）；冷渲染场景下读独立文件即可。

![[PRD_v1_section3.1_UI_v2]]

---

<!-- ============================================================ -->
<!-- §3.2 — Sib B · LLM Workflow                                  -->
<!-- ============================================================ -->

完整内容见独立文件 **v2**：[`PRD_v1_section3.2_LLM_v2.md`](./PRD_v1_section3.2_LLM_v2.md)（1254 行；按 10 个产品功能场景重组 S1-S10，每个场景含触发条件 / 输入数据表 / 工作流（含 LLM prompt 全文）/ 输出 schema；新增 `summarize_reviews_for_overview` 和 `modify_trip_slot` 两个 tool；新增 trip 场景 fallback；按场景重新估算成本）。v1 见 [`PRD_v1_section3.2_LLM.md`](./PRD_v1_section3.2_LLM.md)（已 deprecated）。

![[PRD_v1_section3.2_LLM_v2]]

---

<!-- ============================================================ -->
<!-- §3.3 — Sib C · 推荐模型 Spec（ML2 评分主战场）                  -->
<!-- ============================================================ -->

完整内容见独立文件 **v2**：[`PRD_v1_section3.3_Model_v2.md`](./PRD_v1_section3.3_Model_v2.md)（559 行；新增 H9/H10 假设、3 个新 context 特征（period_id / activity_emb / prior_meals_cuisines，特征数 23 → 26）、新子节 §3.3.4.5 MMR 重排 + 启发式约束层、L7/L8 风险）。v1 见 [`PRD_v1_section3.3_Model.md`](./PRD_v1_section3.3_Model.md)（已 deprecated）。

![[PRD_v1_section3.3_Model_v2]]

---

<!-- ============================================================ -->
<!-- §3.4 — Sib D · 评测系统                                       -->
<!-- ============================================================ -->

完整内容见独立文件 **v2**：[`PRD_v1_section3.4_Eval_v2.md`](./PRD_v1_section3.4_Eval_v2.md)（248 行；新增 4 个 trip 评测维度（Trip Diversity Simpson 系数 / Geographic Compactness / Activity-Restaurant Match / Per-Period Candidate Diversity）、4 个新 case C9-C12、3 个 Agent trip 子维度、新子节 §3.4.4b Trip 独立评测协议（12 个手工 trip case + 3 ablation 设计））。v1 见 [`PRD_v1_section3.4_Eval.md`](./PRD_v1_section3.4_Eval.md)（已 deprecated）。

![[PRD_v1_section3.4_Eval_v2]]

---

## §4 LLM Tools 清单

> [!info] 占位 — v1 暂未展开
>
> §4 计划由 §3.2.3 Tool 接口表抽取为附录，便于工程实装阶段快速检索 schema。当前 §3.2 内已包含完整 TS interface，§4 的独立化在排版收尾阶段进行（5/22 前）。

---

## §5 实施计划与里程碑

> [!info] 占位 — v1 暂未展开
>
> §5 待写。基于 19 天倒排：
>
> | 周期 | 日期 | 关键节点 |
> |---|---|---|
> | 本周末 | 5/4–5/5 | PRD v1 + EDA 起手（**5/5 周二 12:00 同步会**） |
> | w7 | 5/6–5/11 | EDA 终稿 + DeepFM 基线跑通 + Two-Tower 召回训练 |
> | w8 | 5/12–5/18 | 模型迭代 + 正则化 sweep + Agent 层接通 + Demo 集成 |
> | w9 前半 | 5/19–5/22 | 实验定稿 + writeup 8 项 + Demo 演练 + Layer C 自检 |
> | **DDL** | **5/23 周六** | 提交 |

---

## §6 开放问题 / 待定决策

> [!info] 占位 — v1 暂未展开
>
> §6 计划汇总：
> - **5/1 会议 4 项 TBD**：① LLM 选型 ✅（已在 §3.2.1 锁定 Sonnet 4.6）/ ② Demo 前端 Streamlit vs React（建议 Streamlit）/ ③ Trip Plan 启发式层是否纳入交付（建议 stretch goal，5/19 checkpoint 决定）/ ④ Photos.json 5GB 是否下载（建议不下载，UI 用 placeholder + photo_count 元数据）
> - **§3.3.7 模型层 6 项限制**：L1 trip-context 合成假象 / L2 城市覆盖不均 / L3 Two-Tower 进度风险 / L4 photos.json 决策 / L5 单 GPU 算力 vs 80 点 grid search / L6 rating ≥ 4 positive 阈值
> - **Future Work（rubric 8）**：在线 feedback loop（thumbs-up/down 已埋点）/ GRU4Rec 序列模型 / xDeepFM CIN 高阶交叉 / 真实 trip 数据接入（Foursquare API）/ 跨语言（中文 review 接入）
