"""Recommendation pipelines for the Taste Hunter demo backend.

The production target is Pipeline C (hard filter + DeepFM ranker). For the
class demo, this module first provides a deterministic data-backed mock that
uses the real Yelp subset so the frontend can be exercised end to end before
model-serving glue is finished.
"""
from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

try:
    from .models import Candidate
except ImportError:
    from models import Candidate


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data import build_encoders

CLEANED_DIR = REPO_ROOT / "data" / "cleaned"
FEATURES_DIR = REPO_ROOT / "data" / "features"


class PipelineC(Protocol):
    """Minimal recommend interface used by the FastAPI layer."""

    @property
    def model_version(self) -> str:
        ...

    @property
    def model_loaded(self) -> bool:
        ...

    def sample_users(self, n: int = 10, city: str | None = None) -> list[dict]:
        ...

    def recommend(
        self,
        user_id: str,
        query: str | None,
        target_city: str | None,
        top_k: int,
    ) -> tuple[list[Candidate], dict]:
        ...


class MockPipeline:
    """Fast, deterministic recommendations from the real Yelp feature tables."""

    model_version = "mock_real_yelp_v0.1"
    model_loaded = True

    _QUERY_CATEGORY_MAP = {
        "spicy": ["Mexican", "Thai", "Indian", "Korean", "Szechuan"],
        "辣": ["Mexican", "Thai", "Indian", "Korean", "Szechuan"],
        "mexican": ["Mexican", "Tacos"],
        "pizza": ["Pizza", "Italian"],
        "coffee": ["Coffee & Tea", "Cafes", "Bakeries"],
        "咖啡": ["Coffee & Tea", "Cafes", "Bakeries"],
        "breakfast": ["Breakfast & Brunch", "Coffee & Tea", "Cafes", "Bakeries"],
        "brunch": ["Breakfast & Brunch", "Cafes", "American"],
        "sandwich": ["Sandwiches", "Delis"],
        "sandwiches": ["Sandwiches", "Delis"],
        "sushi": ["Sushi Bars", "Japanese"],
        "寿司": ["Sushi Bars", "Japanese"],
        "japanese": ["Japanese", "Sushi Bars", "Ramen"],
        "日料": ["Sushi Bars", "Japanese"],
        "seafood": ["Seafood"],
        "bar": ["Bars", "Cocktail Bars", "Nightlife"],
        "酒": ["Bars", "Cocktail Bars", "Nightlife"],
    }

    def __init__(self) -> None:
        business_path = CLEANED_DIR / "restaurants_open.parquet"
        user_path = FEATURES_DIR / "user_features.parquet"
        if not business_path.exists():
            raise FileNotFoundError(f"Missing {business_path}")
        if not user_path.exists():
            raise FileNotFoundError(f"Missing {user_path}")

        businesses = pd.read_parquet(business_path)
        users = pd.read_parquet(user_path)

        self.businesses = businesses.rename(
            columns={"latitude": "lat", "longitude": "lon", "stars": "rating"}
        )
        self.businesses["price_level"] = self.businesses["attributes"].map(
            _extract_price_level
        )
        self.businesses["primary_category"] = self.businesses["categories"].map(
            _primary_category
        )
        self.businesses["category_list"] = self.businesses["categories"].map(
            _category_list
        )
        review_log = self.businesses["review_count"].clip(lower=1).map(math.log1p)
        self.businesses["_base_score"] = (
            self.businesses["rating"].astype(float) / 5.0 * 0.68
            + (review_log / review_log.max()) * 0.32
        )
        self.users = users[users["user_id"] != "<NEW_USER>"].copy()

    def sample_users(self, n: int = 10, city: str | None = None) -> list[dict]:
        # The feature table does not store dominant city, so return stable demo
        # users with enough review history and let the dropdown label say mixed.
        users = self.users.sort_values("review_count_log", ascending=False).head(
            max(1, min(n, 20))
        )
        dominant_city = city or "Philadelphia"
        return [
            {
                "user_id": row.user_id,
                "review_count": int(round(math.expm1(row.review_count_log))),
                "dominant_city": dominant_city,
                "avg_rating_given": round(float(row.avg_rating_given) * 5.0, 2),
                "label": (
                    f"Active {dominant_city} user "
                    f"({int(round(math.expm1(row.review_count_log)))} reviews, "
                    f"star {round(float(row.avg_rating_given) * 5.0, 2)} avg)"
                ),
            }
            for row in users.itertuples(index=False)
        ]

    def recommend(
        self,
        user_id: str,
        query: str | None,
        target_city: str | None,
        top_k: int,
    ) -> tuple[list[Candidate], dict]:
        started = time.perf_counter()
        city = target_city or "Philadelphia"
        mode = "query_chat" if query else "homepage_push"
        intent = self._parse_query_intent(query)
        query_categories = intent["strict_categories"] or intent["categories"]
        max_price = intent["max_price"]

        pool = self.businesses[self.businesses["city"].str.lower() == city.lower()].copy()
        filter_passes = ["same_city"]

        if query_categories:
            matched = pool[pool["categories"].map(lambda cats: _matches_any(cats, query_categories))]
            if not matched.empty:
                pool = matched
                filter_passes.append("query_category")

        if max_price is not None:
            priced = pool[(pool["price_level"] > 0) & (pool["price_level"] <= max_price)]
            if not priced.empty:
                pool = priced
                filter_passes.append(f"price_lte_{max_price}")

        if pool.empty:
            city = "Philadelphia"
            pool = self.businesses[self.businesses["city"] == city].copy()

        pool = pool.copy()
        pool["score_tmp"] = pool["_base_score"]
        if query_categories:
            pool["score_tmp"] += pool["categories"].map(
                lambda cats: 0.08 if _matches_any(cats, query_categories) else 0.0
            )
        if max_price is not None:
            pool["score_tmp"] += pool["price_level"].map(
                lambda p: 0.06 if 0 < int(p) <= max_price else -0.12
            )
        pool_size_before_rank = int(len(pool))
        pool = pool.sort_values(["score_tmp", "review_count"], ascending=False).head(top_k)

        recommendations = [
            self._to_candidate(row, rank=i + 1, filter_passes=filter_passes)
            for i, row in enumerate(pool.itertuples(index=False))
        ]
        debug = {
            "filter_pool_size": pool_size_before_rank,
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "model_version": self.model_version,
            "pipeline": "mock (real Yelp data, hard-filter shaped)",
            "target_city": city,
            "mode": mode,
        }
        return recommendations, debug

    def _categories_from_query(self, query: str | None) -> list[str]:
        if not query:
            return []
        lowered = query.lower()
        out: list[str] = []
        for key, categories in self._QUERY_CATEGORY_MAP.items():
            if key.lower() in lowered:
                out.extend(categories)
        return sorted(set(out))

    def _parse_query_intent(self, query: str | None) -> dict:
        return {
            "categories": self._categories_from_query(query),
            "strict_categories": _strict_categories_from_query(query),
            "max_price": _max_price_from_query(query),
        }

    def _to_candidate(self, row, rank: int, filter_passes: list[str]) -> Candidate:
        categories = row.category_list[:5] if row.category_list else []
        score = float(row.score_tmp)
        deepfm_score = float(getattr(row, "deepfm_score", score))
        return Candidate(
            rank=rank,
            business_id=row.business_id,
            name=row.name,
            rating=float(row.rating),
            review_count=int(row.review_count),
            categories=categories,
            price_level=int(row.price_level),
            address=_format_address(row),
            lat=float(row.lat),
            lon=float(row.lon),
            photo_url=None,
            score=round(score, 4),
            reason_chip=_reason_chip(row, rank),
            reason_long=_reason_long(row),
            deepfm_score=round(deepfm_score, 4),
            filter_passes=filter_passes,
        )


