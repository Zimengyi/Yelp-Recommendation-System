"""Streamlit render helpers for the Taste hunter F1 Chat Home view.

Each function maps to a PRD §3.1.1 module ID:
- `top_bar`        → F1-TB-01..03
- `greeting_block` → F1-GB-01..02
- `recommendation_card` → F1-CD-01..05
- `input_bar`      → F1-IB-01..02
- `footer`         → debug caption
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Callable

import streamlit as st


_STYLES_PATH = Path(__file__).parent / "styles.css"


def inject_styles() -> None:
    """Inject the PRD design-token CSS on every Streamlit rerun.

    Streamlit rebuilds the page DOM on interactions such as "Show more" and
    form submit, while `session_state` persists. Guarding this injection with
    session state makes the next rerun lose all custom card styles.
    """
    css = _STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def top_bar() -> None:
    """F1-TB-01..03 — peach top bar with hamburger | title | user-circle.

    Icons are decorative line-art SVGs (lucide-style). No click handlers in v0.1.
    """
    hamburger = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><line x1="4" y1="6" x2="20" y2="6"/>'
        '<line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>'
    )
    user_circle = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="10" r="3"/>'
        '<path d="M6.5 19a6 6 0 0 1 11 0"/></svg>'
    )
    st.markdown(
        f"""
        <div class="th-topbar">
          <span class="th-topbar__icon" aria-label="menu">{hamburger}</span>
          <span class="th-topbar__title">Taste hunter</span>
          <span class="th-topbar__icon" aria-label="user">{user_circle}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def greeting_block(title: str, subtitle: str) -> None:
    """F1-GB-01..02 — H1 + meta subtitle. Caller derives strings (LLM in prod)."""
    st.markdown(
        f"""
        <div class="th-greeting">
          <h1 class="th-greeting__h1">{html.escape(title)}</h1>
          <p class="th-greeting__sub">{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_meta(item: dict[str, Any]) -> str:
    """F1-CD-03 — `★ {rating} ({review_count}) · {category} · {price}`."""
    rating = item.get("rating")
    review_count = item.get("review_count")
    cats = item.get("categories") or []
    primary_cat = cats[0] if cats else ""
    price_level = item.get("price_level") or 0
    price = "$" * int(price_level) if price_level else ""

    parts: list[str] = []
    if rating is not None:
        rc = f"{int(review_count):,}" if review_count else ""
        parts.append(f"★ {rating}" + (f" ({rc})" if rc else ""))
    if primary_cat:
        parts.append(primary_cat)
    if price:
        parts.append(price)
    return " · ".join(parts)


def price_string(item: dict[str, Any]) -> str:
    price_level = item.get("price_level") or 0
    return "$" * int(price_level) if price_level else "$$"


def recommendation_card(item: dict[str, Any], index: int) -> None:
    """F1-CD-01..05 — thumb | name + meta + tagline + reason chip.

    `index` is 0-based; PRD shows rank 1-3 by default with chevron expanding to top-10.
    """
    name = html.escape(item.get("name", "—"))
    meta = html.escape(_format_meta(item))
    tagline = html.escape(item.get("reason_long", "") or "")
    chip = html.escape(item.get("reason_chip", "") or "")
    initial = (item.get("name", "?") or "?")[0].upper()

    chip_html = f'<span class="th-card__chip">{chip}</span>' if chip else ""

    st.markdown(
        f"""
        <div class="th-card">
          <div class="th-card__thumb" aria-hidden="true">{html.escape(initial)}</div>
          <div class="th-card__col">
            <p class="th-card__name">{name}</p>
            <p class="th-card__meta">{meta}</p>
            <p class="th-card__tagline">{tagline}</p>
            {chip_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def message_actions() -> None:
    """F1-MA — visual action row: copy / like / dislike / refresh."""
    icons = {
        "copy": '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
        "up": '<svg viewBox="0 0 24 24"><path d="M7 10v12"/><path d="M15 5.9 14 10h5.8a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.4 22H7"/><path d="M7 10 12 2a3 3 0 0 1 3 3.9"/></svg>',
        "down": '<svg viewBox="0 0 24 24"><path d="M17 14V2"/><path d="M9 18.1 10 14H4.2a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.6 2H17"/><path d="M17 14 12 22a3 3 0 0 1-3-3.9"/></svg>',
        "refresh": '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></svg>',
    }
    st.markdown(
        f"""
        <div class="th-actions" aria-label="message actions">
          <span>{icons["copy"]}</span>
          <span>{icons["up"]}</span>
          <span>{icons["down"]}</span>
          <span>{icons["refresh"]}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def trip_planner_pill() -> bool:
    """Render F1-QA Trip Planner pill. Returns True when clicked."""
    return st.button("✈  Trip Planner", key="th_trip_planner", type="secondary")


def input_bar(on_submit: Callable[[str], None], placeholder: str = "想吃辣？人均 30 以下？说说看…") -> None:
    """F1-IB-01..02 — text input + send button."""
    col_input, col_send = st.columns([6, 0.9])
    with col_input:
        query = st.text_input(
            "query",
            key="th_query_input",
            placeholder=placeholder,
            label_visibility="collapsed",
        )
    with col_send:
        send_clicked = st.button("⌃", key="th_send", use_container_width=True)
    if send_clicked and query and query.strip():
        on_submit(query.strip())


def detail_sheet(item: dict[str, Any], index: int, total: int) -> None:
    """F1.1 visual bottom-sheet detail overlay."""
    name = html.escape(item.get("name", "Restaurant"))
    city = html.escape(item.get("address", "").split(",")[-2].strip() if "," in item.get("address", "") else "Philadelphia")
    meta = html.escape(_format_meta(item))
    overview = html.escape(item.get("reason_long", "A strong local pick with a compact, high-signal Yelp profile."))
    menu = html.escape(_menu_guess(item))
    disabled_prev = "is-disabled" if index <= 0 else ""
    disabled_next = "is-disabled" if index >= total - 1 else ""
    st.markdown(
        f"""
        <div class="th-sheet-backdrop"></div>
        <div class="th-sheet">
          <div class="th-sheet__hero">
            <div class="th-sheet__close-vis">×</div>
            <div class="th-photo-badge">▣ 5</div>
          </div>
          <div class="th-sheet__body">
            <div class="th-sheet__title-row">
              <h2>{name} <span>({city})</span></h2>
              <span class="th-copy-mini">□</span>
            </div>
            <p class="th-sheet__meta">{meta}</p>
            <div class="th-pills">
              <span class="th-pill th-pill--dark">Directions</span>
              <span class="th-pill">Call</span>
              <span class="th-pill">Website</span>
            </div>
            <div class="th-panel">
              <section><h3>AI Overview</h3><p>{overview}</p></section>
              <section><h3>Review · ★ {item.get("rating", 4.5)}</h3><p>“A dependable neighborhood favorite with strong review momentum.”</p><small>— Yelp top review</small></section>
              <section><h3>menu</h3><p>{menu}</p></section>
            </div>
            <div class="th-attribution">Yelp Open Dataset · #b1u2 · 2026</div>
            <div class="th-bottom-nav-vis">
              <span class="{disabled_prev}">‹</span><b>{index + 1} of {total}</b><span class="{disabled_next}">›</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def trip_plan_view(active_day: int, slot_indices: dict[str, int]) -> None:
    """F2 visual trip plan shell from the Figma v2 ground truth."""
    days = _trip_demo_data()
    st.markdown(
        """
        <div class="th-trip-head">
          <div>
            <h1>LA · 3 days · 9 meals</h1>
            <p>Generated from your itinerary · regional clustering + cuisine diversity</p>
          </div>
          <span class="th-export">⇩ 导出</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i in range(3):
        with cols[i]:
            if st.button(f"DAY {i + 1}", key=f"th_day_{i}", type="primary" if active_day == i else "secondary", use_container_width=True):
                st.session_state["trip_day"] = i
                st.rerun()

    day = days[active_day]
    for period in day["periods"]:
        slot_key = f"{active_day}_{period['key']}"
        idx = slot_indices.get(slot_key, 0)
        item = period["restaurants"][idx]
        st.markdown(
            f"""
            <div class="th-period">
              <h2>{html.escape(period["title"])}</h2>
              <p>{html.escape(period["activity"])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, mid, right = st.columns([0.35, 6, 0.35])
        with left:
            if st.button("‹", key=f"prev_{slot_key}", disabled=idx == 0):
                st.session_state["trip_slots"][slot_key] = max(0, idx - 1)
                st.rerun()
        with mid:
            recommendation_card(item, idx)
        with right:
            if st.button("›", key=f"next_{slot_key}", disabled=idx >= 2):
                st.session_state["trip_slots"][slot_key] = min(2, idx + 1)
                st.rerun()
        dots = "".join(
            f'<span class="{"is-active" if j == idx else ""}"></span>' for j in range(3)
        )
        st.markdown(f'<div class="th-dots">{dots}</div>', unsafe_allow_html=True)


def footer(debug: dict[str, Any], mode: str, pool_size: int | None = None) -> None:
    """Footer caption — `latency · pool · mode` per acceptance gate."""
    latency = debug.get("latency_ms")
    pool = pool_size if pool_size is not None else debug.get("filter_pool_size")
    model = debug.get("model_version", "?")

    bits: list[str] = []
    if latency is not None:
        bits.append(f"backend latency: {float(latency):.1f} ms")
    if pool is not None:
        bits.append(f"pool: {pool} candidates")
    bits.append(f"mode: {mode}")
    bits.append(f"model: {model}")
    st.markdown(
        f'<div class="th-footer">{html.escape(" · ".join(bits))}</div>',
        unsafe_allow_html=True,
    )


def error_panel(message: str, hint: str | None = None) -> None:
    """Friendly error block when the backend is unreachable or returns 4xx/5xx."""
    full = message
    if hint:
        full = f"{message}\n\n_{hint}_"
    st.error(full)


def _menu_guess(item: dict[str, Any]) -> str:
    cats = " ".join(item.get("categories") or []).lower()
    if "sushi" in cats or "japanese" in cats:
        return "Tonkotsu $16 · Spicy Miso $17 · Gyoza $8"
    if "coffee" in cats or "bak" in cats:
        return "Latte $5 · Croissant $6 · Avocado toast $13"
    if "seafood" in cats:
        return "Oysters $18 · Lobster roll $24 · Clam chowder $12"
    return "Chef special $18 · House plate $16 · Seasonal side $8"


def _trip_demo_data() -> list[dict[str, Any]]:
    def r(name: str, rating: float, count: int, category: str, price: int, desc: str, chip: str) -> dict[str, Any]:
        return {
            "name": name,
            "rating": rating,
            "review_count": count,
            "categories": [category],
            "price_level": price,
            "reason_long": desc,
            "reason_chip": chip,
        }

    return [
        {
            "periods": [
                {"key": "morning", "title": "早晨", "activity": "参观盖蒂中心，欣赏欧洲艺术收藏和花园景观。", "restaurants": [
                    r("Getty View Café", 4.6, 892, "Café", 2, "Bright coffee stop before the museum climb.", "距盖蒂中心 0.3 mi"),
                    r("Brentwood Bakery", 4.5, 421, "Bakery", 2, "Quiet pastry counter for a slow morning.", "早晨营业中"),
                    r("Garden Terrace", 4.4, 618, "American", 2, "Light brunch with canyon views.", "适合 museum day"),
                ]},
                {"key": "lunch", "title": "中午", "activity": "漫步圣莫尼卡海边，享受海风和阳光。", "restaurants": [
                    r("Pier Seafood", 4.5, 1204, "Seafood", 2, "Casual seafood after the pier walk.", "距 Santa Monica Pier 5 min 步行"),
                    r("Ocean Deli", 4.4, 733, "Sandwiches", 2, "Fast lunch between beach stops.", "路线顺路"),
                    r("Sunny Bowl", 4.6, 389, "Healthy", 2, "Fresh bowls for a lighter midday meal.", "轻食平衡"),
                ]},
                {"key": "evening", "title": "晚上", "activity": "探索艺术区画廊，感受洛杉矶当代艺术氛围。", "restaurants": [
                    r("Tatsu Ramen", 4.7, 571, "Ramen", 1, "Late ramen near the gallery cluster.", "艺术区核心，步行可达"),
                    r("Gallery Wine Bar", 4.5, 804, "Wine Bars", 3, "Good after-gallery small plates.", "适合晚上"),
                    r("Little Tokyo Grill", 4.6, 956, "Japanese", 2, "Short ride from the Arts District.", "换一种日料"),
                ]},
            ]
        },
        {
            "periods": [
                {"key": "morning", "title": "早晨", "activity": "去 Griffith Observatory 看城市天际线。", "restaurants": [
                    r("Hilltop Coffee", 4.5, 690, "Coffee", 2, "Caffeine before the observatory trail.", "距山路入口近"),
                    r("Los Feliz Brunch", 4.6, 1042, "Brunch", 2, "Classic LA brunch near Griffith.", "同区高分"),
                    r("Vermont Bakery", 4.4, 512, "Bakery", 1, "Quick pastry stop before parking.", "节省时间"),
                ]},
                {"key": "lunch", "title": "中午", "activity": "沿 Hollywood 一带轻松走走，避开晚高峰。", "restaurants": [
                    r("Hollywood Tacos", 4.5, 1320, "Mexican", 1, "Fast, flavorful lunch near the walk.", "换 cuisine"),
                    r("Sunset Thai", 4.4, 905, "Thai", 2, "Spicy lunch option near Sunset.", "想吃辣"),
                    r("Studio Diner", 4.3, 1108, "Diner", 2, "Reliable comfort food for a group.", "选择稳"),
                ]},
                {"key": "evening", "title": "晚上", "activity": "在 LACMA 附近看灯光装置和夜景。", "restaurants": [
                    r("Wilshire Bistro", 4.6, 876, "American", 3, "Polished dinner near museum row.", "距 LACMA 0.4 mi"),
                    r("Miracle Mile Sushi", 4.5, 488, "Sushi Bars", 3, "Clean sushi option after museum time.", "晚餐轻盈"),
                    r("La Brea Pasta", 4.4, 611, "Italian", 2, "Comfort pasta without a long detour.", "路线紧凑"),
                ]},
            ]
        },
        {
            "periods": [
                {"key": "morning", "title": "早晨", "activity": "在 Rodeo Drive 附近散步，看橱窗和街景。", "restaurants": [
                    r("Beverly Café", 4.5, 760, "Café", 3, "Quiet coffee before shopping streets.", "步行 6 min"),
                    r("Canon Brunch", 4.6, 982, "Brunch", 3, "Polished breakfast near Beverly Hills.", "适合慢早晨"),
                    r("Pastry House", 4.4, 348, "Desserts", 2, "Small pastry stop before Rodeo.", "轻量选择"),
                ]},
                {"key": "lunch", "title": "中午", "activity": "转去 Little Tokyo，逛小店和日式街区。", "restaurants": [
                    r("Daikokuya", 4.5, 3201, "Ramen", 2, "Classic ramen anchor in Little Tokyo.", "街区核心"),
                    r("Sushi Gen", 4.6, 2550, "Sushi Bars", 3, "High-signal sushi lunch option.", "日料 top pick"),
                    r("Marugame Monzo", 4.5, 1760, "Japanese", 2, "Handmade udon for a warmer lunch.", "不重复 ramen"),
                ]},
                {"key": "evening", "title": "晚上", "activity": "回到 Downtown，看夜景后吃一顿收尾晚餐。", "restaurants": [
                    r("Bavel", 4.7, 2500, "Middle Eastern", 3, "High-energy final dinner downtown.", "收尾仪式感"),
                    r("Bestia", 4.6, 4300, "Italian", 4, "Celebratory dinner with strong reviews.", "高分热门"),
                    r("Water Grill", 4.5, 2100, "Seafood", 3, "Seafood dinner near downtown hotels.", "路线好收"),
                ]},
            ]
        },
    ]
