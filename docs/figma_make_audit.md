# Figma Make Prototype Audit — 2026-05-04

> **来源**：Figma Make 文件 `ssHwZecVKYUg8O5bUmwJnx`（[link](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx/Draw-Based-on-Instructions)）
> **方法**：通过 Figma MCP `get_design_context` + `ReadMcpResourceTool` 拉取了 5 个核心 React 组件源码（App.tsx / ChatHome.tsx / RestaurantDetail.tsx / TripPlan.tsx / RestaurantCard.tsx）
> **目的**：给 Sib 第二轮 §3.1 / §3.2 / §3.3 / §3.4 更新提供 ground truth，使 PRD 与已落地的原型严格对齐

---

## 1. 三屏并列展示（App.tsx）

App 是一个并排展示三屏的 demo wrapper（横向 flex），不是真实导航流。每屏标题：`F1 — Chat Home` / `F1.1 — Restaurant Detail` / `F2 — Trip Plan`。点击单屏切换 `currentScreen` state，但当前 demo 主要用作三屏对照展示。**实装时三屏需要变成单屏 + 真实 routing**（F1 → F1.1 modal slide-up → F1，F1 → F2 via Trip Planner pill）。

---

## 2. F1 Chat Home（ChatHome.tsx）

### 与 PRD §3.1.1 一致的部分 ✅
- Top bar peach `#F5DCA6` + Menu / "Taste hunter" / UserCircle
- Greeting block：`Wed brunch in Redmond ☕` + `10:32 AM · 5 picks based on your location & this week's trends`
- 3 张卡片，硬编码 (Moonlark's / Cafe Corina / Marlowe's Kitchen)，与 PRD 演示数据一致
- chevron 展开/收起逻辑（state `expanded`，按钮在第 3 卡下方居中）
- Message actions：Copy / ThumbsUp / ThumbsDown / RefreshCcw（lucide-react，18pt #8A8A8A）
- Quick action：Trip Planner pill (背景 #EBEBEB，含 Plane icon)
- Input bar：placeholder + 黑色圆形 send 按钮（chevron-up white icon）

### 与 PRD §3.1.1 不一致 / 需补充 ⚠️
- **F1 当前没有真实展开 4-10 卡的逻辑**，只切换 chevron-up/down icon。PRD 之前说的"展开到 top-10"实装为**TODO**，前端逻辑只占了 placeholder。
- **send button enabled / disabled 状态没有实装**——总是显示黑色实心。PRD 写的"opacity 0.30 when input empty"需要在最终实装时补上。

---

## 3. F1.1 Restaurant Detail Overlay（RestaurantDetail.tsx）— **与 PRD 出入最大**

### 重大差异（PRD 必须重写）

| 项 | PRD §3.1.2 当前规格 | Figma Make 实际实现 | 行动 |
|---|---|---|---|
| **形态** | 全屏 modal slide-up（占满 844pt） | **bottom sheet modal**（占屏幕 95% 高 + rounded-top 20pt + 黑色 40% backdrop） | PRD 改为 bottom sheet |
| **Hero photo 高度** | 240pt | **280pt** | PRD 改 280pt |
| **侧边浮动 nav 箭头**（y=540 left/right edges） | absolute 浮在两侧边缘 | **❌ 不存在**——替换为**底部中央 nav bar** | PRD 删除侧边箭头规格，改为底部 nav |
| **底部 nav** | 不存在 | `‹` + `[2 of 3]` 计数 pill + `›`，居中排列在 `bottom-8`（距底部 32pt），白色圆按钮 + 阴影 | 新增到 PRD |
| **Counter 圆按钮尺寸** | — | 48×48pt（w-12 h-12，比侧边箭头方案的 44pt 大） | PRD 补充规格 |
| **Counter 中央 pill** | — | 白色 pill，`2 of 3` 文字 (15pt Medium #1A1A1A，shadow 0 2 8 rgba(0,0,0,0.12)) | 新增到 PRD |

### 与 PRD 一致 ✅
- Top bar 同 F1
- Hero photo 暖棕 placeholder #B8A89E
- 左上 close X 圆按钮 32×32pt 白色 + X icon (16pt #222)
- 右下 Camera + "5" 黑色 55% opacity 计数 pill
- Title row：Playfair Display Bold 22pt "Tatsu Ramen   (Arts District)" + Copy icon
- Meta row：4.7 + filled SVG star + 571 · Ramen restaurant + $（左右分组）
- Action pills：Directions 黑底白字 + Call/Website outline `#C7C7C7` 1pt
- Content panel：`#EBEBEB` bg + 16pt padding + AI Overview / Review · ★ 4.7 / menu 三段 + 1pt #D6D6D6 分隔线
- Mock 内容：tonkotsu 12 小时熬制 / Yelp top review / Tonkotsu $16 · Spicy Miso ... / Yelp Open Dataset 归因

---

## 4. F2 Trip Plan（TripPlan.tsx）— **与 PRD 出入很大**

### 重大差异（PRD 必须重写）

| 项 | PRD §3.1.3 当前规格 | Figma Make 实际实现 | 行动 |
|---|---|---|---|
| **结构** | 多日纵向堆叠（DAY 1 / DAY 2 / DAY 3 各占整屏区） | **Tab 切换式**——顶部胶囊 tabs `[DAY 1] [DAY 2] [DAY 3]`，选中黑底白字，其他灰；只渲染当前日 | PRD 重写为 tab 形态 |
| **每日内结构** | 每日 1 张 morning + 1 张 lunch + 1 张 dinner card | **每日 3 段**（早晨 / 中午 / 晚上），每段含 1 个 **activity 描述** + 1 张餐厅卡片（带左右切换 + 指示点） | PRD 加 activity 字段 + 切换交互 |
| **餐厅候选数** | 每段 1 张固定 | **每段 3 个候选**，用户用 ‹ › 切换 + 底部 indicator dots（1.5×1.5pt 黑/灰圆点）显示位置 | PRD 加 candidate cycling 交互 |
| **Day header pills**（Open route + Copy） | "Open route" 黑底 pill + "Copy" outline pill 在每日块顶部 | **❌ 不存在**——日级别 navigation 全部依赖 day tabs | PRD 删除 Open route / Copy pill |
| **顶部 export 按钮** | 不存在 | Greeting block 右侧有一个 outline pill `Download icon + 导出` | 新增到 PRD |
| **左轨时间标签**（vertical-rl 上午 10 点 / 下午 1 点 / 晚上 7 点） | 每张卡片左侧 40pt 宽 vertical text | **❌ 不存在**——period 标题 (早晨/中午/晚上 Inter Semi Bold 15pt) 直接放在卡片**上方**作为 section header | PRD 删除 left rail，改为 above-card section header |
| **Activity 描述行** | 不存在 | **新增** Inter Regular 13pt #4D4D4D，放在 period title 和 card 之间，描述当时段的活动建议（如"参观盖蒂中心，欣赏欧洲艺术收藏..."） | PRD 加 activity 字段 |
| **Reason chip 风格** | 同 F1 卡片 | 同样使用 #F0F2FF / #3349B3，但 **F2 中的 chip 文案承载行程约束理由**（如"距盖蒂中心 0.3 mi"、"看完日落 5 min 步行"） | 和 F1 共享样式 ✓ |

### Trip 数据规模
- 每个 day 数据：3 periods × 3 candidates = 9 餐厅候选
- 全 trip：3 days × 9 = 27 餐厅候选 + 9 段 activity 描述
- demo 数据已硬编码 LA 3-day trip（盖蒂中心 / Santa Monica / Venice / Arts District / Griffith Observatory / Hollywood / LACMA / Rodeo Drive / Little Tokyo），覆盖经典 LA 行程动线

### 与 PRD 一致 ✅
- Top bar 同 F1（peach + ☰ Menu + Taste hunter + UserCircle）
- Greeting H1 `LA · 3 days · 9 meals` + subtitle `Generated from your itinerary · regional clustering + cuisine diversity`
- 卡片视觉规格（80×96pt photo placeholder #DCDDE8 + name + meta + desc + reason chip）继承 RestaurantCard.tsx
- Input bar 同 F1（placeholder 复用）

---

## 5. RestaurantCard 共享组件（RestaurantCard.tsx）

接受 `restaurant` props（id / name / rating / reviewCount / category / price / description / reasonChip / time?），外加可选 `onClick`。**两屏共享同一组件**：F1 ChatHome 渲染时不传 `time`，F2 TripPlan 也不传 `time`（实际使用 above-card section header 而非 left rail）。

`time` 字段的 `vertical-rl` writing mode 只在传 time 时生效——这意味着代码留了"左轨时间"插槽但实装没用上。**PRD 应当删除 left-rail 设计、保留 RestaurantCard 的 time 字段为可选属性**（注释为 "deprecated, kept for schema flexibility"）。

---

## 6. 按"产品功能场景"梳理 LLM / 推荐器调用点 (用于重构 §3.2)

下面是用户与 Taste hunter 交互过程中所有触发 LLM 或推荐器的场景。Sib B2 应按这个顺序结构化重写 §3.2。

### 场景 S1 — F1 进入屏初始推荐 feed
- **触发**：用户打开 app（或从 F1.1/F2 返回 F1）。
- **输入**：`user_ctx`（lat/lon/local_time/accumulated_prefs）+ 当前**没有**用户文本。
- **LLM 工作流**：
  1. **Greeting Synthesis LLM 子调用**（Sonnet）—— 输入当前 hour_bucket + city + day_of_week，生成 H1 + subtitle 文案（如 "Wed brunch in Redmond ☕" + "10:32 AM · 5 picks based on your location & this week's trends"）。
  2. **Recommender 调用** `recommend_restaurants(user_ctx, intent={}, location, time, top_k=10)` —— 默认 intent 为空，用 popularity + geo + time-bucket 兜底排序（DeepFM 当前 hour_bucket × city embedding × user_emb 给出 top-10）。
  3. **Reason Chip Synthesis LLM 子调用**（Sonnet）—— 对每个 top-10 候选，根据其在 ranking 中胜出的最强特征（distance / popularity / cuisine match / user history similarity）生成 ≤30 字 reason chip。
- **输出**：`CardListRender` (cards: 10) → 前端默认渲染前 3 张，chevron 控制展开。

### 场景 S2 — F1 自然语言对话精化
- **触发**：用户在 input bar 输入消息（如"想吃辣，人均 30 以下"）并 send。
- **输入**：`user_text` + `conversation_history`（最近 3 turn）+ `user_ctx`。
- **LLM 工作流**（与 §3.2 现有的 3-step 一致）：Step 1 Intent Extraction → Step 2 Tool Dispatch → Step 3 Response Synthesis。Tool 选 `recommend_restaurants`。
- **输出**：新一轮 `CardListRender`（替换前一轮卡片）+ `reply_text`（自由流文字渲染在卡片上方）。

### 场景 S3 — F1 Message Action 反馈循环
- **触发**：用户点 thumbs-up / thumbs-down / refresh 任一图标。
- **输入**：当前 message 的 `business_ids[]`（top-10 列表）+ action_type。
- **工作流**：
  - thumbs-up：log 正向 feedback 到 `user_feedback` 表（隐式 like 信号），不重新生成。
  - thumbs-down：log 负向 feedback + 触发 **soft re-rank**（call recommend_restaurants with `exclude_categories: [当前 dominant cuisine]`），返回新 list。
  - refresh：call recommend_restaurants 同样参数 + `exclude_ids: [当前已展示 10 个]`，返回 next-10。
- **输出**：thumbs：可能的新 CardListRender（dislike 时） + feedback ack。refresh：必新的 CardListRender。

### 场景 S4 — F1 → F1.1 详情卡片展开 + AI Overview 生成
- **触发**：用户点 F1 任一卡片。
- **输入**：`business_id`。
- **LLM 工作流**：
  1. **Tool 调用** `get_restaurant_detail(business_id, include_ai_overview=true, max_reviews_for_summary=10)` —— 后端从 Yelp 数据库拉商家完整信息 + top-10 reviews。
  2. **AI Overview LLM 子调用**（Sonnet）—— 输入：top-10 reviews 文本 + categories + attributes（`good_for_meal` / `ambience` / `noise_level`）+ best_dishes 推断；输出：2-3 句话 editorial summary（如 "招牌 tonkotsu，汤底 12 小时熬制；本周「辣味噌限定」别错过。本地客比游客多，氛围 chill。"）。
- **输出**：`DetailRender`（card + ai_overview + top_review + menu_preview）→ F1.1 modal slide-up 渲染。

### 场景 S5 — F1.1 Bottom Nav 兄弟切换
- **触发**：用户点 F1.1 底部 ‹ 或 › 按钮。
- **输入**：`current_index` + `total_count` + `direction` (-1 / +1)。
- **工作流**：纯前端导航，已 cache F1 卡片列表的全部 business_id。target_business_id = list[current_index + direction]。如果未 cache `RestaurantDetail`（仅 cache 了 F1 卡片字段），需异步重新调用 `get_restaurant_detail` 取得 ai_overview。
- **输出**：新一轮 `DetailRender` + 计数 pill 更新（如 "3 of 10"）。

### 场景 S6 — F1 → F2 Trip Plan 生成（核心 LLM workflow）
- **触发**：用户点 F1 Quick action `Trip Planner` pill（预填 input "Plan my trip…"）+ 提交，**或**直接在 input 输入 "我要去 LA 玩 3 天"。
- **输入**：`user_text`（行程描述）+ `user_ctx`。
- **LLM 工作流**：
  1. **Step 1 Intent Extraction** —— 检测 `is_trip_planning_request=true`。
  2. **Step 2 Tool Dispatch** —— LLM 选 `plan_trip` tool。
  3. **Trip Itinerary Parsing LLM 子调用** —— 从用户文本解析 `destination` (city/country) + `days` + 可选 `regions`（如"前两天市区，第三天圣莫尼卡"）。
  4. **Activity Sequence Generator LLM 子调用** —— 对每天 × 3 时段（早晨/中午/晚上），生成一个 `activity` 字符串（13pt body 文案，描述当时段建议的旅行活动，如"参观盖蒂中心，欣赏欧洲艺术收藏和花园景观"）。这是一个新职责，PRD 之前没有考虑。
  5. **Recommender 多次调用** `recommend_restaurants` —— 对每天 × 每时段，传入 `period_context`(activity 文本 + period 早午晚 + 当日已选 cuisine 列表) 作为额外 ranking 信号；要求返回 **top-3 候选**（不是只返回 1 家）；强制约束 candidate 与 activity 地理临近（distance constraint 0.5-2 mi）。
  6. **Diversity Re-rank 启发式层**（非 LLM）—— 跨天去重 cuisine（同一 trip 不连续 3 餐相同 cuisine）；同一时段 3 候选互相之间也要 cuisine / 价位多样化。
  7. **Trip Plan Response Synthesis** —— 拼装为 `TripPlanRender`（含 days[].periods[].activity + restaurants[3]）。
- **输出**：完整 `TripPlanRender`（27 candidate 餐厅 + 9 个 activity 描述）→ F2 渲染，默认 DAY 1 active。

### 场景 S7 — F2 Day Tab 切换
- **触发**：用户点 day tab `[DAY 1] [DAY 2] [DAY 3]`。
- **输入**：`day_index`。
- **工作流**：纯前端 state 切换，所有数据已在 S6 一次性生成。
- **输出**：当前选中日的 morning / afternoon / evening section 重新渲染。

### 场景 S8 — F2 候选切换（每段内 3 候选）
- **触发**：用户在某段 (如 morning) 点 ‹ 或 › 按钮。
- **输入**：`day_index` + `period` + `direction`。
- **工作流**：纯前端 index 切换 + indicator dot 更新。
- **输出**：当前 period 的活跃 restaurant index 更新。

### 场景 S9 — F2 行程导出
- **触发**：用户点 greeting block 右侧 `导出 / Download` outline pill。
- **输入**：当前 `TripPlanRender` 全量数据。
- **工作流**：纯前端格式化（生成 markdown / PDF / image）；可选**包装 LLM 子调用**生成更友好的 narrative format（如 "DAY 1 早晨：从酒店出发去盖蒂中心，10:30 在 Urth Caffé 享用有机咖啡和早午餐..."）。
- **输出**：可下载文件（md / pdf / png）。

### 场景 S10 — F2 内对话精化（替换某餐）
- **触发**：用户在 F2 input bar 输入（如"把第二天午餐换成素食"）。
- **输入**：`user_text` + 当前 `TripPlanRender` + `user_ctx`。
- **LLM 工作流**：
  1. Intent Extraction 识别为 "modify_trip" 子意图（`day=2, period=lunch, constraint=vegetarian`）。
  2. **新 tool** `modify_trip_slot(trip, day, period, new_constraint)` —— 仅对 (day=2, lunch) 重新 call recommend_restaurants with `dietary=["vegetarian"]`，保留 activity 不变；同时检查与 day=2 dinner 和 day=1/3 lunch 的 cuisine 多样性约束。
  3. Response Synthesis 生成短确认文字 + patch 后的 TripPlanRender。
- **输出**：patched `TripPlanRender`（仅 day=2 lunch 的 3 candidates 更换） + reply_text。

---

## 7. 给 §3.3（推荐模型 Spec）的更新点

### 新增/补充
1. **`activity` 文本作为 ranking context 的一种**——需要在特征工程中新增 `activity_embedding`（用 LLM 或 sentence-transformer 把 activity 文本嵌入为向量），作为 user × item 交互的 context feature（H4/H5 系列假设的 superset）。
2. **每段返回 top-3 而非 top-1**——recommender 默认 top_k=10，但对 trip 场景，需要返回 **per-period top-3**（前 3 名都送上来，前端用户切换）。这意味着 ranking 需要有"head 多样性"——不能 3 个都是同 cuisine。新增 **MMR (Maximal Marginal Relevance)** 重排作为一个 stretch goal。
3. **Trip Planner 启发式层**——Day-level cuisine diversity 约束（同 trip 内同 cuisine 不超过 2 餐）；时段地理紧凑性（同 day 内三餐不超过区域中心半径 5 mi）；价位 distribution（避免一日全 $$$）。这些是规则约束，不是 ML，但在报告中作为 "post-processing layer" 提及。
4. **Period × Activity context features**——`period_id` (early=0, lunch=1, dinner=2) + `activity_emb` (768-dim 或 32-dim 降维) 加入 DeepFM 输入。

### 修订 §3.3.1 假设
- 补 H9：activity 文本与餐厅类型存在显著语义匹配（如"看完日落"语义靠近 seafood / sunset bar），verifies via cosine similarity between activity_emb and category_emb。
- 修订 H4/H5：trip context features 不只是 day_of_trip + region_cluster_id，还包括 activity_emb 和 period_id。

### 修订 §3.3.3 特征工程
- 新增 3 个特征到 Context group：`period_id` (categorical 3) / `activity_emb` (numeric vector 32) / `prior_meals_cuisines` (multi-hot of cuisines already chosen this trip)。
- 总特征数从 23 → 26。

---

## 8. 给 §3.4（评测系统）的更新点

### 新增评测维度
| 维度 | 公式 | 目标 | 用途 |
|---|---|---|---|
| **Trip diversity** | 1 - Σ(同 cuisine 餐数 / 总餐数)² | ≥ 0.7（HHI 倒数视角） | 衡量跨日跨段 cuisine 多样性 |
| **Geographic compactness** | 平均 day-level 三餐之间 pairwise 距离 | < 3 mi (LA 场景) | 同日紧凑度 |
| **Activity-Restaurant semantic match** | cos(activity_emb, restaurant_category_emb) per period | ≥ 0.4 | 活动与餐饮的语义对齐（H9） |
| **Per-period candidate diversity** | per-period top-3 内 cuisine 唯一数 / 3 | ≥ 0.66 (avg 至少 2 unique) | 段内候选多样性，确保 ‹ › 切换有意义 |

### 新增评测样例（trip 场景）
- C9：3-day LA trip，全程素食 → 期望每段候选都符合 dietary，且 cuisine spread 不退化。
- C10：F2 内 modify_trip "把第二天午餐换成素食" → 仅 (day2, lunch) 的 3 候选更换，其他不变。
- C11：F1.1 ‹ › 切换连贯性 → counter pill 数字与 list index 同步无 off-by-one。
- C12：F2 export → 导出 markdown 字段完整（cuisine / address / time / reason chip 全保留）。

### Agent 层评测增项
| 子维度 | 度量方式 | 样本量 | 目标 |
|---|---|---|---|
| Itinerary parsing 准确率 | 抽取 destination / days / regions 的 F1 | 30 utterance | ≥ 0.85 |
| Activity 文案合理性 | 人工 5-point Likert (与 activity 真实可达性 / 时间合理性 / 与下一活动接续性) | 27 个 activity (3 days × 3 periods × 3 candidates) → 抽样 9 个 | mean ≥ 4.0 / 5 |
| modify_trip slot 局部修改正确性 | 仅修改目标 slot，其他不变；binary check | 10 个 modify case | 100% |

---

<!-- audit done · 2026-05-04 · 给 §3.x v2 Sib 团队用 -->