class DeepFMV2(nn.Module):
    """Final notebook DeepFM v2 architecture with ColBERT-light item text input."""

    def __init__(
        self,
        n_users: int,
        n_items: int,
        emb_dim: int = 32,
        user_num_dim: int = 6,
        user_cuisine_dim: int = 50,
        item_num_dim: int = 7,
        item_cat_dim: int = 50,
        item_text_dim: int = 32,
        dnn_hidden: tuple[int, ...] = (256, 128, 64),
        dropout: float = 0.1,
    ):
        super().__init__()
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)
        self.user_num_proj = nn.Linear(user_num_dim, emb_dim)
        self.item_num_proj = nn.Linear(item_num_dim, emb_dim)
        self.item_text_proj = nn.Linear(item_text_dim, emb_dim)

        feat_dim_linear = user_num_dim + item_num_dim + user_cuisine_dim + item_cat_dim + item_text_dim
        self.linear_features = nn.Linear(feat_dim_linear, 1)
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        dnn_input_dim = emb_dim * 5 + user_cuisine_dim + item_cat_dim + item_text_dim
        layers: list[nn.Module] = []
        prev = dnn_input_dim
        for h in dnn_hidden:
            layers.extend([nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)])
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.dnn = nn.Sequential(*layers)

    def forward(
        self,
        user_idx: torch.Tensor,
        item_idx: torch.Tensor,
        user_num: torch.Tensor,
        user_cuisine: torch.Tensor,
        item_num: torch.Tensor,
        item_cat: torch.Tensor,
        item_text: torch.Tensor,
    ) -> torch.Tensor:
        u_emb = self.user_emb(user_idx)
        i_emb = self.item_emb(item_idx)
        un_emb = self.user_num_proj(user_num)
        in_emb = self.item_num_proj(item_num)
        it_emb = self.item_text_proj(item_text)

        feat_concat = torch.cat([user_num, item_num, user_cuisine, item_cat, item_text], dim=-1)
        order1 = self.linear_features(feat_concat).squeeze(-1)
        bu = self.user_bias(user_idx).squeeze(-1)
        bi = self.item_bias(item_idx).squeeze(-1)

        embs = torch.stack([u_emb, i_emb, un_emb, in_emb, it_emb], dim=1)
        order2 = 0.5 * ((embs.sum(dim=1) ** 2) - (embs ** 2).sum(dim=1)).sum(dim=-1)

        dnn_input = torch.cat([u_emb, i_emb, un_emb, in_emb, it_emb, user_cuisine, item_cat, item_text], dim=-1)
        dnn_output = self.dnn(dnn_input).squeeze(-1)
        return torch.sigmoid(order1 + order2 + dnn_output + bu + bi + self.global_bias)


