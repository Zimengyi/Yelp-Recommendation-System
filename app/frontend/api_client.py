"""HTTP client for the Taste hunter backend (`POST /api/recommend`,
`GET /api/users/sample`, `GET /api/health`).

All response shapes follow `app/shared/API_CONTRACT.md`. Returns plain dicts —
the contract is documented + stable, and a Streamlit demo doesn't need
pydantic gymnastics.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 15.0


def _backend_url() -> str:
    return os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


class BackendError(RuntimeError):
    """Raised when the backend returns 4xx/5xx or is unreachable."""

    def __init__(self, message: str, *, status_code: int | None = None,
                 payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{_backend_url()}{path}"
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise BackendError(
            f"cannot reach backend at {url}: {exc}",
            status_code=None,
        ) from exc

    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except Exception:
            payload = {"detail": resp.text}
        raise BackendError(
            f"backend {method} {path} → {resp.status_code}: "
            f"{payload.get('error') or payload.get('detail') or 'unknown'}",
            status_code=resp.status_code,
            payload=payload,
        )

    return resp.json()


def get_health() -> dict[str, Any]:
    """GET /api/health → {status, model_loaded, model_version, uptime_seconds, device}"""
    return _request("GET", "/api/health")


def sample_users(n: int = 10, city: str | None = None) -> list[dict[str, Any]]:
    """GET /api/users/sample → list of user dicts (with `user_id`, `label`, ...)."""
    params: dict[str, Any] = {"n": n}
    if city:
        params["city"] = city
    payload = _request("GET", "/api/users/sample", params=params)
    return payload.get("users", [])


def recommend(
    user_id: str,
    query: str | None = None,
    target_city: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """POST /api/recommend → {user_id, target_city, mode, recommendations[], debug, ts}.

    `query=None` → S0 homepage_push; non-empty `query` → S2 query_chat.
    """
    body = {
        "user_id": user_id,
        "query": query if query else None,
        "target_city": target_city,
        "top_k": top_k,
    }
    return _request("POST", "/api/recommend", json=body)
