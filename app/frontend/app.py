"""Taste hunter — Streamlit demo shell.

Phase 8 demo aligned to PRD §3.1 v2 / Figma Make ground truth:
F1 chat home, F1.1 bottom-sheet detail, and F2 tabbed trip plan.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

import api_client
import components


PAGE_TITLE = "Taste hunter"
DEFAULT_TOP_K = 10
DEFAULT_VISIBLE_CARDS = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _greeting_strings(rec_payload: dict[str, Any]) -> tuple[str, str]:
    """Derive H1 + subtitle from the response. LLM-generated in prod; static here."""
    now = datetime.now()
    hour = now.hour
    if hour < 11:
        slot, emoji = "morning", "☕"
    elif hour < 14:
        slot, emoji = "lunch", "🥗"
    elif hour < 17:
        slot, emoji = "afternoon", "🍰"
    elif hour < 21:
        slot, emoji = "dinner", "🍽️"
    else:
        slot, emoji = "late night", "🌙"
    weekday = now.strftime("%a")
    city = rec_payload.get("target_city") or "your area"
    n_recs = len(rec_payload.get("recommendations", []))

    h1 = f"{weekday} {slot} in {city} {emoji}"
    sub = (
        f"{now.strftime('%H:%M')} · {n_recs} picks based on your location & "
        f"this week's trends"
    )
    return h1, sub


@st.cache_data(ttl=600, show_spinner=False)
def _cached_sample_users(n: int = 10, city: str | None = None) -> list[dict[str, Any]]:
    """Cache user list for 10min so the dropdown doesn't refetch on every interaction."""
    return api_client.sample_users(n=n, city=city)


def _fetch_recommendations(user_id: str, query: str | None) -> dict[str, Any] | None:
    """Wrap api_client.recommend with friendly error handling. Returns None on failure."""
    try:
        with st.spinner("Finding spots for you…"):
            return api_client.recommend(
                user_id=user_id, query=query, top_k=DEFAULT_TOP_K
            )
    except api_client.BackendError as exc:
        components.error_panel(
            f"Recommendation failed: {exc}",
            hint="Is the backend running on http://localhost:8000? "
                 "Try `cd app/backend && uvicorn main:app --port 8000`.",
        )
        return None


def _set_recommendations(payload: dict[str, Any], mode: str) -> None:
    st.session_state["rec_payload"] = payload
    st.session_state["mode"] = mode
    st.session_state["visible_cards"] = DEFAULT_VISIBLE_CARDS


def _on_query_submit(query: str) -> None:
    if _is_trip_query(query):
        st.session_state["view_mode"] = "trip"
        st.session_state.setdefault("trip_slots", {})
        st.session_state["trip_day"] = 0
        st.rerun()
        return

    user_id = st.session_state.get("user_id")
    if not user_id:
        components.error_panel("Pick a user first.")
        return
    payload = _fetch_recommendations(user_id, query)
    if payload is not None:
        _set_recommendations(payload, mode=payload.get("mode", "query_chat"))
        st.rerun()


