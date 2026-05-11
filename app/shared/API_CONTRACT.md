# Taste hunter — Frontend ↔ Backend API Contract

**Version**: v0.1 (2026-05-09)
**Stack**: FastAPI backend ↔ Streamlit frontend (HTTP/JSON)
**Purpose**: Wire Phase 8 Streamlit demo to Pipeline C (Phase 6.1c hard-filter + DeepFM v2 ranking). Mock first, swap to real model tomorrow.

## Scenarios covered (per PRD §3.1 v2 + user 2026-05-09 directive)

| Scenario | UI screen | Trigger | Backend mode |
|---|---|---|---|
| **S0 — Homepage push recommendation** | F1 Chat Home (entry view, `query=null`) | App open / refresh | `homepage_push` — Pipeline C with empty query, returns top-3 cards based on user profile + time-of-day |
| **S2 — Query-based chat recommendation** | F1 Chat Home (with input) | User types & presses send | `query_chat` — Pipeline C with NL query passed through (currently treated same as S0; future: LLM intent extraction inserts hard-filter constraints) |

F1.1 Restaurant Detail Overlay and F2 Trip Plan are explicitly **out of scope for this v0.1**.

---

## Endpoints

### `POST /api/recommend`

Returns top-K restaurant recommendations.

**Request body** (Pydantic model `RecommendRequest`):

```json
{
  "user_id": "qVc8ODYU5SZjKXVBgXdI7w",
  "query": null,
  "target_city": null,
  "top_k": 10
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | str | yes | Yelp `user_id` from `data/cleaned/users_target.parquet`, or `"demo_user_<n>"` for canned demo profiles |
| `query` | str \| null | no | Natural language input. `null` → S0 homepage push. Non-null → S2 chat |
| `target_city` | str \| null | no | Explicit city filter. `null` → derive from user's dominant train-history city |
| `top_k` | int | no | Default 10, max 20 |

**Response body** (Pydantic model `RecommendResponse`):

```json
{
  "user_id": "qVc8ODYU5SZjKXVBgXdI7w",
  "target_city": "Philadelphia",
  "mode": "homepage_push",
  "recommendations": [
    {
      "rank": 1,
      "business_id": "abc123...",
      "name": "Joe's Pizza",
      "rating": 4.5,
      "review_count": 1234,
      "categories": ["Italian", "Pizza", "Restaurants"],
      "price_level": 2,
      "address": "123 Main St, Philadelphia, PA",
      "lat": 39.95,
      "lon": -75.16,
      "photo_url": null,
      "score": 0.873,
      "reason_chip": "🔥 周榜 Top 3 · 1.1 mi · ★ 4.5",
      "reason_long": "Italian comfort food matches your weekday brunch pattern",
      "deepfm_score": 0.873,
      "filter_passes": ["same_city", "price_match", "cuisine_overlap"]
    }
  ],
  "debug": {
    "filter_pool_size": 638,
    "latency_ms": 99.4,
    "model_version": "deepfm_final_v2",
    "pipeline": "C (hard-filter + DeepFM v2)"
  },
  "ts": "2026-05-09T03:00:00Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `mode` | enum | `"homepage_push"` \| `"query_chat"` |
| `recommendations[]` | list | Sorted by `score` desc, length `top_k` |
| `recommendations[i].rank` | int | 1-indexed |
| `recommendations[i].score` | float | DeepFM v2 sigmoid score in [0, 1] |
| `recommendations[i].reason_chip` | str | Short pill text per PRD F1-CD-05 (max ~30 chars, can include emoji) |
| `recommendations[i].reason_long` | str | One-line description per PRD F1-CD-04 (max 80 chars) |
| `recommendations[i].filter_passes` | list[str] | Which hard filter rules this candidate passed (debugging) |
| `debug.filter_pool_size` | int | How many candidates passed hard filter (pre-rank) |
| `debug.latency_ms` | float | Server-side end-to-end ms |
| `debug.model_version` | str | e.g. `"deepfm_final_v2"` or `"mock"` |

**Error responses** (4xx/5xx):

```json
{
  "error": "user_not_found",
  "detail": "user_id 'xxx' not in users_target.parquet",
  "request_id": "uuid"
}
```

| HTTP code | `error` | When |
|---|---|---|
| 400 | `invalid_request` | Schema validation fail |
| 404 | `user_not_found` | user_id doesn't exist (and not `demo_user_*`) |
| 503 | `model_not_loaded` | Backend started without `deepfm_final_v2.pt` available |
| 500 | `internal_error` | Anything else (include traceback in dev mode only) |

### `GET /api/health`

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "deepfm_final_v2",
  "uptime_seconds": 1234,
  "device": "mps"
}
```

### `GET /api/users/sample?n=5&city=Philadelphia`

Returns a sample of `n` user_ids for the demo's user-picker dropdown.

```json
{
  "users": [
    {
      "user_id": "qVc8...",
      "review_count": 87,
      "dominant_city": "Philadelphia",
      "avg_rating_given": 4.1,
      "label": "Active Philly user (87 reviews, ★ 4.1 avg)"
    }
  ]
}
```

| Query param | Default | Notes |
|---|---|---|
| `n` | 5 | Max 20 |
| `city` | null | Filter to users whose dominant city = given. Null = mixed |

### `GET /api/business/<business_id>`

(Out of scope for v0.1 — F1.1 detail overlay; stub it but return 501.)

---

## Backend implementation rules

1. **Mock-first**: Initial backend returns canned recommendations from a fixture JSON. No model load required to start the server.
2. **Pluggable `Pipeline` class**: `app/backend/pipeline_c.py` defines an interface:
   ```python
   class PipelineC(Protocol):
       def recommend(self, user_id: str, query: str | None,
                     target_city: str | None, top_k: int) -> list[Candidate]: ...
   ```
   With two implementations:
   - `MockPipeline` — returns from `app/backend/fixtures/mock_recommendations.json`
   - `DeepFMPipeline` — wraps `models/deepfm_final_v2.pt` + hard-filter logic from `notebooks/06c_pipeline_C_hard_filter.ipynb`. Loads model on startup.
3. **Choose at startup** via env var `PIPELINE=mock` (default) or `PIPELINE=deepfm` (production).
4. **CORS**: allow `http://localhost:8501` (Streamlit default) for cross-origin requests.
5. **Logging**: structlog with request_id correlation; log `latency_ms` and `filter_pool_size` per request.
6. **Type-safe**: 100% pydantic models for request/response. mypy clean.
7. **Tests**: pytest covering happy path + 4 error cases per endpoint. Run via `pytest app/backend/tests/`.

