"""Pydantic request/response models for the Taste Hunter API.

Schema is frozen by ``app/shared/API_CONTRACT.md`` v0.1 (2026-05-09).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    user_id: str
    query: Optional[str] = None
    target_city: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=20)


class Candidate(BaseModel):
    rank: int
    business_id: str
    name: str
    rating: float
    review_count: int
    categories: list[str]
    price_level: int
    address: str
    lat: float
    lon: float
    photo_url: Optional[str] = None
    score: float
    reason_chip: str
    reason_long: str
    deepfm_score: float
    filter_passes: list[str]


class DebugInfo(BaseModel):
    filter_pool_size: int
    latency_ms: float
    model_version: str
    pipeline: str


class RecommendResponse(BaseModel):
    user_id: str
    target_city: str
    mode: Literal["homepage_push", "query_chat"]
    recommendations: list[Candidate]
    debug: DebugInfo
    ts: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    model_version: str
    uptime_seconds: float
    device: str


class UserSampleEntry(BaseModel):
    user_id: str
    review_count: int
    dominant_city: str
    avg_rating_given: float
    label: str


class UserSampleResponse(BaseModel):
    users: list[UserSampleEntry]


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str