def _is_trip_query(query: str) -> bool:
    q = query.lower()
    return any(token in q for token in ["trip", "plan my trip", "行程", "旅行", "旅游", "玩 3 天", "玩3天"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon="🍽️",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    components.inject_styles()
    components.top_bar()
    st.session_state.setdefault("view_mode", "home")
    st.session_state.setdefault("trip_slots", {})

    # --- Sidebar: user picker + reset ---
    with st.sidebar:
        st.markdown("### Demo controls")
        try:
            users = _cached_sample_users(n=10)
        except api_client.BackendError as exc:
            components.error_panel(
                f"Cannot reach backend: {exc}",
                hint="Start it with `cd app/backend && uvicorn main:app --port 8000`.",
            )
            st.stop()

        if not users:
            components.error_panel("Backend returned no sample users.")
            st.stop()

        if st.session_state.get("detail_open"):
            st.markdown("### Detail overlay")
            if st.button("Close detail", key="th_sidebar_close_detail"):
                st.session_state["detail_open"] = False
                st.rerun()
            cprev, cnext = st.columns(2)
            with cprev:
                if st.button("‹ Prev", key="th_sidebar_prev_detail"):
                    st.session_state["detail_index"] = max(0, st.session_state.get("detail_index", 0) - 1)
                    st.rerun()
            with cnext:
                if st.button("Next ›", key="th_sidebar_next_detail"):
                    visible_now = st.session_state.get("visible_cards", DEFAULT_VISIBLE_CARDS)
                    st.session_state["detail_index"] = min(visible_now - 1, st.session_state.get("detail_index", 0) + 1)
                    st.rerun()

        labels = [u.get("label") or u["user_id"] for u in users]
        # Restore previous selection if user_id still in list, else default 0
        prev_user_id = st.session_state.get("user_id")
        try:
            default_idx = next(
                i for i, u in enumerate(users) if u["user_id"] == prev_user_id
            )
        except StopIteration:
            default_idx = 0

        chosen_idx = st.selectbox(
            "Demo user",
            options=list(range(len(users))),
            format_func=lambda i: labels[i],
            index=default_idx,
            key="user_picker",
        )
        chosen_user_id = users[chosen_idx]["user_id"]

        # On user switch (or first load), refetch homepage push
        if chosen_user_id != st.session_state.get("user_id"):
            st.session_state["user_id"] = chosen_user_id
            payload = _fetch_recommendations(chosen_user_id, query=None)
            if payload is not None:
                _set_recommendations(payload, mode=payload.get("mode", "homepage_push"))

        if st.button("🔄 Reset session", type="secondary"):
            for k in [
                "rec_payload", "mode", "visible_cards", "user_id",
                "detail_open", "detail_index", "view_mode", "trip_day", "trip_slots",
            ]:
                st.session_state.pop(k, None)
            st.cache_data.clear()
            st.rerun()

    if st.session_state.get("view_mode") == "trip":
        st.session_state.setdefault("trip_day", 0)
        st.session_state.setdefault("trip_slots", {})
        components.trip_plan_view(
            active_day=st.session_state["trip_day"],
            slot_indices=st.session_state["trip_slots"],
        )
        components.input_bar(_on_query_submit, placeholder="把第二天午餐换成素食？")
        return

    # --- Main view: greeting + cards ---
    payload = st.session_state.get("rec_payload")
    if payload is None:
        components.error_panel(
            "No recommendations loaded yet — pick a user in the sidebar.",
        )
        return

    h1, sub = _greeting_strings(payload)
    components.greeting_block(h1, sub)

    recs = payload.get("recommendations", [])
    visible = st.session_state.get("visible_cards", DEFAULT_VISIBLE_CARDS)
    visible = min(visible, len(recs))

    for i, item in enumerate(recs[:visible]):
        components.recommendation_card(item, i)
        if st.button("View details", key=f"th_detail_{i}", type="secondary"):
            st.session_state["detail_open"] = True
            st.session_state["detail_index"] = i
            st.rerun()

    # Show more / Show less chevron equivalent (F1-EX-01)
    total = min(len(recs), DEFAULT_TOP_K)
    if visible < total:
        if st.button(
            f"⌄  Show more ({total - visible} more)",
            key="th_show_more",
            type="secondary",
        ):
            st.session_state["visible_cards"] = total
            st.rerun()
    elif visible > DEFAULT_VISIBLE_CARDS and total > DEFAULT_VISIBLE_CARDS:
        if st.button("⌃  Show less", key="th_show_less", type="secondary"):
            st.session_state["visible_cards"] = DEFAULT_VISIBLE_CARDS
            st.rerun()

    components.message_actions()

    if components.trip_planner_pill():
        st.session_state["view_mode"] = "trip"
        st.session_state["trip_day"] = 0
        st.session_state.setdefault("trip_slots", {})
        st.rerun()

    if st.session_state.get("detail_open"):
        detail_index = min(st.session_state.get("detail_index", 0), len(recs) - 1)
        if recs:
            components.detail_sheet(recs[detail_index], detail_index, len(recs[:visible]))
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("‹", key="th_detail_prev", disabled=detail_index <= 0):
                    st.session_state["detail_index"] = detail_index - 1
                    st.rerun()
            with c2:
                if st.button("Close detail", key="th_detail_close", use_container_width=True):
                    st.session_state["detail_open"] = False
                    st.rerun()
            with c3:
                if st.button("›", key="th_detail_next", disabled=detail_index >= visible - 1):
                    st.session_state["detail_index"] = detail_index + 1
                    st.rerun()

    # --- Bottom input + footer ---
    components.input_bar(_on_query_submit)

    components.footer(
        payload.get("debug", {}),
        mode=st.session_state.get("mode", "homepage_push"),
    )


if __name__ == "__main__":
    main()