class DeepFMPipeline(MockPipeline):
    """Pipeline C deployment: hard-filter retrieval + final DeepFM v2 reranker."""

    model_version = "deepfm_final_v2"

    def __init__(self) -> None:
        super().__init__()
        self.device = torch.device("cpu")
        self.user_features = pd.read_parquet(FEATURES_DIR / "user_features.parquet")
        self.item_features = pd.read_parquet(FEATURES_DIR / "item_features.parquet")
        self.user_encoder, self.item_encoder = build_encoders(self.user_features, self.item_features)
        self._build_feature_tensors()
        self.model = DeepFMV2(
            n_users=len(self.user_encoder),
            n_items=len(self.item_encoder),
            emb_dim=32,
            dropout=0.1,
        ).to(self.device)
        state = torch.load(REPO_ROOT / "models" / "deepfm_final_v2.pt", map_location=self.device)
        self.model.load_state_dict(state)
        self.model.eval()

    @property
    def model_loaded(self) -> bool:
        return True

    def recommend(
        self,
        user_id: str,
        query: str | None,
        target_city: str | None,
        top_k: int,
    ) -> tuple[list[Candidate], dict]:
        started = time.perf_counter()
        city = target_city or "Philadelphia"
        mode = "query_chat" if query else "homepage_push"
        intent = self._parse_query_intent(query)
        query_categories = intent["strict_categories"] or intent["categories"]
        max_price = intent["max_price"]

        pool = self.businesses[self.businesses["city"].str.lower() == city.lower()].copy()
        filter_passes = ["same_city"]
        if query_categories:
            matched = pool[pool["categories"].map(lambda cats: _matches_any(cats, query_categories))]
            if not matched.empty:
                pool = matched
                filter_passes.append("query_category")

        if max_price is not None:
            priced = pool[(pool["price_level"] > 0) & (pool["price_level"] <= max_price)]
            if not priced.empty:
                pool = priced
                filter_passes.append(f"price_lte_{max_price}")

        if pool.empty:
            city = "Philadelphia"
            pool = self.businesses[self.businesses["city"] == city].copy()

        pool = pool.copy()
        recall_k = max(top_k * 25, 120)
        pool["retrieval_score"] = pool["_base_score"]
        if query_categories:
            pool["retrieval_score"] += pool["categories"].map(
                lambda cats: 0.12 if _matches_any(cats, query_categories) else 0.0
            )
        if max_price is not None:
            pool["retrieval_score"] += pool["price_level"].map(
                lambda p: 0.08 if 0 < int(p) <= max_price else -0.20
            )
        pool = pool.sort_values(["retrieval_score", "review_count"], ascending=False).head(recall_k).copy()
        pool_size_before_rank = int(len(pool))

        deepfm_scores = self._score_deepfm(user_id, pool["business_id"].tolist())
        pool["deepfm_score"] = deepfm_scores
        pool["score_tmp"] = (
            pool["deepfm_score"] * 0.72
            + pool["_base_score"] * 0.22
            + pool["retrieval_score"] * 0.06
        )
        if max_price is not None:
            pool["score_tmp"] += pool["price_level"].map(
                lambda p: 0.04 if 0 < int(p) <= max_price else -0.30
            )
        pool = pool.sort_values(["score_tmp", "review_count"], ascending=False).head(top_k)

        recommendations = [
            self._to_candidate(row, rank=i + 1, filter_passes=filter_passes)
            for i, row in enumerate(pool.itertuples(index=False))
        ]
        debug = {
            "filter_pool_size": pool_size_before_rank,
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "model_version": self.model_version,
            "pipeline": "Pipeline C: hard filter retrieval + DeepFM v2 rerank",
            "target_city": city,
            "mode": mode,
        }
        return recommendations, debug

    def _build_feature_tensors(self) -> None:
        n_users = len(self.user_encoder)
        n_items = len(self.item_encoder)
        self.user_num = np.zeros((n_users, 6), dtype=np.float32)
        self.user_cuisine = np.zeros((n_users, 50), dtype=np.float32)
        self.item_num = np.zeros((n_items, 7), dtype=np.float32)
        self.item_cat = np.zeros((n_items, 50), dtype=np.float32)
        self.item_text = np.zeros((n_items, 32), dtype=np.float32)

        for row in self.user_features.itertuples(index=False):
            uidx = self.user_encoder.encode(row.user_id)
            self.user_num[uidx] = [
                row.avg_rating_given,
                row.review_count_log,
                row.days_active,
                row.elite_flag,
                row.mean_distance_traveled,
                row.price_tolerance_avg,
            ]
            emb = row.fav_cuisine_emb
            if isinstance(emb, list) and len(emb) == 50:
                self.user_cuisine[uidx] = np.asarray(emb, dtype=np.float32)

        for row in self.item_features.itertuples(index=False):
            iidx = self.item_encoder.encode(row.business_id)
            self.item_num[iidx] = [
                row.avg_rating,
                row.review_count_log,
                row.price_level,
                row.is_open,
                row.has_outdoor_seating,
                row.photo_count_log,
                row.city_id,
            ]
            cat = row.categories_multi_hot
            if isinstance(cat, list) and len(cat) == 50:
                self.item_cat[iidx] = np.asarray(cat, dtype=np.float32)
            text = row.item_text_emb_pca32
            if isinstance(text, list) and len(text) == 32:
                self.item_text[iidx] = np.asarray(text, dtype=np.float32)

        self.user_num_t = torch.from_numpy(self.user_num).to(self.device)
        self.user_cuisine_t = torch.from_numpy(self.user_cuisine).to(self.device)
        self.item_num_t = torch.from_numpy(self.item_num).to(self.device)
        self.item_cat_t = torch.from_numpy(self.item_cat).to(self.device)
        self.item_text_t = torch.from_numpy(self.item_text).to(self.device)

    def _score_deepfm(self, user_id: str, business_ids: list[str]) -> np.ndarray:
        if not business_ids:
            return np.array([], dtype=np.float32)
        uidx = self.user_encoder.encode(user_id)
        item_idx = np.array([self.item_encoder.encode(bid) for bid in business_ids], dtype=np.int64)
        user_idx = np.full(len(item_idx), uidx, dtype=np.int64)
        u_t = torch.from_numpy(user_idx).to(self.device)
        i_t = torch.from_numpy(item_idx).to(self.device)
        with torch.no_grad():
            pred = self.model(
                u_t,
                i_t,
                user_num=self.user_num_t[u_t],
                user_cuisine=self.user_cuisine_t[u_t],
                item_num=self.item_num_t[i_t],
                item_cat=self.item_cat_t[i_t],
                item_text=self.item_text_t[i_t],
            )
        return pred.cpu().numpy()


