#!/usr/bin/env bash
# Taste hunter — frontend e2e smoke test.
#
# Boots the backend (mock pipeline) + the Streamlit frontend in the background,
# waits for both to come up, curls the Streamlit page, and greps for marker
# text. Exits 0 on success, non-zero on failure.
#
# Usage: bash e2e_smoke.sh
# Env:
#   BACKEND_PORT  default 8000
#   FRONTEND_PORT default 8501

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_ROOT="$REPO_ROOT/app"
LOG_DIR="$APP_ROOT/frontend/.smoke_logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Pick a Python that has streamlit + httpx installed. Order:
#   1. $PYTHON env var (explicit override)
#   2. yelp-arm64 conda env (project default)
#   3. python3 on PATH
auto_pick_python() {
    if [[ -n "${PYTHON:-}" ]]; then
        echo "$PYTHON"
        return
    fi
    local candidates=(
        "$HOME/miniforge3/envs/yelp-arm64/bin/python3"
        "$(command -v python3)"
    )
    for p in "${candidates[@]}"; do
        [[ -z "$p" ]] && continue
        if "$p" -c 'import streamlit, httpx' 2>/dev/null; then
            echo "$p"
            return
        fi
    done
    # Fall through — return python3 even if streamlit is missing, so we get a
    # clear error message later.
    command -v python3
}
PYTHON="$(auto_pick_python)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    local rc=$?
    echo
    echo "[smoke] cleanup …"
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
    [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null || true
    sleep 0.5
    [[ -n "$FRONTEND_PID" ]] && kill -9 "$FRONTEND_PID" 2>/dev/null || true
    [[ -n "$BACKEND_PID" ]]  && kill -9 "$BACKEND_PID"  2>/dev/null || true
    exit $rc
}
trap cleanup EXIT INT TERM

wait_for() {
    local label="$1" url="$2" timeout="${3:-30}"
    local start="$(date +%s)"
    while true; do
        if curl -sf -o /dev/null "$url"; then
            echo "[smoke] ✅ $label up at $url"
            return 0
        fi
        local now elapsed
        now="$(date +%s)"
        elapsed=$((now - start))
        if (( elapsed >= timeout )); then
            echo "[smoke] ❌ $label did not come up within ${timeout}s"
            return 1
        fi
        sleep 0.5
    done
}

echo "[smoke] repo:    $REPO_ROOT"
echo "[smoke] python:  $PYTHON"
echo "[smoke] backend: http://localhost:$BACKEND_PORT"
echo "[smoke] frontend: http://localhost:$FRONTEND_PORT"
echo

# ---- 1. Boot backend (mock pipeline) ----
if [[ ! -d "$APP_ROOT/backend" ]] || [[ ! -f "$APP_ROOT/backend/main.py" ]]; then
    echo "[smoke] ⚠️  backend not found at $APP_ROOT/backend — running frontend-only smoke"
    BACKEND_AVAILABLE=0
else
    BACKEND_AVAILABLE=1
    echo "[smoke] booting backend …"
    (
        cd "$APP_ROOT/backend"
        PIPELINE=mock "$PYTHON" -m uvicorn main:app --port "$BACKEND_PORT" --host 127.0.0.1
    ) >"$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "[smoke] backend pid=$BACKEND_PID, log=$BACKEND_LOG"

    if ! wait_for "backend /api/health" "http://localhost:$BACKEND_PORT/api/health" 30; then
        echo "[smoke] --- backend log tail ---"
        tail -n 40 "$BACKEND_LOG" || true
        exit 1
    fi
fi

