# Figma Make Prompt — Travel-aware Restaurant Recommender (Chatbot UI)

> 用法：直接把下面 `=== PROMPT START ===` 到 `=== PROMPT END ===` 之间的内容粘贴给 Figma Make。已经按 Make 偏好的"指令式英文 + 关键值清单"风格组织，结构化字段在前，叙事在后，避免 Make 自由发挥。

---

=== PROMPT START ===

Build a **3-screen mobile prototype** at iPhone 14 Pro dimensions (390×844pt) for **Taste hunter**, a travel-aware restaurant recommender chatbot. The app is an LLM-powered conversational agent that calls a DeepFM recommender system trained on the Yelp Open Dataset. Users get time-and-location-aware restaurant suggestions through chat and can plan multi-day trip meal itineraries.

Visual feel: **warm editorial × Apple-Maps × Claude-chat**. Soft peach top bar, serif title for restaurant names, minimal grayscale palette, line-art SVG icons (lucide-react style). NOT corporate-blue, NOT material-design.

## Design system

### Color tokens
- `peach.500` = #F5DCA6 — top bar background
- `bg.canvas` = #FFFFFF — page background
- `bg.card` = #FFFFFF — card surface
- `bg.panel` = #EBEBEB — content panel surface
- `bg.input` = #F2F2F2 — input field
- `bg.quick` = #EBEBEB — quick action chip
- `text.primary` = #1A1A1A
- `text.secondary` = #737373
- `text.tertiary` = #8C8C8C
- `text.body` = #4D4D4D
- `border.light` = #C7C7C7
- `border.dark` = #222222
- `divider` = #D6D6D6
- `chip.bg` = #F0F2FF
- `chip.text` = #3349B3
- `primary.fill` = #1A1A1A (button) / `primary.text` = #FFFFFF
- `photo.placeholder` = #B8A89E (hero) / #DCDDE8 (card thumb)
- `shadow.card` = 0 2 12 rgba(0,0,0,0.08)
- `shadow.float` = 0 2 8 rgba(0,0,0,0.12)

### Typography
- UI sans: **Inter** (Regular / Medium / Semi Bold / Bold)
- Restaurant name (display only): **Playfair Display Bold 22pt** — editorial serif. Fallback: PT Serif Bold, then Times New Roman Bold.
- App name "Taste hunter": Inter Semi Bold 16pt
- H1 chat header: Inter Bold 22pt
- Section header: Inter Semi Bold 13pt
- Card title: Inter Semi Bold 15pt
- Meta / subtitle: Inter Regular 13pt
- Body: Inter Regular 12pt
- Pill label: Inter Medium 14pt
- Reason chip text: Inter Medium 11pt
- Caption: Inter Regular 11pt

### Spacing rhythm
- Page horizontal padding: 20pt
- Top bar: 50pt top safe area + 14pt bottom padding
- Section vertical gap: 14pt
- Card padding: 12pt; card-to-card gap: 10pt
- Card body inner gap: 4pt
- Bottom safe area for input bar: 28pt

### Iconography
Use **lucide-react** style line icons (1.5–2pt stroke, rounded ends, viewBox 24×24). Required:
- `menu` (3-line hamburger), `user-circle` (silhouette outline), `x` (close), `camera`, `images`, `copy` (overlapping squares), `chevron-down`, `chevron-left`, `chevron-right`, `chevron-up`, `refresh-ccw`, `thumbs-up`, `thumbs-down`, `plane` (Trip Planner), `star` (filled, used inline in meta lines).

**Never** use emoji as functional buttons. Emoji are allowed only as garnishes inside copy strings (e.g. "Wed brunch in Redmond ☕", reason chips like "🌅 上午 10 点").

---

## SCREEN 1 — F1: Chat Home

A conversational chat interface modeled on Claude.ai mobile: **assistant text flows freely on the page**, NOT inside chat bubbles. Only the restaurant cards (each card individually) have container shapes. The user's eventual message bubble (when they reply) sits right-aligned with a light gray bubble — but the initial assistant greeting + cards have NO outer wrapping container.

Top to bottom layout:

### 1. Top bar (sticky, peach background)
- Left: hamburger menu (3 lines, 20×2pt, 4pt gap, black)
- Center: "Taste hunter" Inter Semi Bold 16pt black
- Right: user-circle silhouette icon, 28×28pt, 1.8pt stroke, black

