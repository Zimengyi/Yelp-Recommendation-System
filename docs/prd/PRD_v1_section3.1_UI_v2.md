### §3.1 User Interaction & Design

> [!info] 📐 本节定位
>
> §3.1 覆盖 Taste hunter 的全部前端交互规格。三个屏幕（F1 Chat Home / F1.1 Restaurant Detail Overlay / F2 Trip Plan）均已通过 Figma Make 高保真原型落地，设计源文件见 [Figma 设计稿](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx/Draw-Based-on-Instructions)。本节每个子章遵循「视觉范例表 → 字段大表 → 决策 callout → 风险 callout」四件套结构（参照 Elfen PRD 标准模板 §3.4.1）。
>
> 重要边界：UI 在 ML2 rubric 的 8 项评分中不单独计分；其存在目的是为推荐模型提供端到端可演示的上下文，并为 EDA / future work 段提供数据流锚点。精力分配目标：模型 70% / Agent 20% / 前端 10%。

> [!note] 🔄 v2 更新说明 — 2026-05-04
>
> **本节为 v2 版本，与 Figma Make 原型实现严格对齐。** F1.1 和 F2 两个屏幕相较 v1 前瞻规格有重大修订：
>
> - **F1.1 Restaurant Detail Overlay**：形态从全屏 modal 改为 bottom sheet modal（95% 屏高，顶部圆角 20pt，黑色 40% 遮罩）；Hero photo 高度从 240pt 改为 280pt；侧边浮动 prev/next 箭头方案完全废弃，改为底部中央 nav bar（`‹` + `2 of 3` 计数 pill + `›`，距 sheet 底部 32pt）。
> - **F2 Trip Plan**：结构从多日纵向堆叠改为 tab 切换式（`[DAY 1] [DAY 2] [DAY 3]` 胶囊 tabs）；每日每段增加 activity 描述行（Inter Regular 13pt `#4D4D4D`）；每段含 3 个候选餐厅（`‹ ›` 切换 + indicator dots）；左轨时间标签（vertical-rl）废弃；per-day Open route / Copy pills 废弃；greeting block 新增 Export outline pill。
> - **F1 Chat Home**：细节补充两处 implementation TODO warning callout（chevron 展开数据源 + send button 状态）。
> - **RestaurantCard 组件**：`time` 字段保留但标注 deprecated，F2 v2 不使用。
> - **⚠️ F2 Meal Card 字段 ID 重新编号（Sib 间协调注意）**：v1 中 `F2-MC-01`（左轨时间标签行）已在 v2 中删除；原 `F2-MC-02`（photo）至 `F2-MC-06`（rating）顺移为 v2 中的 `F2-MC-01` 至 `F2-MC-05`。其他 Sib（§3.2 / §3.3 / §3.4）如有引用 `F2-MC-XX` 字段 ID，请注意编号向前偏移一位。

---

#### §3.1.0 信息架构

Taste hunter 共三个顶层屏幕，对应两种用户路径。**F1 Chat Home** 是应用入口，也是用户最长时间停留的主视图：LLM 输出（欢迎词 + 推荐卡片列表）直接渲染在页面背景上，无气泡容器，仿 Claude.ai mobile 排版；用户的自然语言输入通过底部固定输入栏发送，agent 循环在同一屏内渲染新结果。**F1.1 Restaurant Detail Overlay** 是 F1 的次级视图，由点击任意餐厅卡片触发，以 **bottom sheet modal** 形态向上弹出（占屏幕 95% 高度，顶部圆角 20pt，背后黑色 40% 遮罩）；用户可在 sheet 内通过底部中央 nav bar（`‹` / 计数 pill / `›`）横向切换相邻餐厅，不退出 sheet。**F2 Trip Plan** 是第二个一级功能，通过 F1 快捷操作区的"Trip Planner" pill 进入（pill 点击预填输入框内容 `Plan my trip…` 并 focus）；同一输入栏 + 同一 agent 循环，但 LLM 输出替换为**三日 tab 切换式**行程视图，每个 tab 内渲染三段（早晨 / 中午 / 晚上），每段含 activity 描述 + 3 候选餐厅卡片（可 `‹ ›` 循环切换）。

屏幕关系如下（ASCII frame）：

```
┌─────────────────────────────────────┐
│  F1 — Chat Home (入口 / 主视图)       │
│                                     │
│  [卡片1] [卡片2] [卡片3]              │
│  [chevron-down → 展开到 top-10]      │
│                                     │
│  底部快捷区: [✈ Trip Planner pill]   │──────→  F2 Trip Plan
│  底部输入栏: [想吃辣? ...]  [Send ↑]  │
└──────────────┬──────────────────────┘
               │ tap 任意卡片
               ▼ (bottom sheet slide-up, 95% 高, 顶部圆角 20pt)
┌─────────────────────────────────────┐
│  F1.1 — Restaurant Detail Overlay   │
│         (bottom sheet modal)        │
│  [Hero Photo 280pt]  [✕ close]      │
│  Playfair Display 餐厅名              │
│  [Directions] [Call] [Website]      │
│  ┌─────── Content Panel ──────────┐ │
│  │ AI Overview / Review / menu    │ │
│  └────────────────────────────────┘ │
│     ‹   [  2 of 3  ]   ›           │
│     ↑ bottom-center nav, 底部 32pt  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  F2 — Trip Plan                     │
│                                     │
│  "Philadelphia · 3 days · 9 meals"    [导出]   │
│  [DAY 1] [DAY 2] [DAY 3]  ← tabs   │
│                                     │
│  早晨 (period title)                 │
│  参观费城美术馆... (activity desc)      │
│  ‹ [RestaurantCard] ›  • ◦ ◦       │
│                                     │
│  中午 / 晚上 同结构                    │
│                                     │
│  底部输入栏: [...]  [Send ↑]          │
└─────────────────────────────────────┘
```

> [!tip] 设计基准线
>
> - **Chat 布局**：对标 Claude.ai mobile — assistant 文本自由流布局，无气泡。
> - **餐厅详情页**：对标 Google Maps place detail — hero photo + action pill row + 灰色内容面板分节；底部 nav `‹ [N of M] ›` 对标 Google Maps place detail 轮播模式。
> - **编辑感 serif 标题**：对标 Resy / Eater — Playfair Display 区分餐厅名与 UI 无衬线字体。
> - **暖色调 top bar**：对标 La Bonne Femme app / Wes-Anderson 调色盘 — `peach.500 = #F5DCA6`。
> - **Trip Plan tab 切换**：对标主流旅行类 app（TripAdvisor / Airbnb 行程）的 day-tab 模式，避免多日纵向堆叠造成的无限滚动问题。

##### 设计系统 — Color Tokens

所有色彩 token 以 Figma Variables 形式导出，下表为完整清单。实装时统一引用 token name，禁止直接硬编码 hex 值。

| Token Name | Hex 值 | 用途说明 |
|---|---|---|
| `peach.500` | `#F5DCA6` | Top bar 背景色（全三屏共享） |
| `bg.canvas` | `#FFFFFF` | 页面背景（F1 / F2 对话区） |
| `bg.card` | `#FFFFFF` | 餐厅卡片表面 |
| `bg.panel` | `#EBEBEB` | F1.1 内容面板背景（AI Overview / Review / menu 区）；F2 day-tab 非活跃背景 |
| `bg.input` | `#F2F2F2` | 输入框填充色 |
| `bg.quick` | `#EBEBEB` | Quick action pill 背景 |
| `text.primary` | `#1A1A1A` | 主要文字（标题、卡片名、按钮文字）；F2 active day-tab 文字；F2 period title；indicator dot active |
| `text.secondary` | `#737373` | 次要文字（meta 行、评分、类目） |
| `text.tertiary` | `#8C8C8C` | 第三级文字（placeholder、归因条、caption） |
| `text.body` | `#4D4D4D` | 正文描述（卡片 tagline、AI Overview body、review quote；**F2 activity 描述行**） |
| `border.light` | `#C7C7C7` | 轻描边（Call / Website pill outline；F1.1 底部 nav 圆按钮描边；F2 per-period nav 圆按钮描边；Export pill 描边） |
| `border.dark` | `#222222` | 重描边（close X icon） |
| `divider` | `#D6D6D6` | F1.1 内容面板三节之间的分隔线（1pt 全宽）；F2 indicator dot inactive |
| `chip.bg` | `#F0F2FF` | Reason chip 背景（柔和蓝紫） |
| `chip.text` | `#3349B3` | Reason chip 文字（深蓝，与 chip.bg 对比度 ≥ 4.5:1） |
| `primary.fill` | `#1A1A1A` | 主要 CTA 按钮填充（Directions pill，Send button，F2 active day-tab 背景） |
| `primary.text` | `#FFFFFF` | 主要 CTA 按钮文字（与 primary.fill 搭配；F2 active day-tab 文字） |
| `photo.placeholder` | `#B8A89E` | F1.1 Hero photo 占位色（暖棕，仿真实餐厅照片色调） |
| `card.thumb.placeholder` | `#DCDDE8` | F1 / F2 卡片缩略图占位色（冷灰蓝） |
| `sheet.backdrop` | `rgba(0,0,0,0.40)` | F1.1 bottom sheet 背后遮罩（40% 黑色，非纯黑） |
| `shadow.card` | `0 2 12 rgba(0,0,0,0.08)` | 卡片投影（低海拔，轻盈） |
| `shadow.float` | `0 2 8 rgba(0,0,0,0.12)` | 浮动元素投影（F1.1 底部 nav 圆按钮；F2 per-period nav 圆按钮；F1.1 counter pill） |

