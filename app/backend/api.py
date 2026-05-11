"""FastAPI routes for the Taste Hunter demo backend."""
from __future__ import annotations

import os
import math
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

try:
    from .models import (
        HealthResponse,
        RecommendRequest,
        RecommendResponse,
        TripDayPlan,
        TripPeriodPlan,
        TripPlanDebug,
        TripPlanRequest,
        TripPlanResponse,
        UserSampleResponse,
    )
    from .pipeline_c import DeepFMPipeline, MockPipeline, PipelineC
except ImportError:
    from models import (
        HealthResponse,
        RecommendRequest,
        RecommendResponse,
        TripDayPlan,
        TripPeriodPlan,
        TripPlanDebug,
        TripPlanRequest,
        TripPlanResponse,
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


@router.post("/trip/plan", response_model=TripPlanResponse)
def plan_trip(req: TripPlanRequest) -> TripPlanResponse:
    started = time.perf_counter()
    pipeline = get_pipeline()
    city = _normalize_city(_city_from_query(req.query) or req.destination_city)
    activity_days = _activity_template(city, req.days)
    days: list[TripDayPlan] = []
    diversity_scores: list[float] = []

    for day_index, periods in enumerate(activity_days, start=1):
        period_plans: list[TripPeriodPlan] = []
        day_seen_cuisines: set[str] = set()
        for period, label, activity, food_hint in periods:
            query = " ".join(part for part in [req.query, food_hint] if part).strip()
            recommendations, _ = pipeline.recommend(
                user_id=req.user_id,
                query=query,
                target_city=city,
                top_k=20,
            )
            selected = _mmr_select(
                recommendations,
                k=req.candidates_per_period,
                lambda_=0.65,
                day_seen_cuisines=day_seen_cuisines,
            )
            for candidate in selected:
                cuisine = _primary_display_cuisine(candidate.categories)
                if cuisine:
                    day_seen_cuisines.add(cuisine)
            diversity = _candidate_diversity(selected)
            diversity_scores.append(diversity)
            period_plans.append(
                TripPeriodPlan(
                    period=period,
                    label=label,
                    activity=activity,
                    candidates=selected,
                    diversity_score=round(diversity, 4),
                )
            )
        days.append(
            TripDayPlan(
                day_index=day_index,
                title=f"DAY {day_index}",
                periods=period_plans,
            )
        )

    mean_diversity = sum(diversity_scores) / max(len(diversity_scores), 1)
    return TripPlanResponse(
        user_id=req.user_id,
        destination_city=city,
        days=days,
        debug=TripPlanDebug(
            latency_ms=(time.perf_counter() - started) * 1000.0,
            model_version=pipeline.model_version,
            pipeline="S6 trip plan: intent hard-filter + DeepFM v2 + MMR top-3",
            mmr_lambda=0.65,
            mean_period_diversity=round(mean_diversity, 4),
        ),
        ts=datetime.now(timezone.utc).isoformat(),
    )


def _normalize_city(city: str) -> str:
    lookup = {
        "la": "Los Angeles",
        "l.a.": "Los Angeles",
        "los angeles": "Los Angeles",
        "洛杉矶": "Los Angeles",
        "philly": "Philadelphia",
        "philadelphia": "Philadelphia",
        "tampa": "Tampa",
        "tucson": "Tucson",
    }
    return lookup.get(city.strip().lower(), "Los Angeles")


def _city_from_query(query: str | None) -> str | None:
    if not query:
        return None
    text = query.lower()
    if "los angeles" in text or " l.a." in text or " la " in f" {text} " or "洛杉矶" in query:
        return "Los Angeles"
    if "philadelphia" in text or "philly" in text or "费城" in query:
        return "Philadelphia"
    if "tampa" in text:
        return "Tampa"
    if "tucson" in text:
        return "Tucson"
    return None


def _activity_template(city: str, days: int) -> list[list[tuple[str, str, str, str]]]:
    templates = {
        "Los Angeles": [
            [
                ("morning", "早晨", "Griffith Observatory 周边看城市天际线，早上先轻量走一段。", "coffee brunch"),
                ("lunch", "中午", "转去 Silver Lake / Los Feliz，控制移动距离。", "sandwiches lunch"),
                ("evening", "晚上", "Arts District 和 Little Tokyo 附近收尾。", "sushi japanese dinner"),
            ],
            [
                ("morning", "早晨", "Santa Monica 海边散步，避开午后拥挤。", "coffee breakfast"),
                ("lunch", "中午", "Venice / Abbot Kinney 一带轻松逛。", "seafood lunch"),
                ("evening", "晚上", "West Hollywood 或 Fairfax 晚餐，适合夜间活动。", "bar dinner"),
            ],
            [
                ("morning", "早晨", "Getty Center 或 Beverly Hills 附近慢节奏开始。", "breakfast brunch"),
                ("lunch", "中午", "Koreatown / Mid-City 找一顿高性价比餐。", "korean lunch"),
                ("evening", "晚上", "Downtown LA 夜景后吃最后一餐。", "dinner"),
            ],
        ],
        "Philadelphia": [
            [
                ("morning", "早晨", "Old City 历史街区散步，顺路看 Independence Hall。", "coffee brunch"),
                ("lunch", "中午", "沿 Walnut Street 和 Washington Square 轻松逛一圈。", "sandwiches lunch"),
                ("evening", "晚上", "去 Rittenhouse Square 周边吃一顿收尾晚餐。", "dinner"),
            ],
            [
                ("morning", "早晨", "Philadelphia Museum of Art 和 Schuylkill River Trail。", "coffee brunch"),
                ("lunch", "中午", "Fairmount 一带慢走，避开过长绕路。", "pizza lunch"),
                ("evening", "晚上", "Fishtown / Northern Liberties 晚间小店和酒吧。", "bar dinner"),
            ],
            [
                ("morning", "早晨", "Reading Terminal Market 附近开始一天。", "breakfast brunch"),
                ("lunch", "中午", "Chinatown 和 Center City 之间短距离移动。", "sushi japanese lunch"),
                ("evening", "晚上", "Penn's Landing 河边散步后吃最后一餐。", "seafood dinner"),
            ],
        ],
        "Tampa": [
            [
                ("morning", "早晨", "Tampa Riverwalk 轻松散步。", "coffee brunch"),
                ("lunch", "中午", "Ybor City 历史街区和小店。", "sandwiches lunch"),
                ("evening", "晚上", "Water Street 周边晚餐。", "seafood dinner"),
            ]
        ],
        "Tucson": [
            [
                ("morning", "早晨", "Saguaro National Park 早间短线。", "coffee breakfast"),
                ("lunch", "中午", "Downtown Tucson 壁画和街区。", "mexican lunch"),
                ("evening", "晚上", "University / Fourth Avenue 晚餐。", "bar dinner"),
            ]
        ],
    }
    base = templates.get(city, templates["Los Angeles"])
    return [base[i % len(base)] for i in range(days)]


def _mmr_select(
    candidates,
    k: int,
    lambda_: float,
    day_seen_cuisines: set[str],
):
    remaining = list(candidates)
    selected = []
    while remaining and len(selected) < k:
        best_idx = 0
        best_score = -float("inf")
        for idx, candidate in enumerate(remaining):
            relevance = float(candidate.score)
            similarity = max((_candidate_similarity(candidate, item) for item in selected), default=0.0)
            cuisine = _primary_display_cuisine(candidate.categories)
            day_penalty = 0.08 if cuisine and cuisine in day_seen_cuisines else 0.0
            mmr_score = lambda_ * relevance - (1.0 - lambda_) * similarity - day_penalty
            if mmr_score > best_score:
                best_idx = idx
                best_score = mmr_score
        selected.append(remaining.pop(best_idx))
    return selected


def _candidate_similarity(a, b) -> float:
    a_vec = _candidate_tokens(a)
    b_vec = _candidate_tokens(b)
    if not a_vec or not b_vec:
        return 0.0
    overlap = len(a_vec & b_vec)
    return overlap / math.sqrt(len(a_vec) * len(b_vec))


def _candidate_tokens(candidate) -> set[str]:
    tokens = {f"price:{candidate.price_level}"}
    tokens.update(f"cat:{c.lower()}" for c in candidate.categories[:4])
    tokens.add(f"region:{round(candidate.lat, 2)}:{round(candidate.lon, 2)}")
    return tokens


def _candidate_diversity(candidates) -> float:
    cuisines = [_primary_display_cuisine(c.categories) for c in candidates]
    cuisines = [c for c in cuisines if c]
    if len(cuisines) <= 1:
        return 0.0
    return len(set(cuisines)) / len(cuisines)


def _primary_display_cuisine(categories: list[str]) -> str:
    ignored = {"restaurants", "food", "nightlife", "bars"}
    for category in categories:
        if category.lower() not in ignored:
            return category
    return categories[0] if categories else ""