# ---- 2. Boot frontend ----
echo "[smoke] booting Streamlit …"
(
    cd "$APP_ROOT/frontend"
    BACKEND_URL="http://localhost:$BACKEND_PORT" \
        "$PYTHON" -m streamlit run app.py \
        --server.headless true \
        --server.port "$FRONTEND_PORT" \
        --server.address 127.0.0.1 \
        --browser.gatherUsageStats false
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "[smoke] frontend pid=$FRONTEND_PID, log=$FRONTEND_LOG"

if ! wait_for "frontend root" "http://localhost:$FRONTEND_PORT/" 30; then
    echo "[smoke] --- frontend log tail ---"
    tail -n 60 "$FRONTEND_LOG" || true
    exit 1
fi

# ---- 3. Verify Streamlit serves index ----
echo "[smoke] curling http://localhost:$FRONTEND_PORT/ …"
if ! curl -sf "http://localhost:$FRONTEND_PORT/" | grep -qi "streamlit"; then
    echo "[smoke] ❌ streamlit page does not contain 'streamlit' marker"
    exit 1
fi
echo "[smoke] ✅ streamlit page served (markers OK)"

# Streamlit's index.html is a SPA shell — the page title is set client-side after
# bootstrap, so we cannot grep for "Taste hunter" in the raw HTML response.
# Instead verify Streamlit's healthz endpoint reports a healthy script.
if curl -sf "http://localhost:$FRONTEND_PORT/_stcore/health" | grep -qi "ok"; then
    echo "[smoke] ✅ streamlit core health OK"
else
    echo "[smoke] ⚠️  streamlit /_stcore/health did not return 'ok' (continuing)"
fi

# ---- 4. Backend smoke — exercise the core API endpoints in mock mode ----
if [[ "$BACKEND_AVAILABLE" == "1" ]]; then
    echo "[smoke] verifying /api/users/sample …"
    USERS_JSON="$(curl -sf "http://localhost:$BACKEND_PORT/api/users/sample?n=3")"
    echo "$USERS_JSON" | grep -q '"users"' || { echo "[smoke] ❌ /api/users/sample missing 'users'"; exit 1; }
    USER_ID="$(echo "$USERS_JSON" | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["users"][0]["user_id"])')"
    echo "[smoke] ✅ /api/users/sample → user_id=$USER_ID"

    echo "[smoke] verifying /api/recommend (homepage_push) …"
    REC_JSON="$(curl -sf -X POST "http://localhost:$BACKEND_PORT/api/recommend" \
        -H 'Content-Type: application/json' \
        -d "{\"user_id\":\"$USER_ID\",\"query\":null,\"top_k\":5}")"
    echo "$REC_JSON" | grep -q '"recommendations"' || { echo "[smoke] ❌ /api/recommend missing 'recommendations'"; exit 1; }
    echo "$REC_JSON" | grep -q '"homepage_push"' || { echo "[smoke] ❌ /api/recommend mode != homepage_push"; exit 1; }
    echo "[smoke] ✅ /api/recommend homepage_push OK"

    echo "[smoke] verifying /api/recommend (query_chat) …"
    REC2_JSON="$(curl -sf -X POST "http://localhost:$BACKEND_PORT/api/recommend" \
        -H 'Content-Type: application/json' \
        -d "{\"user_id\":\"$USER_ID\",\"query\":\"想吃辣的\",\"top_k\":5}")"
    echo "$REC2_JSON" | grep -q '"query_chat"' || { echo "[smoke] ❌ /api/recommend mode != query_chat"; exit 1; }
    echo "[smoke] ✅ /api/recommend query_chat OK"

    echo "[smoke] verifying /api/trip/plan (S6 trip + MMR) …"
    TRIP_JSON="$(curl -sf -X POST "http://localhost:$BACKEND_PORT/api/trip/plan" \
        -H 'Content-Type: application/json' \
        -d "{\"user_id\":\"$USER_ID\",\"query\":\"cheap\",\"destination_city\":\"Philadelphia\",\"days\":1,\"candidates_per_period\":3}")"
    echo "$TRIP_JSON" | grep -q '"days"' || { echo "[smoke] ❌ /api/trip/plan missing 'days'"; exit 1; }
    echo "$TRIP_JSON" | grep -q '"mean_period_diversity"' || { echo "[smoke] ❌ /api/trip/plan missing MMR diversity debug"; exit 1; }
    echo "[smoke] ✅ /api/trip/plan S6 OK"
fi

echo
echo "[smoke] 🎉 all checks passed"
