# Taste hunter — Streamlit frontend (v0.1)

Phase 8 demo for **F1 Chat Home** (homepage push + chat input). Talks to the
FastAPI backend at `http://localhost:8000` via the contract in
[`../shared/API_CONTRACT.md`](../shared/API_CONTRACT.md).

Out of scope for v0.1:
- F1.1 Restaurant Detail Overlay (bottom sheet)
- F2 Trip Plan (day tabs)
- F1 Message Action icons (copy / thumbs / refresh)
- LLM intent extraction (query is passed through as-is)

## Run

```bash
# Terminal 1 — backend (mock mode)
cd app/backend
pip install -e .
PIPELINE=mock uvicorn main:app --port 8000

# Terminal 2 — frontend
cd app/frontend
pip install -e .
BACKEND_URL=http://localhost:8000 streamlit run app.py
# → http://localhost:8501
```

`BACKEND_URL` defaults to `http://localhost:8000` if unset.

## E2E smoke

```bash
cd app/frontend
bash e2e_smoke.sh
```

The script boots the backend (`PIPELINE=mock`) + the Streamlit app, waits for
both to come up, and exercises:

- `GET /api/health` (backend)
- `GET /api/users/sample?n=3`
- `POST /api/recommend` with `query=null` (homepage_push)
- `POST /api/recommend` with `query="想吃辣的"` (query_chat)
- `GET /` on the Streamlit server (200 + Streamlit marker)
- `GET /_stcore/health` on Streamlit core

Logs are saved to `.smoke_logs/`. Exits non-zero on any failure.

## Project layout

```
app/frontend/
├── pyproject.toml      streamlit + httpx + python-dotenv
├── app.py              Streamlit entry — page config, sidebar user picker, main flow
├── api_client.py       httpx wrapper around backend (recommend / sample_users / health)
├── components.py       render fns: top_bar, greeting_block, recommendation_card, input_bar, footer
├── styles.css          PRD §3.1 v2 design tokens (peach.500, Inter, spacing rhythm)
├── e2e_smoke.sh        boot backend + frontend, verify endpoints
└── README.md           this file
```

## Component → PRD field map

| Function (`components.py`)    | PRD module IDs                |
|------------------------------|-------------------------------|
| `top_bar`                    | F1-TB-01..03                  |
| `greeting_block`             | F1-GB-01..02                  |
| `recommendation_card`        | F1-CD-01..05                  |
| `input_bar`                  | F1-IB-01..02                  |
| `footer`                     | debug caption (latency/pool/mode) |

## ASCII layout (rendered)

```
┌─────────────────────────────────────┐
│      ☰      Taste hunter      ⊙     │  ← peach.500 top bar (F1-TB)
├─────────────────────────────────────┤
│  Wed brunch in Philadelphia ☕       │  ← H1 (F1-GB-01)
│  10:42 · 3 picks based on your …    │  ← subtitle (F1-GB-02)
│                                     │
│  ┌──┐  Moonlark's Dinette           │
│  │JD│  ★ 4.8 (1,038) · American · $$│  ← card 1..3 (F1-CD)
│  └──┘  Downtown 高分早午餐…          │
│        🌅 上午 10 点 · Top 3         │
│  ⌄ Show more (7 more)               │  ← chevron expand (F1-EX-01)
│                                     │
│  [想吃辣? 人均 30 以下? …] [Send ↑]   │  ← input bar (F1-IB)
│  backend latency: 99 ms · pool: 638 │  ← debug footer
│  · mode: homepage_push · model: …   │
└─────────────────────────────────────┘
```

## Manual visual verification checklist

After `streamlit run app.py` open `http://localhost:8501`:

- [ ] Peach (`#F5DCA6`) top bar with hamburger icon | "Taste hunter" centered | user-circle icon
- [ ] Inter font loaded (visible in DevTools → Computed → font-family)
- [ ] Sidebar user picker populated — 10 users from `/api/users/sample`
- [ ] Switch user → cards refresh (homepage_push)
- [ ] 3 cards visible by default; "⌄ Show more" reveals up to 10
- [ ] Each card shows: thumb (gray-blue color block), name, ★ rating + count + cat + $$$, tagline, reason chip
- [ ] Type `想吃辣的` + Enter → cards refresh, footer shows `mode: query_chat`
- [ ] Backend latency / pool size / mode visible in footer
- [ ] Reset session button clears state
- [ ] Stopping backend then refreshing shows a friendly error (not a stack trace)

## Design fidelity notes

- **Streamlit constraints**: pixel-perfect Figma mapping isn't possible without a custom
  React component. We approximate via injected CSS variables + `st.markdown(..., unsafe_allow_html=True)`.
- The PRD top-bar is sticky-positioned and uses peach.500 — this is achieved.
- Send button is a Streamlit form-submit button restyled to round-pill black (primary.fill).
- Card layout uses CSS grid `80px 1fr` matching the PRD 80×96pt thumb spec.
- Reason chip uses `chip.bg #F0F2FF` / `chip.text #3349B3` per token spec.
- Default card thumb is the placeholder color `#DCDDE8` with the first letter of the
  restaurant name as a subtle watermark — acceptable v0.1 stand-in until Yelp photo wiring.

## Dependencies

```toml
streamlit>=1.30
httpx>=0.25
python-dotenv>=1.0
```

Dev (optional): `pytest>=7.4`.