### 2. Conversation area (scrollable, white bg, padding 20pt)
**a. Greeting block** — free text on page, no container:
- H1: `Wed brunch in Redmond ☕` — Inter Bold 22pt
- Subtitle: `10:32 AM · 5 picks based on your location & this week's trends` — Inter Regular 13pt secondary

**b. Restaurant card list** — vertical, 10pt gap, no wrapping container. Default shows 3 cards, expandable to 10. Each card:
- Layout: horizontal, padding 12pt, gap 12pt, white surface, 14pt corner radius, `shadow.card` drop shadow
- Left: 80×96pt photo placeholder, 10pt corner radius, fill `#DCDDE8`
- Right column (vertical, gap 4pt, fill remaining width):
  - Restaurant name (Inter Semi Bold 15pt)
  - Meta (Inter Regular 11pt secondary): `★ {rating} ({reviewCount}) · {category}` (use unicode ★ here, NOT a separate icon — this is the inline meta line)
  - One-line description (Inter Regular 12pt body color)
  - **Reason chip** — pill with `chip.bg` background, 6pt radius, 8/3pt padding, `chip.text` color text

Sample card content (use exactly these):

| Name | Meta | Description | Reason chip |
|---|---|---|---|
| Moonlark's Dinette | ★ 4.8 (1,038) · American · Brunch · $$ | Downtown 高分早午餐，炸鸡华夫饼必点 | 🌅 上午 10 点 · 1.1 mi · 周榜 Top 3 |
| Cafe Corina | ★ 4.6 (421) · Coffee · Breakfast · $$ | 本地人推荐的 latte + avocado toast 组合 | 📍 距你 0.8 mi · 周三上午营业中 |
| Marlowe's Kitchen | ★ 4.5 (892) · Bakery · Pastry · $ | 现烤可颂 + 手冲，安静角落适合一个人 | 🍪 与你常去的店风格相似 |

**c. Expand chevron** — centered below the 3rd card, line-art chevron-down icon 22×22pt color #9AA0A6. Tap behavior: expands list to top-10 cards (you don't need to render all 10, just the affordance).

**d. Message-action icon row** — left-aligned, 4 icons in a row, 18pt size, color `#8A8A8A`, 18pt horizontal gap, 4pt vertical padding. Order: `copy`, `thumbs-up`, `thumbs-down`, `refresh-ccw`. These are the standard chat-assistant message reactions.

### 3. Quick action bar (white bg, padding 4/8pt vertical, 20pt horizontal)
A single chip pill, left-aligned:
- "Trip Planner" with leading `plane` icon (14pt black) + label (Inter Medium 12pt black)
- Background `bg.quick`, 18pt radius, padding 8/14pt

### 4. Input bar (white bg, bottom-pinned, 28pt bottom safe-area padding)
- Rounded input field `bg.input`, 22pt corner radius, padding 11/16pt, FILL remaining width
- Placeholder: `想吃辣？人均 30 以下？说说看…` Inter Regular 14pt tertiary
- Trailing 40×40pt black circle button with white chevron-up icon (18pt, 2.5pt stroke) — the send button

---

## SCREEN 2 — F1.1: Restaurant Detail Overlay

Triggered when user taps a single card on F1. Full-screen modal slide-up. Layout top to bottom:

### 1. Top bar — IDENTICAL to F1's top bar (peach, same hamburger / Taste hunter / user-circle).

