"""Uvicorn entrypoint for the Taste Hunter FastAPI backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .api import router
except ImportError:
    from api import router


app = FastAPI(title="Taste Hunter Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "taste-hunter-backend"}