## Frontend implementation rules

1. **Streamlit single-file `app/frontend/app.py`** is fine for v0.1, but split data layer into `api_client.py` (HTTP client to backend).
2. **Match PRD §3.1 v2 design tokens** — peach.500 top bar, Inter font, Playfair Display for restaurant name in F1.1 (skip for v0.1). Apply via `st.markdown(unsafe_allow_html=True)` + custom CSS in `styles.css`.
3. **Two screens**:
   - **F1 Chat Home (homepage push)** — load on app open, calls `/api/recommend` with `query=null`. Renders 3 cards by default + "show more" expand to 10.
   - **F1 Chat Home (chat input)** — text input at bottom; on submit, calls `/api/recommend` with `query=<input>`. Replaces card list.
4. **User picker** — top-of-page `st.selectbox` populated from `/api/users/sample?n=10`. Sticky in session_state.
5. **Card component** — match PRD F1-CD-01..05 fields: thumb (placeholder for v0.1), name, meta line, tagline, reason_chip.
6. **Latency display** — small footer caption showing backend `debug.latency_ms`.
7. **Error states** — friendly message if backend down (poll `/api/health` on app start).
8. **Tests** — Streamlit doesn't lend itself to unit testing; instead add a `e2e_smoke.sh` that boots backend in mock mode + curls 3 scenarios + greps expected fields.

## Project structure

```
app/
├── shared/
│   └── API_CONTRACT.md        ← this file
├── backend/
│   ├── pyproject.toml         ← FastAPI + uvicorn + pydantic + structlog
│   ├── main.py                ← uvicorn entry
│   ├── api.py                 ← FastAPI router + endpoint handlers
│   ├── models.py              ← pydantic Request/Response models
│   ├── pipeline_c.py          ← Pipeline protocol + Mock + DeepFM impls
│   ├── fixtures/
│   │   └── mock_recommendations.json
│   ├── tests/
│   │   ├── test_api.py
│   │   └── test_pipeline.py
│   └── README.md              ← run instructions
├── frontend/
│   ├── pyproject.toml         ← streamlit + httpx
│   ├── app.py                 ← main Streamlit entry
│   ├── api_client.py          ← backend HTTP client
│   ├── components.py          ← card + input + header components
│   ├── styles.css             ← custom CSS for design tokens
│   └── README.md              ← run instructions
├── e2e_smoke.sh               ← boot backend + curl 3 scenarios
└── README.md                  ← orchestration: how to run both sides
```

## Run instructions (target state)

```bash
# Terminal 1 — backend
cd app/backend
pip install -e .
uvicorn main:app --reload --port 8000   # mock mode by default

# Terminal 2 — frontend
cd app/frontend
pip install -e .
BACKEND_URL=http://localhost:8000 streamlit run app.py

# Tomorrow morning — swap to real model
PIPELINE=deepfm uvicorn main:app --port 8000  # loads deepfm_final_v2.pt
```

## Acceptance criteria

- [ ] Backend `/api/health` returns 200 with `model_loaded: true|false`
- [ ] Backend `/api/recommend` mock mode returns ≥3 valid candidates within 50ms
- [ ] Backend `/api/recommend` deepfm mode returns ≥3 valid candidates within 200ms p95
- [ ] Frontend boots on `streamlit run app.py` and shows top bar + 3 cards on load
- [ ] User can switch demo users via dropdown — cards refresh
- [ ] User can type query + send — cards refresh with mode=`query_chat`
- [ ] Custom CSS approximates Figma peach.500 top bar + Inter font
- [ ] `bash e2e_smoke.sh` passes 3 scenarios green
- [ ] Both backend and frontend have README with copy-pasteable run commands

## What's NOT in scope (v0.1)

- F1.1 Restaurant Detail Overlay (bottom sheet)
- F2 Trip Plan (day tabs)
- LLM agent layer (intent extraction, AI Overview generation) — query is passed through to model as-is
- Authentication / user accounts
- Real Yelp photos (use placeholder color block per PRD `card.thumb.placeholder = #DCDDE8`)
- Mobile-only interactions (swipe, pull-to-refresh) — desktop browser only
