"""FastAPI routes for the Taste Hunter demo backend."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

try:
    from .models import (
        HealthResponse,
        RecommendRequest,
        RecommendResponse,
        UserSampleResponse,
    )
    from .pipeline_c import DeepFMPipeline, MockPipeline, PipelineC
except ImportError:
    from models import (
        HealthResponse,
        RecommendRequest,
        RecommendResponse,
        UserSampleResponse,
    )
    from pipeline_c import DeepFMPipeline, MockPipeline, PipelineC


router = APIRouter(prefix="/api")
_STARTED_AT = time.perf_counter()
_PIPELINE: PipelineC | None = None


def get_pipeline() -> PipelineC:
    global _PIPELINE
    if _PIPELINE is None:
        pipeline_name = os.environ.get("PIPELINE", "deepfm").lower()
        if pipeline_name == "deepfm":
            _PIPELINE = DeepFMPipeline()
        else:
            _PIPELINE = MockPipeline()
    return _PIPELINE


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    pipeline = get_pipeline()
    return HealthResponse(
        status="ok",
        model_loaded=pipeline.model_loaded,
        model_version=pipeline.model_version,
        uptime_seconds=round(time.perf_counter() - _STARTED_AT, 3),
        device="cpu",
    )


@router.get("/users/sample", response_model=UserSampleResponse)
def sample_users(n: int = 5, city: Optional[str] = None) -> UserSampleResponse:
    n = max(1, min(n, 20))
    return UserSampleResponse(users=get_pipeline().sample_users(n=n, city=city))


@router.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    recommendations, debug = get_pipeline().recommend(
        user_id=req.user_id,
        query=req.query,
        target_city=req.target_city,
        top_k=req.top_k,
    )
    return RecommendResponse(
        user_id=req.user_id,
        target_city=debug.get("target_city") or req.target_city or "Philadelphia",
        mode=debug.get("mode") or ("query_chat" if req.query else "homepage_push"),
        recommendations=recommendations,
        debug={
            "filter_pool_size": debug["filter_pool_size"],
            "latency_ms": debug["latency_ms"],
            "model_version": debug["model_version"],
            "pipeline": debug["pipeline"],
        },
        ts=datetime.now(timezone.utc).isoformat(),
    )