##### 设计系统 — Typography Scale

| 级别 | 字体 | 字重 | 尺寸 | 用途 |
|---|---|---|---|---|
| Display / Restaurant Name | Playfair Display | Bold | 22pt | F1.1 标题行餐厅名（仅此一处）；Fallback: PT Serif Bold → Times New Roman Bold |
| H1 Chat Heading | Inter | Bold | 22pt | F1 / F2 对话标题（Greeting block H1） |
| App Name | Inter | Semi Bold | 16pt | Top bar "Taste hunter" |
| Period / Section Header | Inter | Semi Bold | 15pt | F2 每段标题（早晨 / 中午 / 晚上）；F1 Card Title |
| Section Label (content panel) | Inter | Semi Bold | 13pt | F1.1 内容面板节标题（AI Overview / Review / menu） |
| Day Tab Label | Inter | Medium | 13pt | F2 day tab 文字（active 白色 / inactive `#1A1A1A`） |
| Pill Label | Inter | Medium | 14pt | Action pill 文字（Directions / Call / Website / input placeholder） |
| Export Pill Label | Inter | Medium | 13pt | F2 "导出" pill 文字 |
| Bottom Nav Counter | Inter | Medium | 15pt | F1.1 底部 counter pill "N of M" 文字 |
| Reason Chip | Inter | Medium | 11pt | Reason chip 文本 |
| Activity Description | Inter | Regular | 13pt | F2 每段活动描述（period title 与卡片之间） |
| Meta / Subtitle | Inter | Regular | 13pt | 副标题、meta 行、评分行 |
| Body | Inter | Regular | 12pt | 卡片 tagline、AI Overview 正文、review quote、menu items |
| Caption / Attribution | Inter | Regular | 11pt | Yelp 归因条、photo counter 数字 |

##### 设计系统 — Spacing Rhythm

| 区域 | 规格值 | 说明 |
|---|---|---|
| 页面水平 padding | 20pt | 全三屏通用（Top bar 内容 / 对话区 / input bar 左右） |
| Top bar 顶部 safe area | 50pt | iPhone 14 Pro notch 安全区 |
| Top bar 底部 padding | 14pt | top bar 内容与内容区分隔 |
| 节间垂直间距 | 14pt | 各功能区块之间的标准间距 |
| 卡片内 padding | 12pt | 卡片内 horizontal + vertical padding |
| 卡片间距 | 10pt | 相邻卡片之间的垂直 gap |
| 卡片内列间距 | 12pt | 缩略图与右侧文字列之间 |
| 卡片内行间距 | 4pt | 卡片右列各行之间的 gap |
| Input bar 底部 safe area | 28pt | iPhone Home Indicator 安全区（底部输入栏） |
| Action pill 圆角 | 22pt | Directions / Call / Website / Send button（全圆角 pill 感） |
| Reason chip 圆角 | 6pt | 卡片 reason chip（轻微圆角，更精致） |
| Quick action pill 圆角 | 18pt | Trip Planner pill（接近全圆） |
| **F1.1 Bottom sheet 高度** | **95% viewport** | Bottom sheet modal 占屏幕高度 95%，顶部圆角 20pt |
| **F1.1 Hero photo 高度** | **280pt** | 较 v1（240pt）增加 40pt，提供更强视觉冲击 |
| **F1.1 Bottom nav 圆按钮** | **48×48pt** | `‹` / `›` 圆形按钮（w-12 h-12），白色填充 + `border.light` 描边 + `shadow.float` |
| **F1.1 Bottom nav 距底部** | **32pt** | 底部中央 nav bar 整体距 sheet 底部 32pt（`bottom-8`） |
| **F2 Day tab 圆角** | **full** | 胶囊 tab（capsule 全圆），active = `primary.fill` 黑底白字，inactive = `bg.panel` 灰底黑字 |
| **F2 Per-period nav 按钮** | **28×28pt** | per-period `‹ ›` 圆形按钮，绝对定位于卡片边缘 -8pt（`-left-2 / -right-2`），overlap 卡片 8pt |
| **F2 Indicator dot 尺寸** | **1.5×1.5pt** | 每段候选指示点，active = `#1A1A1A`，inactive = `#D6D6D6`，居中排列于卡片下方 |

##### 设计系统 — Iconography

所有功能性图标使用 **lucide-react** 风格 line-art SVG，1.5–2pt stroke，rounded ends，viewBox 24×24。

| 图标名 | Lucide ID | 尺寸 & 颜色 | 出现位置 | 语义 |
|---|---|---|---|---|
| `menu` | `Menu` | 20×2pt 三横线，4pt 间距，`#1A1A1A` | F1/F1.1/F2 Top bar 左侧 | 侧边导航（预留） |
| `user-circle` | `UserCircle` | 28×28pt，1.8pt stroke，`#1A1A1A` | F1/F1.1/F2 Top bar 右侧 | 用户设置（预留） |
| `x` | `X` | 16pt，`border.dark = #222222` | F1.1 Hero photo 左上角 close button 内 | 关闭 / dismiss sheet |
| `camera` | `Camera` | 13pt，2pt stroke，白色 | F1.1 Hero photo 右下角 photo counter 内 | 图片计数提示 |
| `copy` | `Copy` | 16pt，`#666666`（F1.1 title）/ 18pt，`#8A8A8A`（F1 message action） | F1.1 标题行复制图标 + F1 消息操作第 1 icon | 复制文本到剪贴板 |
| `thumbs-up` | `ThumbsUp` | 18pt，`#8A8A8A` | F1 消息操作第 2 icon | 正向反馈 |
| `thumbs-down` | `ThumbsDown` | 18pt，`#8A8A8A` | F1 消息操作第 3 icon | 负向反馈 |
| `refresh-ccw` | `RefreshCcw` | 18pt，`#8A8A8A` | F1 消息操作第 4 icon | 刷新推荐 |
| `plane` | `Plane` | 14pt，`#1A1A1A`（F1 QA pill） | F1 Trip Planner pill leading icon | 行程 / 旅行语义 |
| `star` | `Star`（filled，无描边） | 12pt，`#1A1A1A`（F1.1 meta）/ 11pt，`#444444`（F1.1 review header） | F1.1 meta 行 inline star + F1.1 Review 节标题旁 mini star | 评分星标 |
| `chevron-down` | `ChevronDown` | 22×22pt，`#9AA0A6` | F1 第 3 卡片下方展开触发 | 展开更多卡片（旋转 180° 变为 chevron-up） |
| `chevron-left` | `ChevronLeft` | 18pt，`#222222`（F1.1 bottom nav）/ 14pt，`#222222`（F2 per-period nav） | F1.1 底部中央 nav 左按钮 + F2 每段 per-period nav 左按钮 | 切换至前一餐厅 / 前一候选 |
| `chevron-right` | `ChevronRight` | 18pt，`#222222`（F1.1 bottom nav）/ 14pt，`#222222`（F2 per-period nav） | F1.1 底部中央 nav 右按钮 + F2 每段 per-period nav 右按钮 | 切换至后一餐厅 / 后一候选 |
| `chevron-up` | `ChevronUp` | 18pt，2.5pt stroke，白色 | F1/F2 Send button 内 | 发送消息 |
| `download` | `Download` | 14pt，`#1A1A1A` | F2 greeting block 右侧 Export pill leading icon | 导出行程文件 |