def _category_list(categories: str | None) -> list[str]:
    if not categories:
        return []
    return [c.strip() for c in str(categories).split(",") if c.strip()]


def _primary_category(categories: str | None) -> str:
    cats = [c for c in _category_list(categories) if c.lower() != "restaurants"]
    return cats[0] if cats else "Restaurant"


def _matches_any(categories: str | None, needles: list[str]) -> bool:
    cats = (categories or "").lower()
    return any(n.lower() in cats for n in needles)


def _strict_categories_from_query(query: str | None) -> list[str]:
    if not query:
        return []
    lowered = query.lower()
    if "sushi" in lowered or "寿司" in lowered:
        return ["Sushi Bars"]
    return []


def _max_price_from_query(query: str | None) -> int | None:
    if not query:
        return None
    lowered = query.lower()
    if any(token in lowered for token in ("very cheap", "super cheap", "under 15", "15以下", "人均15", "一美元", "$ only")):
        return 1
    if any(token in lowered for token in ("cheap", "budget", "affordable", "inexpensive", "便宜", "平价", "实惠", "人均", "以下", "under")):
        return 2
    match = re.search(r"(?:under|below|less than|人均|低于|小于)\s*\$?\s*(\d+)", lowered)
    if match:
        amount = int(match.group(1))
        if amount <= 15:
            return 1
        if amount <= 35:
            return 2
        if amount <= 60:
            return 3
        return 4
    if "$$$$" in lowered or any(token in lowered for token in ("fancy", "高端", "贵", "仪式感")):
        return None
    if "$$$" in lowered:
        return 3
    if "$$" in lowered:
        return 2
    if "$" in lowered:
        return 1
    return None


def _extract_price_level(attributes: dict | None) -> int:
    if not isinstance(attributes, dict):
        return 0
    raw = attributes.get("RestaurantsPriceRange2")
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def _format_address(row) -> str:
    pieces = [getattr(row, "address", ""), getattr(row, "city", ""), getattr(row, "state", "")]
    return ", ".join(str(p) for p in pieces if p)


def _reason_long(row) -> str:
    category = row.primary_category or "restaurant"
    price = "$" * int(row.price_level) if int(row.price_level) > 0 else "price unknown"
    deepfm = getattr(row, "deepfm_score", None)
    model_note = f" DeepFM score {float(deepfm):.3f}." if deepfm is not None else ""
    return f"{category} pick with {row.rating:.1f} stars, {row.review_count:,} reviews, {price}.{model_note}"


def _reason_chip(row, rank: int) -> str:
    price = "$" * int(row.price_level) if int(row.price_level) > 0 else "?"
    return f"{price} · DeepFM #{rank} · {row.city}"