### 2. Hero photo (240pt tall, full bleed width)
- Background fill `photo.placeholder` (in production: real Yelp photo of restaurant storefront)
- Overlay 1 (top-left, 14pt from edges): 32×32pt white circle with line-art `x` icon (16pt, color #222) — the close button
- Overlay 2 (bottom-right, 14pt from edges): pill badge — black 55%-opacity background, 12pt radius, padding 5/9pt, contains: white camera icon (13pt, 2pt stroke) + space + "5" (Inter Medium 11pt white)

### 3. Restaurant info block (white, padding 18/20pt, 14pt vertical gap)
**a. Title row** (horizontal, gap 8pt, center cross-axis):
- `Tatsu Ramen   (Arts District)` — **Playfair Display Bold 22pt** primary color (note: 3 spaces between name and the parenthesized district)
- Trailing copy icon (line-art, 16pt, #666) — copy address to clipboard

**b. Meta row** (horizontal, gap 14pt between left-group and "$"):
- Left group: `4.7` + inline filled black star SVG (12pt, no stroke) + `571  ·  Ramen restaurant` — all Inter Regular 13pt secondary
- Right: `$` — Inter Regular 13pt secondary

**c. Action pills row** — horizontal, 10pt gap, FULL WIDTH (`align: flex-start`), 4pt top/bottom padding:
- **[Directions]** — BLACK FILL `primary.fill`, WHITE TEXT `primary.text`, Inter Medium 14pt, 22pt corner radius, padding 11/22pt. **No icon, text only.**
- **[Call]** — WHITE FILL, 1pt `border.light` outline, BLACK TEXT, same dimensions
- **[Website]** — WHITE FILL, 1pt `border.light` outline, BLACK TEXT, same dimensions

**Critical**: pills row must NOT visually overlap the content panel below. Use 14pt min gap between this row and the panel.

### 4. Content panel (gray, FILL remaining vertical space)
- Surface `bg.panel`, 12pt corner radius, padding 16pt, vertical gap 10pt
- Three sections separated by 1pt full-width `divider` lines:

**Section 1 — AI Overview**
- Header: `AI Overview` Inter Semi Bold 13pt primary
- Body: `招牌 tonkotsu，汤底 12 小时熬制；本周「辣味噌限定」别错过。本地客比游客多，氛围 chill。` Inter Regular 12pt body color

`---` divider (1pt #D6D6D6, full width)

**Section 2 — Review**
- Header row (horizontal, gap 6pt): `Review` Inter Semi Bold 13pt + ` · ` + filled mini star (11pt, #444) + `4.7` Inter Regular 12pt secondary
- Quote: `"Best ramen south of LA. The chashu melts."` Inter Regular 12pt body
- Attribution: `— Yelp top review` Inter Regular 11pt tertiary

`---` divider

**Section 3 — menu** (lowercase 'm' is intentional, mimicking Google Maps' minimal label style)
- Header: `menu` Inter Semi Bold 13pt
- Body: `Tonkotsu  $16  ·  Spicy Miso  $17  ·  Veggie  $15  ·  Gyoza  $8` Inter Regular 12pt body

### 5. Bottom strip (8pt top padding, inside the detail container, below content panel)
- Single line, left-aligned: `Yelp Open Dataset · #b1u2 · 2026` Inter Regular 11pt tertiary

### 6. Floating side-edge nav arrows (CRITICAL — these float ON TOP of the screen at the LEFT and RIGHT EDGES, not in any container)
Two 44×44pt white circular buttons, ABSOLUTE-positioned over the screen:
- Left button: `top: 540pt, left: 12pt` — chevron-left icon (18pt, #222)
- Right button: `top: 540pt, right: 12pt` — chevron-right icon (18pt, #222)
- Both: white fill, 1pt `border.light` stroke, `shadow.float` drop shadow, 22pt corner radius (full circle)
- Function: prev/next restaurant from the F1 card list (swipe between siblings without dismissing modal)

---

## SCREEN 3 — F2: Trip Plan

Same shell as F1 (peach top bar, chat-flow content area, input bar at bottom). The assistant message contains a multi-day meal plan instead of a flat card list.

### Conversation content
**a. Greeting block** (free text, no container):
- H1: `LA · 3 days · 9 meals` Inter Bold 22pt
- Subtitle: `Generated from your itinerary · regional clustering + cuisine diversity` Inter Regular 13pt secondary

**b. Day blocks** — vertical, 14pt gap. Each day block:
- Day header row (horizontal, space-between):
  - Left: day label `DAY 3 · LA 市区 + 圣莫尼卡` Inter Bold 18pt primary
  - Right: two pills inline (gap 6pt) — `[Open route]` BLACK FILL with white plane icon + label (Inter Medium 12pt white), and `[Copy]` WHITE outline pill (same as F1.1's Call style)
- 3 stacked meal cards. Each meal card extends the F1 card schema with a **left rail time-label**:
  - Add a left-most column (40pt wide) BEFORE the photo: vertical text `上午 10 点` (or `下午 1 点` / `晚上 7 点`) in Inter Medium 11pt secondary, top-aligned
  - Then photo + body (same as F1 card)

Sample DAY 3 content:
| Time | Restaurant | Reason |
|---|---|---|
| 上午 10 点 | Moonlark's Dinette · ★ 4.8 (1,038) · American · Brunch · $$ · "Downtown 高分早午餐" | 🌅 起床后 15 min 步行 |
| 下午 1 点 | Bestia · ★ 4.7 (3,201) · Italian · $$$ · "Arts District 名店，意面是招牌" | 🍝 跨日避开海鲜 |
| 晚上 7 点 | Water Grill · ★ 4.4 (2,773) · Seafood · $$$ · "圣莫尼卡精致海鲜" | 🌅 看完夕阳 5 min 步行 |

The Trip Planner pill above the input is REMOVED on this screen (already in this view). Input bar same as F1.

---

## Interaction notes
- **F1 → F1.1**: tapping any restaurant card slides F1.1 up as a full-screen modal. The `x` button or swipe-down dismisses. Side-edge ‹ › chevrons swipe between sibling restaurants without closing.
- **F1 chevron-down**: expands 3-card list to top-10. Chevron rotates 180° to chevron-up when expanded.
- **F1.1 nav arrows**: do NOT show on the first/last restaurant in the list (gray out or hide).
- **Quick action "Trip Planner"** pill on F1: tapping pre-fills the input with `Plan my trip…` and focuses the input.
- **Send button on input bar**: enabled (black) only when input has ≥1 character; disabled state is 30% opacity.

---

## What NOT to do
1. ❌ No bubble around assistant text. Greeting + cards are FREE TEXT on the page background (Claude.ai mobile pattern), NOT in chat bubbles. Only **user** messages get a bubble (right-aligned, light gray) — and there's no user message in F1's initial state.
2. ❌ No emoji as functional buttons / icons. Use lucide-style line-art SVGs.
3. ❌ No Material Design FAB / ripple / TabBar at bottom. Bottom is reserved for the chat input.
4. ❌ No corporate blue / Apple-blue accent. The only color accent is the peach top bar; everything else is grayscale + the muted blue chip color.
5. ❌ Do NOT change "menu" to "Menu" in F1.1 — lowercase is intentional (matches Google Maps).
6. ❌ Do NOT put the prev/next nav arrows in the bottom strip. They MUST float on the left and right screen edges, vertically near y=540.
7. ❌ Do NOT add iOS segmented controls / Android material chips. The reason chip is a custom shape (see spec).
8. ❌ Do NOT add a TabBar / bottom navigation. There's no global navigation in this prototype.

---

## Reference benchmarks (visual mood)
- **Chat layout**: Claude.ai mobile (free-flowing assistant text, no bubbles)
- **Restaurant detail page**: Google Maps place detail (hero photo, action-pill row, gray content panel sectioned)
- **Editorial serif title**: Resy / Eater (Playfair Display feel)
- **Reason chip**: Pinterest "More like this" tags
- **Top-bar warm peach**: La Bonne Femme app / muted Wes-Anderson palette

## Deliverables
- Three artboards: `F1 — Chat Home`, `F1.1 — Restaurant Detail`, `F2 — Trip Plan`
- All at 390×844pt (iPhone 14 Pro)
- Use Auto Layout everywhere; component-ize the restaurant card and pill button
- Export tokens as Figma variables (color + spacing + typography)

=== PROMPT END ===

---

## 给你（Haobo）的辅助说明

### Make 跑出来后建议改 / 检查的几个地方
1. **餐厅名 serif 字体**：Make 可能装不了 Playfair Display，会回退 Times。记得手动换成 Playfair（Figma 里 fonts.google.com → install）
2. **峰值色 #F5DCA6**：颜色 hex 我从你 image 27 截图里推算的，可能你想要更暖/更淡，到时候直接调 token 即可
3. **F2 我没跟你迭代过**，里面的字段（左侧时间 rail / Open route + Copy 双 pill）是我按 wireframe v1 推断的——你看到效果不对的话直接踢
4. **「menu」小写**和**「Yelp Open Dataset · #b1u2 · 2026」**这两条是 image 21 里你原图就有的细节，我专门写在"NOT to do"里防止 Make 自作主张改成大写或换成 Google Maps

### Make 没法靠 prompt 给的东西
- 真实的 Yelp 餐厅照片（要么 Make 用占位，要么后期用 plugin 拉 Yelp photos.json）
- 实际的交互动画（slide-up modal / 卡片展开）只能在 Figma prototype 模式接 connection
- 跨语言 emoji 在不同字体里渲染差异

### 复用建议
这个 prompt 文件可以扔到 `canvas/ml2/project/` 里 commit 一份，万一 Make 改坏了你重跑——不用从对话里翻。文件路径已经写到：
`canvas/ml2/project/figma_make_prompt.md`