> [!example] Iconography 使用示例
>
> F1 消息操作图标行（左→右）：`copy` (18pt, #8A8A8A) · `thumbs-up` (18pt) · `thumbs-down` (18pt) · `refresh-ccw` (18pt)，4 个图标水平排列，18pt 间距。**不使用 emoji 替代**（如 ❤️ 代替 thumbs-up），不使用平台内置符号字体（SF Symbols / Material Icons）。

---

#### §3.1.1 F1 — Chat Home

##### 视觉范例表

| 视觉范例 (Mode) | 视觉系统 (色彩 token) | Mockup |
|---|---|---|
| Light — 默认态（3 卡片，未展开） | Top bar: `peach.500 = #F5DCA6` · Page bg: `bg.canvas = #FFFFFF` · Card: `bg.card = #FFFFFF` + `shadow.card = 0 2 12 rgba(0,0,0,0.08)` · Reason chip: `chip.bg = #F0F2FF` / `chip.text = #3349B3` · Input: `bg.input = #F2F2F2` | [F1 Frame →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| Light — 展开态（top-10 卡片，chevron 旋转 180°） | 同上；chevron-up icon 颜色 `#9AA0A6` | [F1 Expanded →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| 输入激活态（Send button enabled） | Input outline `border.light = #C7C7C7`（focus ring）· Send button fill `primary.fill = #1A1A1A`（opacity 100%） | [F1 Input Active →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |

##### 字段大表

| 功能模块 | ID | 功能名称 | 功能描述 | 命名候选 | 数据来源 |
|---|---|---|---|---|---|
| **Top Bar** | F1-TB-01 | 汉堡菜单图标 | 左上角 3 横线图标，20×2pt，4pt 间距，黑色。点击（当前 demo 不实装）预留侧边导航扩展点。 | Hamburger / NavMenu / MenuIcon | 前端常量 |
| **Top Bar** | F1-TB-02 | 应用标题 | 居中 "Taste hunter"，Inter Semi Bold 16pt，`text.primary = #1A1A1A`。与 logo 概念合一，无副标题。 | AppTitle / BrandName | 前端常量 |
| **Top Bar** | F1-TB-03 | 用户头像图标 | 右上角 user-circle 轮廓图标，28×28pt，1.8pt stroke，黑色。点击（当前 demo 不实装）预留用户偏好设置入口。 | UserAvatar / UserCircle / ProfileIcon | 前端常量 |
| **Greeting Block** | F1-GB-01 | 对话标题 H1 | 主标题，Inter Bold 22pt，`text.primary`。内容由 LLM 依据当前时段 + 城市生成，如 "Wed brunch in Philly ☕"。Emoji 仅作装饰，不作功能按钮。 | GreetingTitle / ChatHeading / H1 | LLM 生成 |
| **Greeting Block** | F1-GB-02 | 副标题说明 | Inter Regular 13pt，`text.secondary = #737373`。格式 `{时间} · {N} picks based on your location & this week's trends`。N = 本次推荐总数（默认 3，展开后 10）。 | GreetingSubtitle / ContextLine / SubHeading | LLM 生成 |
| **Card Body** | F1-CD-01 | 餐厅缩略图 | 80×96pt，10pt corner radius，左侧定位。占位色 `card.thumb.placeholder = #DCDDE8`；生产态从 Yelp `photos.json` 拉取 storefront 图。 | CardPhoto / RestaurantThumb / PhotoPlaceholder | Yelp 字段 (`photos`) |
| **Card Body** | F1-CD-02 | 餐厅名称 | Inter Semi Bold 15pt，`text.primary`。点击卡片整体触发 F1.1 Overlay；名称本身不单独可点。 | CardTitle / RestaurantName | Yelp 字段 (`name`) |
| **Card Body** | F1-CD-03 | Meta 信息行 | Inter Regular 11pt，`text.secondary`。格式 `★ {rating} ({review_count}) · {category} · {price_range}`。★ 使用 Unicode 字符，非单独 SVG 图标（inline meta 专用规则）。 | CardMeta / RatingLine / MetaRow | Yelp 字段 (`rating`, `review_count`, `categories`, `price`) |
| **Card Body** | F1-CD-04 | 一句话描述 | Inter Regular 12pt，`text.body = #4D4D4D`，1 行截断。由 LLM 结合 top-review 关键词生成，突出必点菜或氛围亮点。 | CardDesc / Tagline / OneLiner | LLM 生成 |
| **Card Body** | F1-CD-05 | Reason chip | 圆角 pill，`chip.bg = #F0F2FF`，6pt radius，8pt 垂直 / 3pt 水平 padding，`chip.text = #3349B3`，Inter Medium 11pt。内容 = DeepFM ranking score 最高的推荐理由，可含 emoji 装饰（如 "🌅 上午 10 点 · 1.1 mi · 周榜 Top 3"）。冷启动降级策略见下方风险 callout。 | ReasonChip / WhyChip / RankingReason | LLM 生成（基于 DeepFM 特征权重） |
| **Expand Chevron** | F1-EX-01 | 展开箭头 | 第 3 张卡片下方居中，chevron-down，22×22pt，`#9AA0A6`。点击展开至 top-10 卡片；同时图标旋转 180° 变为 chevron-up。收起时反向动作。 | ExpandChevron / ShowMore / CollapseToggle | 前端常量 |
| **Message Actions** | F1-MA-01 | 消息操作图标组 | 4 个 18pt line-art 图标，左对齐，18pt 横向间距，4pt 垂直 padding，颜色 `#8A8A8A`。顺序：`copy`（复制推荐文本）/ `thumbs-up`（正向反馈）/ `thumbs-down`（负向反馈）/ `refresh-ccw`（刷新推荐）。反馈信号可在后续迭代接入在线学习。 | MessageActions / FeedbackRow / ReactionIcons | 前端常量 |
| **Message Actions** | F1-MA-02 | 复制图标 | `copy`（overlapping squares），18pt，`#8A8A8A`。点击将当前推荐列表文本写入剪贴板。 | CopyIcon / CopyAction | 前端常量 |
| **Message Actions** | F1-MA-03 | 点赞图标 | `thumbs-up`，18pt，`#8A8A8A`。点击记录正向隐式反馈（可用于离线重训特征）。 | ThumbsUp / LikeAction | 前端常量 |
| **Message Actions** | F1-MA-04 | 踩图标 | `thumbs-down`，18pt，`#8A8A8A`。点击记录负向隐式反馈 + 触发轻量过滤（下次排除同类目）。 | ThumbsDown / DislikeAction | 前端常量 |
| **Message Actions** | F1-MA-05 | 刷新图标 | `refresh-ccw`，18pt，`#8A8A8A`。点击重新调用 DeepFM 给出新排序（same context, resample top-k）。 | RefreshIcon / RerollAction | 前端常量 |
| **Quick Action Bar** | F1-QA-01 | Trip Planner pill | 左对齐 pill，`bg.quick = #EBEBEB`，18pt radius，8pt 垂直 / 14pt 水平 padding。leading `plane` icon（14pt，黑色）+ "Trip Planner" 标签，Inter Medium 12pt。点击预填输入框内容为 `Plan my trip…` 并 focus。F2 视图内此 pill 隐藏（已在该视图）。 | TripPlannerPill / QuickAction / TripCTA | 前端常量 |
| **Input Bar** | F1-IB-01 | 文本输入框 | `bg.input = #F2F2F2`，22pt corner radius，11pt 垂直 / 16pt 水平 padding，FILL 剩余宽度。Placeholder "想吃辣？人均 30 以下？说说看…"，Inter Regular 14pt，`text.tertiary = #8C8C8C`。 | InputField / ChatInput / MessageBox | 前端常量 |
| **Input Bar** | F1-IB-02 | 发送按钮 | 40×40pt 黑色圆形按钮，白色 chevron-up 图标（18pt，2.5pt stroke）。enabled（`opacity: 1`）当且仅当输入框字符数 ≥ 1；disabled 时 `opacity: 0.30`。 | SendButton / SubmitBtn / UpArrowBtn | 前端常量 |

##### F1 样例卡片内容（Figma 中渲染的固定演示数据）

以下三条为 Figma 原型中使用的固定样例，data-source = Yelp Open Dataset（rating + review_count + categories + price 字段实际存在），name 和 description 为编辑后的演示值，reason chip 为 LLM 生成的演示字符串。

| 序号 | 餐厅名 | Meta 信息 | 一句话描述 | Reason chip |
|---|---|---|---|---|
| 1 | Moonlark's Dinette | ★ 4.8 (1,038) · American · Brunch · $$ | Downtown 高分早午餐，炸鸡华夫饼必点 | 🌅 上午 10 点 · 1.1 mi · 周榜 Top 3 |
| 2 | Cafe Corina | ★ 4.6 (421) · Coffee · Breakfast · $$ | 本地人推荐的 latte + avocado toast 组合 | 📍 距你 0.8 mi · 周三上午营业中 |
| 3 | Marlowe's Kitchen | ★ 4.5 (892) · Bakery · Pastry · $ | 现烤可颂 + 手冲，安静角落适合一个人 | 🍪 与你常去的店风格相似 |

> [!example] Reason chip 生成逻辑说明
>
> 三张卡片的 reason chip 分别代表三种不同的推荐逻辑层次：
> - **卡片 1**（Moonlark）：基于时段 context feature（上午 10 点）+ 地理距离（1.1 mi）+ 周榜 popularity signal —— 不依赖用户历史。
> - **卡片 2**（Cafe Corina）：基于地理 context（0.8 mi）+ 营业时间约束（Yelp `hours` 字段）—— 不依赖用户历史。
> - **卡片 3**（Marlowe's）：基于用户历史偏好相似性（需要用户 embedding，冷启动降级为 Tier-2 或隐藏）。
>
> 这三种层次对应 DeepFM 中 context feature 权重 → popularity feature 权重 → user embedding 权重的梯度，实现"有历史数据个性化、无历史数据也好用"的降级链。

> [!success] ✅ 决策：默认 3 卡片 + chevron 展开到 top-10
>
> **结论**：F1 初始渲染 3 张餐厅卡片；用户点击 chevron-down 后展开至最多 10 张。
>
> **理由**：
> - **信号密度 vs. 可扫描性**：3 张卡片在 390pt 宽、844pt 高的 iPhone 14 Pro 视口内可以全部呈现，无需滚动，用户一眼获得足够对比信息。展开到 10 是 Top-K 推荐的完整输出，满足深度探索需求但不在默认态增加认知负载。
> - **召回 → 精排分层**：Two-Tower 召回层输出 Top-100，DeepFM 精排后取 Top-10 渲染到前端；3 是"高信心推荐"的精选切面，10 是精排全量。
> - **对标参考**：Claude.ai mobile 首屏同样限制 assistant 输出高度，避免首屏全被内容占满。

> [!warning] ⚠️ Implementation TODO — Chevron 展开数据源
>
> **当前状态**：Figma Make 原型中，chevron 点击逻辑已连接到 `expanded` state（icon 旋转 + 展开/收起动画），但第 4-10 张卡片的**数据源尚未实装**——原型内 placeholder 逻辑不调用任何推荐接口，仅切换 icon。
>
> **待实装要求**：chevron 展开事件必须触发 `recommend_restaurants(user_ctx, intent, offset=3, top_k=7)` 调用，将返回的 7 张新卡片追加至 `cards[]` 数组（index 3-9），并在 offset 不足时（总数 < 4）隐藏 chevron。实装前 demo 演示以 3 张固定卡片为准。

> [!warning] ⚠️ Implementation TODO — Send Button 状态
>
> **当前状态**：Figma Make 原型中 Send button 总是显示黑色实心（`opacity: 1.0`），未实装 enabled / disabled 状态区分——不论输入框是否为空，按钮样式恒定。
>
> **PRD 规格保持不变**（`opacity: 0.30` when `input.trim().length === 0`，`opacity: 1.0` when ≥ 1 字符）。实装时在输入框 `onChange` 事件中联动 Send button 的 opacity 和 `pointer-events` 属性。

> [!warning] ⚠️ 风险：冷启动用户 Reason Chip 降级
>
> **问题**：新用户无历史行为数据，DeepFM 的用户侧 embedding 退化为均值向量，个性化 reason 无从生成。
>
> **降级策略**（按优先级）：
> 1. **Tier-1 降级**：Reason chip 改为基于地理 + 时段的通用理由，如 "📍 距你 0.8 mi · 周三上午营业中" —— context feature 不依赖用户 embedding。
> 2. **Tier-2 降级**：连地理信息也无（离线 demo 场景），chip 退回纯 popularity signal，如 "🔥 本周 Top 3 · 1,038 条评价"。
> 3. **Tier-3 降级**（最后防线）：chip 隐藏，卡片仅显示 meta 行，UI 不崩溃。
>
> 降级逻辑在 LLM agent 的 response-synthesis 步骤中判断（详见 §3.2）。

---

#### §3.1.2 F1.1 — Restaurant Detail Overlay

F1.1 由点击 F1 中任意餐厅卡片触发，以 **bottom sheet modal** 形态（占屏幕 95% 高度，顶部圆角 20pt，背后黑色 40% 遮罩）从屏幕底部向上弹出。用户可通过左上角 `✕` 关闭按钮或向下滑动手势退出到 F1；也可通过 **sheet 底部中央 nav bar**（`‹` 白色圆按钮 + 计数 pill `2 of 3` + `›` 白色圆按钮，整体居中，距 sheet 底部 32pt）在同一 sheet 内切换到相邻餐厅，不退出 modal。

内容分区从上至下：top bar（继承 F1 peach 背景）→ hero photo（**280pt** 高）→ 餐厅信息块 → 灰色内容面板（三节分区）→ 底部归因条 → 底部中央 nav bar（悬浮在归因条上方）。

##### 视觉范例表

| 视觉范例 (Mode) | 视觉系统 (色彩 token) | Mockup |
|---|---|---|
| Light — 详情默认态（AI Overview 展开） | Top bar: `peach.500` · Hero: `photo.placeholder = #B8A89E` · Info block: `bg.canvas = #FFFFFF` · Content panel: `bg.panel = #EBEBEB` · Action pills: Directions `primary.fill = #1A1A1A` / Call & Website `border.light = #C7C7C7` outline · Backdrop: `sheet.backdrop = rgba(0,0,0,0.40)` | [F1.1 Frame →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| Light — 底部 nav 可见态（中间餐厅，prev + next 均显示） | 底部中央：`‹` 48×48pt 白色圆 + `2 of 3` 白色 pill（Inter Medium 15pt，shadow.float）+ `›` 48×48pt 白色圆，整体 `bottom-8`（距底 32pt） | [F1.1 Nav →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| Light — 列表首位态（prev 按钮 opacity: 0.30，disabled） | `‹` 按钮 opacity 0.30（disabled）；`›` 按钮正常显示 | [F1.1 First →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |

##### 字段大表

| 功能模块 | ID | 功能名称 | 功能描述 | 命名候选 | 数据来源 |
|---|---|---|---|---|---|
| **Top Bar** | F1.1-TB-01 | 顶部栏（继承） | 与 F1 完全相同：peach.500 背景 + hamburger + "Taste hunter" + user-circle。Modal 覆盖时保留 top bar 视觉连贯性，不额外叠加导航元素。 | TopBar / StickyHeader | 前端常量 |
| **Hero Photo** | F1.1-HP-01 | 主图区域 | **280pt** 高，全出血宽（390pt），填充色 `photo.placeholder = #B8A89E`。生产态接 Yelp `photos` API 取餐厅门面照。 | HeroPhoto / CoverImage / RestaurantHero | Yelp 字段 (`photos`) |
| **Hero Photo** | F1.1-HP-02 | 关闭按钮 (✕) | 主图左上角，距边缘 14pt，32×32pt 白色实心圆 + line-art `x` icon（16pt，`border.dark = #222222`）。点击 dismiss sheet，返回 F1。 | CloseButton / DismissX / ExitOverlay | 前端常量 |
| **Hero Photo** | F1.1-HP-03 | 图片计数徽章 | 主图右下角，距边缘 14pt。pill 形：黑色 55% 透明背景，12pt radius，5pt 垂直 / 9pt 水平 padding。内含 white `camera` icon（13pt，2pt stroke）+ 空格 + 数字（如 "5"），Inter Medium 11pt 白色。表示该餐厅共有 N 张照片可翻阅（当前 demo 为静态常量）。 | PhotoCounter / CameraCountBadge / ImageCountPill | Yelp 字段 (`photos.length`) / 前端常量 (demo) |
| **Info Block** | F1.1-IB-01 | 餐厅名 + 区域 | **Playfair Display Bold 22pt**，`text.primary`。格式 `{name}   ({district})`（名字与括号之间 3 个空格，editorial 间距）。区域字段取 Yelp `location.city` 或 `neighborhood`。 | RestaurantTitle / DisplayName / SerifName | Yelp 字段 (`name`, `location`) |
| **Info Block** | F1.1-IB-02 | 复制图标 | 紧跟标题右侧，line-art `copy` icon（16pt，`#666666`）。点击将餐厅名称 + 地址写入剪贴板。 | CopyAddressIcon / ClipboardIcon | 前端常量 |
| **Info Block** | F1.1-IB-03 | Meta 行（评分 + 类目 + 价位） | 水平排列。左组：`{rating}` + inline filled black star SVG（12pt，无描边）+ `{review_count}  ·  {category}` —— Inter Regular 13pt，`text.secondary`。右侧 `{price_range}` 同规格。 | MetaRow / RatingCategory / RestaurantMeta | Yelp 字段 (`rating`, `review_count`, `categories`, `price`) |
| **Action Pills** | F1.1-AP-01 | Directions pill | 黑色填充（`primary.fill`），白色文字（`primary.text`），Inter Medium 14pt，22pt corner radius，11pt 垂直 / 22pt 水平 padding。文本 "Directions"。点击打开 Google Maps deeplink，传入 Yelp `coordinates`。 | DirectionsBtn / NavigateBtn | Yelp 字段 (`coordinates`) |
| **Action Pills** | F1.1-AP-02 | Call pill | 白色填充，`border.light` 1pt 描边，黑色文字，同尺寸规格。文本 "Call"。点击触发 `tel:` deeplink，传入 Yelp `phone`。 | CallBtn / PhoneBtn | Yelp 字段 (`phone`) |
| **Action Pills** | F1.1-AP-03 | Website pill | 白色填充，`border.light` 1pt 描边，黑色文字，同尺寸规格。文本 "Website"。点击打开 Yelp `url`。 | WebsiteBtn / UrlBtn | Yelp 字段 (`url`) |
| **Content Panel** | F1.1-CP-01 | AI Overview — 标题 | `bg.panel = #EBEBEB` 面板内第一节。Inter Semi Bold 13pt，`text.primary`。固定文本 "AI Overview"。 | AIOverviewHeader / SectionTitle | 前端常量 |
| **Content Panel** | F1.1-CP-02 | AI Overview — 正文 | Inter Regular 12pt，`text.body = #4D4D4D`。内容由 LLM 综合 Yelp top-review 关键词 + `categories` + `attributes` 生成，突出招牌菜、氛围、限时特供。**链接到 §3.2 LLM pipeline Step 3（Response Synthesis）**。 | AIOverviewBody / GeneratedSummary | LLM 生成 |
| **Content Panel** | F1.1-CP-03 | Review — 标题行 | "Review" Inter Semi Bold 13pt + " · " + filled mini star（11pt，`#444444`）+ `{rating}` Inter Regular 12pt，`text.secondary`。水平排列，6pt 间距。 | ReviewHeader / ReviewSectionTitle | Yelp 字段 (`rating`) |
| **Content Panel** | F1.1-CP-04 | Review — 引用文本 | Yelp top-review 原文截取（首句或最高票 quote），Inter Regular 12pt，`text.body`，带引号格式。 | ReviewQuote / TopReviewText | Yelp 字段 (`reviews[0].text`) |
| **Content Panel** | F1.1-CP-05 | Review — 归因 | "— Yelp top review"，Inter Regular 11pt，`text.tertiary = #8C8C8C`。 | ReviewAttribution / QuoteSource | 前端常量 |
| **Content Panel** | F1.1-CP-06 | menu — 标题 | 小写 "menu"（**严格小写，勿改为 Menu**），Inter Semi Bold 13pt。 | menuHeader / MenuSectionLabel | 前端常量 |
| **Content Panel** | F1.1-CP-07 | menu — 菜单文本 | 招牌菜 + 价格，格式 `{dish}  ${price}  ·  {dish}  ${price}  …`，Inter Regular 12pt，`text.body`。数据来源优先 Yelp `attributes.menu_url` 解析；demo 态为 LLM 生成的推断菜单。 | MenuItems / DishList | Yelp 字段 (`attributes`) / LLM 生成 (demo) |
| **Bottom Strip** | F1.1-BS-01 | 数据归因条 | 内容面板下方 8pt padding，左对齐单行：`Yelp Open Dataset · #b1u2 · 2026`，Inter Regular 11pt，`text.tertiary`。满足 Yelp 数据授权的学术用途归因要求。 | YelpAttribution / DataSourceLine | 前端常量 |
| **Bottom Nav** | F1.1-BN-01 | 底部 nav — prev 按钮 | **48×48pt** 白色圆形按钮（`border.light = #C7C7C7` 1pt 描边，`shadow.float = 0 2 8 rgba(0,0,0,0.12)`）。内含 `chevron-left` icon（18pt，`#222222`）。居中排列于 sheet 底部 nav bar 左侧，距底 32pt（`bottom-8`）。**边界处理**：当前餐厅 index = 0（列表首位）时，`opacity: 0.30`（disabled）。 | PrevButton / BottomNavPrev / BackChevron | 前端常量 |
| **Bottom Nav** | F1.1-BN-02 | 底部 nav — 计数 pill | 白色背景 pill，Inter Medium 15pt，`text.primary = #1A1A1A`，`shadow.float`。格式 `{current} of {total}`，如 "2 of 3"。位于 prev / next 按钮之间，水平居中。随翻页实时更新。 | CounterPill / NavIndicator / PageCounter | 前端常量（动态） |
| **Bottom Nav** | F1.1-BN-03 | 底部 nav — next 按钮 | **48×48pt** 白色圆形按钮，规格同 F1.1-BN-01（对称）。内含 `chevron-right` icon（18pt，`#222222`）。**边界处理**：当前 index = 总数 - 1（列表末位）时，`opacity: 0.30`（disabled）。 | NextButton / BottomNavNext / ForwardChevron | 前端常量 |

> [!success] ✅ 决策：底部中央 nav bar（vs. v1 侧边浮动箭头）
>
> **结论**：F1.1 prev/next 导航采用**底部中央 nav bar**（`‹` + `N of M` 计数 pill + `›`，水平居中，距 sheet 底部 32pt），取代 v1 前瞻规格中的侧边浮动箭头（`top: 540pt, left/right: 12pt`）。
>
> **理由**：
> - **可发现性**：底部中央 nav 更符合用户预期——将导航控件集中在拇指自然落区（屏幕底部区域），不需要用户"扫视"屏幕两侧边缘寻找隐藏箭头。
> - **计数 affordance**：底部中央布局天然容纳 `N of M` pill，向用户明确传达"还有多少家可翻阅"，侧边浮动方案无处放置计数文字。
> - **Google Maps 对标**：Google Maps place detail card 的多图 / 多结果导航采用相同的底部中央 nav 模式，用户认知成本接近零。
> - **Form factor 适配**：bottom sheet 形态（95% 高，rounded top）内，底部 32pt 区域不与任何内容信息重叠，nav bar 安置自然；v1 侧边方案的 `y=540pt` 仅在全屏 modal 下有意义，在 bottom sheet 中会叠加在内容面板正文上。

> [!success] ✅ 决策：Playfair Display Bold 用于餐厅名
>
> **结论**：餐厅名称（F1.1 标题行）使用 Playfair Display Bold 22pt，其余所有 UI 文字使用 Inter。
>
> **理由**：餐厅名是 F1.1 视图的第一视觉焦点，衬线字体 (editorial serif) 在大尺寸标题处提供视觉差异化，呼应 Resy / Eater 的高档感排版。Fallback 顺序：Playfair Display → PT Serif Bold → Times New Roman Bold。

> [!success] ✅ 决策：AI Overview 正文由 LLM 综合生成
>
> **结论**：AI Overview 区块的 body 文本不从 Yelp 数据库直接取，而是在 LLM agent response-synthesis 步骤中，以 top-3 Yelp reviews + `categories` + `attributes.good_for` 为输入，由 LLM 动态生成 1-2 句话的 editorial summary。
>
> **理由**：raw Yelp reviews 往往过长、语气不统一；AI Overview 的目标是"推荐 editorial"而非"评论聚合"，适合 LLM 的生成能力。生成逻辑详见 §3.2 LLM Pipeline。

##### F1.1 样例内容（Figma 渲染的固定演示数据 — Yamitsuki Ramen）

| 字段 | 演示值 | 对应 Yelp 字段 |
|---|---|---|
| 餐厅名 (Playfair Display) | `Yamitsuki Ramen   (Old City)` | `name` + `location.neighborhood` |
| 评分 | 4.7 ★ | `rating` |
| 评论数 | 571 | `review_count` |
| 类目 | Ramen restaurant | `categories[0].title` |
| 价位 | $ | `price` |
| AI Overview | 招牌 tonkotsu，汤底 12 小时熬制；本周「辣味噌限定」别错过。本地客比游客多，氛围 chill。 | LLM 生成（基于 reviews + attributes） |
| Top review 引用 | "Best ramen in Center City. The chashu melts." | `reviews[0].text`（截取首句） |
| menu 项目 | Tonkotsu $16 · Spicy Miso $17 · Veggie $15 · Gyoza $8 | LLM 推断 / `attributes.menu_url` |
| Photo counter | 5 | `photos.length`（demo 为常量） |
| Yelp 归因 | Yelp Open Dataset · #b1u2 · 2026 | 前端常量（学术用途归因） |
| Bottom nav counter | 2 of 3 | 前端 state（demo 固定，实装时动态） |

---

#### §3.1.3 F2 — Trip Plan

F2 与 F1 共用相同的页面 shell（peach top bar + 对话区 + 底部输入栏），区别在于 LLM 输出内容替换为**三日 tab 切换式**行程视图。进入 F2 后，对话区顶部出现 `[DAY 1] [DAY 2] [DAY 3]` 胶囊 tabs（active day = `primary.fill = #1A1A1A` 黑底白字，inactive = `bg.panel = #EBEBEB` 灰底黑字，Inter Medium 13pt）；仅 active day 的内容区域渲染，其他 day 不占用 DOM 高度。

每个 day 内渲染三段（早晨 / 中午 / 晚上）。每段结构从上至下：
1. **Period title**（如 "早晨"）— Inter Semi Bold 15pt，`text.primary`
2. **Activity description**（如 "参观费城美术馆，欣赏「Rocky」台阶和印象派藏品"）— Inter Regular 13pt，`text.body = #4D4D4D`，line-height 1.5
3. **RestaurantCard**（单张渲染，3 候选之一）+ 左右各一个 per-period nav 按钮（28×28pt 白色圆，`border.light` 描边，`shadow.float`，`-left-2 / -right-2` 绝对定位，overlap 卡片 8pt）；首候选时 `‹` 按钮 `opacity: 0.30`（disabled），末候选时 `›` 同理
4. **Indicator dots**（3 个 1.5×1.5pt 圆点，居中排列于卡片下方；active = `#1A1A1A`，inactive = `#D6D6D6`）

快捷操作区的 "Trip Planner" pill 在 F2 视图内隐藏（已在该功能内，无需再次引导）。

##### 视觉范例表

| 视觉范例 (Mode) | 视觉系统 (色彩 token) | Mockup |
|---|---|---|
| Light — F2 DAY 1 active 态（Tab 选中 + 三段完整） | Top bar: `peach.500` · Active tab: `primary.fill = #1A1A1A` 白字 · Inactive tabs: `bg.panel = #EBEBEB` `text.primary` · Period title: Inter Semi Bold 15pt · Activity desc: `text.body = #4D4D4D` · Card: 同 F1 · Per-period nav: 28×28pt 白圆 `border.light` · Indicator dots: active `#1A1A1A` / inactive `#D6D6D6` | [F2 Frame →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| Light — F2 Export pill 可见态（greeting block 右侧） | Export pill: 白色背景 outline pill，`border.light` 1pt 描边，`download` icon（14pt，`#1A1A1A`）+ "导出" Inter Medium 13pt；右对齐于 greeting block 同行 | [F2 Export →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |
| Light — Per-period candidate 切换态（候选 2 of 3，dots 中点 active） | 中间 indicator dot 为 `#1A1A1A`；左右两侧为 `#D6D6D6`；`‹` 按钮 opacity 1.0（enabled）；`›` 按钮 opacity 1.0（enabled） | [F2 Candidate →](https://www.figma.com/make/ssHwZecVKYUg8O5bUmwJnx) |

##### 字段大表

| 功能模块 | ID | 功能名称 | 功能描述 | 命名候选 | 数据来源 |
|---|---|---|---|---|---|
| **Greeting Block** | F2-GB-01 | Trip 标题 H1 | Inter Bold 22pt，`text.primary`。格式 `{city} · {N} days · {M} meals`，如 "Philadelphia · 3 days · 9 meals"。字段由 LLM 解析用户行程输入后生成。 | TripTitle / PlanHeading / H1 | LLM 生成 |
| **Greeting Block** | F2-GB-02 | 副标题说明 | Inter Regular 13pt，`text.secondary`。固定格式 "Generated from your itinerary · regional clustering + cuisine diversity"，传达系统约束逻辑。 | TripSubtitle / PlanSubheading | LLM 生成 / 前端常量 |
| **Greeting Block** | F2-EX-01 | Export 导出 pill | Greeting block 右侧，right-aligned。outline pill：白色背景，`border.light = #C7C7C7` 1pt 描边，8pt 垂直 / 12pt 水平 padding，18pt corner radius。内含 `download` icon（14pt，`#1A1A1A`，lucide）+ " 导出" Inter Medium 13pt `text.primary`。点击触发行程导出（markdown / PDF / PNG，格式 TBD）；demo 态为静态 no-op。 | ExportPill / DownloadBtn / ExportItinerary | 前端常量 |
| **Day Tabs** | F2-DT-01 | Day tab 组 | 顶部水平胶囊 tabs，3 个 tab 均分排列于对话区顶部（greeting block 下方 14pt 间距）。每个 tab：Inter Medium 13pt，full-radius capsule pill，8pt 垂直 / 16pt 水平 padding。**Active tab**：背景 `primary.fill = #1A1A1A`，文字 `primary.text = #FFFFFF`。**Inactive tab**：背景 `bg.panel = #EBEBEB`，文字 `text.primary = #1A1A1A`。Tab 文字格式 `DAY {N}`（如 "DAY 1" / "DAY 2" / "DAY 3"）。点击切换 active day，仅 active day 内容渲染，不做 DOM 保留。 | DayTabs / DaySelector / TabGroup | 前端常量（动态 state） |
| **Period Section** | F2-PS-01 | Period title（段落标题） | Inter Semi Bold 15pt，`text.primary = #1A1A1A`，左对齐，卡片上方。值为中文时段标签：`早晨` / `中午` / `晚上`（对应 morning / lunch / dinner）。不使用 v1 的 vertical-rl 左轨时间标签。 | PeriodTitle / MealPeriodLabel / SectionHeader | 前端常量（LLM 映射） |
| **Period Section** | F2-PS-02 | Activity description（活动描述） | Inter Regular 13pt，`text.body = #4D4D4D`，line-height 1.5，左对齐，position：period title 下方 6pt、卡片上方 10pt。内容由 LLM Activity Sequence Generator 子调用生成，描述该时段建议的旅行活动（如"参观费城美术馆，欣赏「Rocky」台阶和印象派藏品"），1-2 句话。约束：活动内容需与推荐餐厅的地理位置匹配（activity_emb × restaurant_emb 语义对齐）。 | ActivityDesc / PeriodActivity / ContextHint | LLM 生成 |
| **Period Section** | F2-PS-03 | Per-period nav — prev 按钮 | **28×28pt** 白色圆形按钮，`border.light = #C7C7C7` 1pt 描边，`shadow.float = 0 2 8 rgba(0,0,0,0.12)`。内含 `chevron-left` icon（14pt，`#222222`）。**绝对定位**于 RestaurantCard 左边缘向外 8pt（`-left-2`，overlap 卡片），垂直居中于卡片高度。**边界处理**：当前候选 index = 0 时，`opacity: 0.30`（disabled）。 | PerPeriodPrev / CandidatePrev / SlotLeftBtn | 前端常量 |
| **Period Section** | F2-PS-04 | Indicator dots（候选指示点） | 3 个 1.5×1.5pt 实心圆，水平居中排列于 RestaurantCard 下方 8pt，4pt 间距。active dot = `#1A1A1A`；inactive dot = `#D6D6D6`。随候选 index 切换实时更新。 | IndicatorDots / CandidateDots / SlotPager | 前端常量（动态 state） |
| **Period Section** | F2-PS-05 | Per-period nav — next 按钮 | **28×28pt** 白色圆形按钮，规格同 F2-PS-03（对称）。内含 `chevron-right` icon（14pt，`#222222`）。**绝对定位**于 RestaurantCard 右边缘向外 8pt（`-right-2`）。**边界处理**：当前候选 index = 2（共 3 候选，末位）时，`opacity: 0.30`（disabled）。 | PerPeriodNext / CandidateNext / SlotRightBtn | 前端常量 |
| **Meal Card** | F2-MC-01 | 餐厅缩略图 | 80×96pt，10pt corner radius，`card.thumb.placeholder = #DCDDE8`。继承 F1-CD-01 规格，数据源相同。 | MealCardPhoto / RestaurantThumb | Yelp 字段 (`photos`) |
| **Meal Card** | F2-MC-02 | 餐厅名称 | Inter Semi Bold 15pt，`text.primary`。继承 F1-CD-02。（F2 中卡片名称不使用 Playfair Display，保持 F1 卡片 schema 一致；Playfair 仅用于 F1.1 Overlay 标题行。） | MealCardTitle / RestaurantName | Yelp 字段 (`name`) |
| **Meal Card** | F2-MC-03 | Meta 信息行 | Inter Regular 11pt，`text.secondary`。格式 `★ {rating} ({review_count}) · {category} · {price_range}`，继承 F1-CD-03。 | MealCardMeta / RatingLine | Yelp 字段 (`rating`, `review_count`, `categories`, `price`) |
| **Meal Card** | F2-MC-04 | 一句话描述 | Inter Regular 12pt，`text.body`，继承 F1-CD-04。 | MealCardDesc / Tagline | LLM 生成 |
| **Meal Card** | F2-MC-05 | Reason chip（Trip 语境） | 格式与 F1-CD-05 相同（`chip.bg / chip.text`，Inter Medium 11pt），但内容切换为 Trip 约束理由，如 "距费城美术馆 0.3 mi" / "看完日落 5 min 步行"，体现地理约束和活动接续逻辑。 | TripReasonChip / ConstraintChip | LLM 生成 |
| **Input Bar** | F2-IB-01 | 文本输入框（F2） | 与 F1-IB-01 完全相同规格。用户可在 F2 视图内继续对话调整行程（如"把第二天午餐换成素食"）。 | InputField / ChatInput | 前端常量 |
| **Input Bar** | F2-IB-02 | 发送按钮（F2） | 与 F1-IB-02 完全相同规格，enabled 规则相同（输入字符 ≥ 1）。 | SendButton / SubmitBtn | 前端常量 |

> [!info] RestaurantCard `time` 字段说明（v2 deprecation note）
>
> 共享组件 `RestaurantCard.tsx` 接受可选 `time` prop，内部使用 `writing-mode: vertical-rl` 渲染为左轨时间标签。v1 PRD 规格在 F2 中使用了此字段（左轨 "上午 10 点 / 下午 1 点 / 晚上 7 点"）。
>
> **v2 起，F2 不传 `time` prop**：period 时段信息由 `F2-PS-01 Period title`（section header，卡片上方）承载；RestaurantCard 的 `time` 字段在 v2 prototype 中两屏均未使用。
>
> **字段保留原因**：为前向兼容性（schema flexibility），`time` 继续保留在 `RestaurantCard` props interface 中，标注为 **deprecated — kept for schema flexibility, not consumed by F2 v2**。未来如有"在卡片内直接显示时间"的需求，无需破坏 props schema。实装时**不传 `time` 给 F2 内任何 RestaurantCard 实例**。

##### F2 DAY 1 样例数据（Figma Make 中 LA 行程的硬编码数据片段）

DAY 1 硬编码以费城美术馆 / 圣莫尼卡 / 艺术区动线为基础。以下为 DAY 1 三段的代表性候选（3 候选中展示 index=0 即默认渲染的一家）：

| 段落 | Period title | Activity description | 代表餐厅（候选 1 of 3） | Reason chip |
|---|---|---|---|---|
| 早晨 | 早晨 | 参观费城美术馆，欣赏「Rocky」台阶和印象派藏品 | ★ 4.6 (892) · Café · $ | 距费城美术馆 0.3 mi |
| 中午 | 中午 | 漫步圣莫尼卡海边，享受海风和阳光 | ★ 4.5 (1,204) · Seafood · $$ | 距 Penn's Landing 5 min 步行 |
| 晚上 | 晚上 | 探索艺术区画廊，感受洛杉矶当代艺术氛围 | ★ 4.7 (571) · Ramen · $ | Old City 历史街区核心，步行可达 |

全 trip 数据规模：3 days × 3 periods × 3 candidates = **27 候选餐厅** + **9 段 activity 描述**。DAY 2 / DAY 3 结构相同，硬编码涵盖 费城天文馆 (Franklin Institute Planetarium) / Center City / Philadelphia Museum of Art / Walnut Street / Chinatown 动线，完整数据见 `TripPlan.tsx`。

> [!success] ✅ 决策：Tab 切换式 day selector（vs. v1 多日纵向堆叠）
>
> **结论**：F2 采用顶部胶囊 tab 切换式 day selector，每次仅渲染 active day 内容，取代 v1 的多日垂直堆叠方案。
>
> **理由**：
> - **无限滚动问题**：3 天 × 9 张餐厅卡片 = 27 张卡片（加 3 候选后 = 27 个候选组），垂直堆叠会导致对话区超长，用户难以定位到特定天。
> - **聚焦认知负载**：tab 切换使用户一次只看一天的行程，与旅行者"今天去哪、今天吃什么"的心智模型直接对应。
> - **对标主流产品**：TripAdvisor / Airbnb 行程视图均采用 day-tab 模式（非纵向滚动），已被充分验证。
> - **实装简洁**：前端只需 state 切换 active day index，无需虚拟列表或复杂滚动优化。

> [!success] ✅ 决策：每段 3 候选 + ‹ › 切换（vs. v1 每段固定 1 张）
>
> **结论**：每个时段提供 3 个候选餐厅，用户可通过 per-period `‹ ›` 按钮和 indicator dots 循环切换，默认渲染 index=0。
>
> **理由**：固定单张卡片剥夺了用户的选择权，但全量展示 3 张又会导致视觉混乱。`‹ ›` 模式在保持界面整洁的同时，将选择权交还用户——用户需要某段换一家时，点 `›` 即可，无需返回 F1 重新搜索。同时，3 候选数据由推荐器一次性生成（per-period top-3，MMR 多样化重排），前端切换为纯本地 state 操作，无追加网络请求。

> [!warning] ⚠️ 风险：Trip Plan 是 Stretch Goal
>
> Trip Plan 功能（F2）属于 stretch goal，交付优先级低于 F1 主推荐流。
>
> **风险场景**：若 DeepFM 模型在 Week 8 前未能稳定输出可用的 ranking 结果（如训练集特征工程超时、或离线评测指标未达基准线），Trip Plan 的地理 × 时段约束求解层将无可靠的排序分数可用，此时 F2 整个功能将移入 §6 Future Work，demo 仅演示 F1。
>
> **决策触发条件**：5/19 周一内部 checkpoint 时，若推荐模型 HR@10 < 0.05（随机基准），则 Trip Plan 推迟；若 HR@10 ≥ 0.05，则按计划实装。

---

#### §3.1.4 Cross-screen 交互模式

以下为跨屏通用的交互行为规范。实装时前端需严格遵守，避免不同屏幕间行为不一致。

| 交互模式 | 触发条件 | 行为描述 | 边界处理 |
|---|---|---|---|
| Bottom sheet 弹出（F1 → F1.1） | 用户点击 F1 中任意餐厅卡片 | F1.1 以 slide-up 动画（建议 300ms ease-out）从屏幕底部弹出，占屏幕 95% 高，顶部圆角 20pt，背后覆盖 `sheet.backdrop = rgba(0,0,0,0.40)` 遮罩。F1 内容保留在遮罩后（不销毁），以便关闭时原地恢复。 | 动画期间屏幕其他交互暂停（防误触）。 |
| Bottom sheet 关闭（F1.1 → F1） | 点击 F1.1 左上角 `✕` 按钮 / 向下滑动手势 | F1.1 以 slide-down 动画消失，遮罩淡出，恢复 F1 原始状态（滚动位置保留，高亮卡片短暂 pulse 提示）。 | 不重置 F1 的展开/收起状态；若已展开 10 张仍保持展开。 |
| 底部 nav 翻页（F1.1 兄弟切换） | 点击 F1.1 底部中央 `‹` 或 `›` 圆形按钮 | 在当前 sheet 内切换至 F1 卡片列表中的前一/后一餐厅，**不退出 sheet**。内容区域更新（hero photo / 餐厅信息 / content panel），top bar 与 sheet chrome 保持不动；counter pill 同步更新（如 "2 of 3" → "3 of 3"）。 | 列表首位时 `‹` 按钮 `opacity: 0.30`（disabled，不可点）；末位时 `›` 同理。切换时禁止超出边界。 |
| Chevron 展开/收起（F1） | 点击第 3 张卡片下方的 chevron-down 图标 | 展开：渲染第 4-10 张卡片，chevron 旋转 180°（变为 chevron-up）。收起：移除第 4-10 张卡片，chevron 旋转回 0°。 | 展开/收起带 150ms ease 动画，避免跳变。若总推荐数 < 4，chevron 隐藏。**注意**：当前 Figma Make 原型仅实装图标切换，第 4-10 卡数据源 TBD（见 §3.1.1 warning callout）。 |
| Day tab 切换（F2） | 点击 F2 顶部 `[DAY 1] / [DAY 2] / [DAY 3]` tab | active day index 切换，当前 day 内容（三段 + 候选卡片）重新渲染。所有数据已在 Trip Plan 生成时（场景 S6）一次性返回，tab 切换为纯前端 state 操作，无网络请求。 | 仅渲染 active day，非 active day 不占 DOM 高度。不重置 per-period candidate index（用户在 DAY 1 切换了某段候选，切回 DAY 1 时候选状态保留）。 |
| Per-period 候选切换（F2） | 点击 F2 某段的 per-period `‹` 或 `›` 按钮 | 当前段（period）的 candidate index 更新（0 → 1 → 2 循环），RestaurantCard 更新为对应候选，indicator dots 同步高亮对应点。纯前端 state 操作，无网络请求。 | 首候选时 `‹` opacity 0.30（disabled）；末候选时 `›` opacity 0.30（disabled）。不跨段影响（每段独立维护自己的 candidate index）。 |
| Send 按钮启用规则 | 输入框字符数实时检测 | 字符数 ≥ 1：Send button `opacity: 1.0`（enabled）。字符数 = 0：`opacity: 0.30`（disabled，点击无反应）。 | 空格字符不计入有效字符数（`input.trim().length`）。**注意**：当前 Figma Make 原型未实装此状态（见 §3.1.1 warning callout）。 |
| Quick Action 预填（Trip Planner pill） | 点击 F1 快捷操作区 "Trip Planner" pill | 输入框内容设为 `Plan my trip…`，输入框获得 focus（弹出键盘）。用户可直接继续输入具体城市/日期，或删除默认文本重写。 | 预填后 Send button 立即 enabled（因字符数 ≥ 1）。 |
| F2 Trip Planner pill 隐藏 | 用户进入 F2 视图（通过 Trip Planner 路径） | F1 Quick action bar 区域的 "Trip Planner" pill 在 F2 视图内不显示（已在该功能内，无需重复引导）。整个 quick action bar row 可隐藏。 | 若用户通过 F2 input bar 发送消息触发普通推荐，系统判断 intent 后动态切换输出模板，pill 随视图模式联动显示/隐藏。 |
| 用户消息气泡（F1/F2 输入后） | 用户点击 Send 发送消息 | 用户输入的文本以右对齐、浅灰气泡（`bg.quick = #EBEBEB`，14pt corner radius）呈现在对话区。与 assistant 输出（无气泡自由流）形成左/右视觉对比。 | 仅用户消息有气泡；assistant 的新一轮输出（新卡片列表）同样以自由流渲染，无气泡容器。 |
| F2 行程导出 | 用户点击 greeting block 右侧 Export pill | 触发行程导出流程：将当前 `TripPlanRender` 全量数据格式化为 markdown / PDF / PNG 并下载；可选 LLM 子调用生成更友好的 narrative 格式。demo 态为静态 no-op（pill 点击无实际导出）。 | 导出文件名建议格式：`tastehunter-trip-{city}-{days}d-{date}.md`。实装优先级：markdown 导出 → PNG → PDF。 |

##### UI 状态矩阵

各元素在不同视图状态下的显示/隐藏/禁用规则汇总：

| UI 元素 | F1 默认态 | F1 展开态 | F1.1 首位 | F1.1 中间位 | F1.1 末位 | F2 |
|---|---|---|---|---|---|---|
| Trip Planner pill | ✅ 显示 | ✅ 显示 | — (sheet 上层) | — | — | ❌ 隐藏 |
| Chevron-down/up | ✅ 显示 (down) | ✅ 显示 (up，旋转 180°) | — | — | — | ❌ 隐藏 |
| Bottom nav `‹` | — | — | ⬜ 30% disabled | ✅ 显示 | ✅ 显示 | — |
| Bottom nav counter pill | — | — | ✅ 显示 | ✅ 显示 | ✅ 显示 | — |
| Bottom nav `›` | — | — | ✅ 显示 | ✅ 显示 | ⬜ 30% disabled | — |
| Send button | ⬜ 30% opacity (空) | ⬜ 30% opacity (空) | ⬜ / ✅ (依输入) | 同左 | 同左 | ⬜ / ✅ (依输入) |
| Day tabs [DAY 1/2/3] | — | — | — | — | — | ✅ 三个 tabs，active 黑底白字 |
| Per-period `‹` (首候选) | — | — | — | — | — | ⬜ 30% disabled |
| Per-period `‹` (非首) | — | — | — | — | — | ✅ 显示 |
| Per-period `›` (末候选) | — | — | — | — | — | ⬜ 30% disabled |
| Per-period `›` (非末) | — | — | — | — | — | ✅ 显示 |
| Indicator dots | — | — | — | — | — | ✅ 每段卡片下方 3 点 |
| Export pill | — | — | — | — | — | ✅ Greeting block 右侧 |
| Yelp 归因条 | ❌ 不在 F1 | ❌ 不在 F1 | ✅ content panel 底部 | ✅ | ✅ | ❌ 不在 F2 |

---

#### §3.1.5 Out-of-scope — UI 明确不建设的内容

以下设计决策源自 `figma_make_prompt.md` "What NOT to do" 列表及 v2 Figma Make 实现审计，在此转录为 PRD 规范条目，防止实装时方向漂移。

| 禁止项 | 说明 | 违规后果 |
|---|---|---|
| ❌ assistant 文本气泡 | Greeting + 推荐卡片为自由流布局，不包裹在任何 chat bubble 容器内（仿 Claude.ai mobile）。**仅**用户消息使用右对齐浅灰气泡。 | 气泡包裹会压缩卡片可用宽度，且与设计基调（editorial / 白底自由流）冲突。 |
| ❌ Emoji 作为功能按钮 / 图标 | Emoji 仅用于 copy string 内的装饰（如 reason chip 文本中的 "🌅"），所有功能性图标必须使用 lucide-react 风格 line-art SVG。 | Emoji 在不同字体/平台渲染不一致，尺寸不可控，无法满足 WCAG 最小可点击目标（44×44pt）。 |
| ❌ Material Design 控件 | 无 FAB（Floating Action Button）/ 无 ripple 效果 / 无 Snackbar。所有 button 为 pill 形（圆角矩形）或圆形，无 Material 阴影模型。 | 视觉与暖色调 editorial 基调不符；增加不必要的依赖。 |
| ❌ TabBar / 底部导航栏 | 屏幕底部区域**专属**输入栏（聊天输入 + Send 按钮）。禁止添加全局 Tab bar 或底部 icon 导航。 | Tab bar 与输入栏空间冲突，且本 prototype 仅 3 屏，不需要全局导航层级。 |
| ❌ iOS 分段控制器 / Android material chip | Quick action 区域仅使用自定义 pill 形状（`bg.quick = #EBEBEB`，18pt radius）。禁止使用 UISegmentedControl 或 Material Chip 组件。 | 平台原生控件无法与 Taste hunter design token 对齐。 |
| ❌ 企业蓝 / Apple 蓝 accent | 唯一允许的色彩 accent 是 peach top bar（`peach.500 = #F5DCA6`）+ reason chip muted blue（`chip.bg = #F0F2FF` / `chip.text = #3349B3`）。禁止引入任何标准 Apple 蓝（`#007AFF`）或企业蓝。 | 破坏暖色调 × 极简灰度调色盘的整体一致性。 |
| ❌ "Menu" 大写 | F1.1 Content Panel 第三节标题必须保持小写 "menu"，仿 Google Maps minimal label 风格（原图细节，不是笔误）。 | 大写 "Menu" 引入不必要的标题层级感，与其他两节视觉权重不平衡。 |
| ❌ F1.1 侧边浮动 prev/next 箭头 | **v2 已废弃**。F1.1 prev/next 导航采用底部中央 nav bar（F1.1-BN-01 / BN-02 / BN-03），不得在屏幕左右边缘实装浮动箭头。v1 规格中的 `top: 540pt, left/right: 12pt` 绝对定位方案已被底部 nav 取代。 | 侧边箭头方案在 bottom sheet form factor 下会叠加在内容面板正文上，视觉混乱；且无处容纳 counter pill 文字。 |
| ❌ F2 左轨时间标签 | **v2 已废弃**。F2 餐厅卡片左侧不得添加 40pt 宽 vertical-rl 时间文字列（"上午 10 点 / 下午 1 点 / 晚上 7 点"）。时段信息由 period title（F2-PS-01，卡片正上方 section header）承载。RestaurantCard 的 `time` prop 保留为 deprecated 字段但**不传值**。 | 左轨时间列在 tab 切换式设计中冗余（period title 已传达时段），且压缩卡片可用宽度。 |
| ❌ F2 per-day Open route / Copy pills | **v2 已废弃**。F2 每日块顶部不得添加"Open route"黑底 pill 和"Copy"outline pill。day-level 导航完全依赖 day tabs；行程导出统一由 greeting block 右侧 Export pill（F2-EX-01）承担。 | F2 tab 切换式设计下，per-day pills 的上下文对应关系不清晰（切 tab 后 pills 随之消失，且导出语义应是全程而非单日）。 |

> [!warning] ⚠️ 实装注意
>
> 上述 "NOT to do" 列表在 Figma Make 生成阶段已通过 prompt 约束落地。但 Make 有时会在细节处"自作主张"回退到平台默认（如把 "menu" 改成 "Menu"，或给 assistant 文本加气泡）。**实装前须逐项对照本表 + Figma 稿做目视校验**，发现后立即在 Figma 中修复并重新导出 token。

> [!info] 设计稿验收清单（Section §3.1 整体 — v2 版本）
>
> 在 Figma 稿与实装均完成后，逐项过以下验收点：
> - [ ] F1 top bar 背景确为 `#F5DCA6`（非白、非灰）
> - [ ] Greeting + 推荐卡片为自由流布局，无气泡容器
> - [ ] Reason chip 颜色：背景 `#F0F2FF`，文字 `#3349B3`
> - [ ] F1 chevron-down 点击可展开至 top-10，图标旋转 180°（数据源须联通 `recommend_restaurants(offset=3)`，demo 阶段可用 placeholder）
> - [ ] F1 Send button 在 `input.trim().length === 0` 时 `opacity: 0.30`，不可点击（**当前 Figma Make 原型未实装，须在最终实装时补上**）
> - [ ] F1.1 为 bottom sheet modal（95% 高，顶部圆角 20pt，40% 黑色遮罩），非全屏 modal
> - [ ] F1.1 Hero photo 高度为 **280pt**（非 240pt）
> - [ ] F1.1 餐厅名为 Playfair Display Bold 22pt（非 Inter）
> - [ ] F1.1 底部中央 nav bar：`‹`（48×48pt 白圆）+ `N of M` 白色 pill（Inter Medium 15pt）+ `›`（48×48pt 白圆），水平居中，距 sheet 底部 32pt
> - [ ] F1.1 侧边无任何浮动箭头（`top: 540pt` 方案已废弃）
> - [ ] F1.1 "menu" 为小写
> - [ ] F2 顶部有 `[DAY 1] [DAY 2] [DAY 3]` 胶囊 tabs，active day = 黑底白字，inactive = 灰底黑字
> - [ ] F2 greeting block 右侧有 `download` icon + "导出" outline pill
> - [ ] F2 每段结构为：period title（Inter Semi Bold 15pt）→ activity 描述（Inter Regular 13pt `#4D4D4D`）→ RestaurantCard + per-period `‹ ›` → indicator dots
> - [ ] F2 无左轨时间标签列，无 per-day Open route / Copy pills
> - [ ] F2 per-period `‹ ›` 按钮为 28×28pt 白圆，`-left-2 / -right-2` 绝对定位，首/末候选时 opacity 0.30
> - [ ] RestaurantCard `time` prop 未传值（F2 v2 不使用）
> - [ ] 任何 lucide-style 图标均非 emoji 替代

---

<!-- §3.1 v2 — Sib A2 产出 · 2026-05-04 · F1.1 和 F2 与 Figma Make 原型严格对齐 -->
