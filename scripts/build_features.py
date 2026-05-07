"""Phase 3 — Feature engineering pipeline.

Reads Phase 1 cleaned parquet + Phase 2 cuisine_vocab.json, computes the
26 features specified in PRD §3.3.3 v2.2, and outputs:

    data/features/user_features.parquet      — 8 user features × 359K users + <NEW_USER>
    data/features/item_features.parquet       — 9 item features × 9K restaurants
    data/features/region_clusters.json        — k-means cluster centers (k=8)
    data/features/feature_spec.json           — feature schema (input dim, types, sources)
    data/features/train_with_negatives.parquet — train positives + 1:4 same-city negatives

Context features (9 fields) are computed at batch-load time, NOT precomputed,
because they depend on the (review, business, user) triple. See
src/feature_context.py for the build_context() function.

Usage:
    python scripts/build_features.py

See docs/prd/PRD_v1_section3.3_Model_v2.md §3.3.3 + docs/recommender_training_explainer.md §2.5 for design.
"""

import json
import logging
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"

# constants
TODAY = pd.Timestamp("2026-05-06")
NEG_RATIO = 4
RANDOM_SEED = 42
REGION_K = 8
EMB_DIM_USER = 8
EMB_DIM_BIZ = 8
CUISINE_VOCAB_SIZE = 50  # from cuisine_vocab.json


def load_cuisine_vocab():
    path = FEATURES_DIR / "cuisine_vocab.json"
    with open(path) as f:
        v = json.load(f)
    return v["cuisines"]


# =============================================================================
# Phase 3.1 — User Features (8 fields: 5 direct + 3 aggregated)
# =============================================================================
def build_user_features(users: pd.DataFrame, reviews: pd.DataFrame, businesses: pd.DataFrame, cuisine_vocab: list[str]) -> pd.DataFrame:
    """Build per-user feature table (one row per user_id + 1 OOV row).

    See docs/recommender_training_explainer.md §2.5.2 for column semantics.
    """
    log.info("=" * 60)
    log.info("Phase 3.1 — User Features (8 features)")
    log.info("=" * 60)

    # ---- 5 direct features ----
    log.info("Computing 5 direct features (user_id / avg_rating_given / review_count_log / days_active / elite_flag)")
    out = pd.DataFrame()
    out["user_id"] = users["user_id"]
    out["avg_rating_given"] = users["average_stars"] / 5.0
    out["review_count_log"] = np.log1p(users["review_count"])
    yelping_since = pd.to_datetime(users["yelping_since"], errors="coerce")
    out["days_active"] = np.log1p((TODAY - yelping_since).dt.days.clip(lower=0))
    out["elite_flag"] = (
        users["elite"].fillna("").astype(str).str.strip().str.lower().ne("").astype(int)
    )

    # ---- 3 aggregated features ----
    log.info("Computing 3 aggregated features (mean_distance_traveled / fav_cuisine_emb / price_tolerance_avg)")

    # Build business lookup: business_id → (lat, lon, categories, price_level)
    biz_idx = businesses.set_index("business_id")
    biz_lat_lon = biz_idx[["latitude", "longitude"]].dropna()
    biz_categories = biz_idx["categories"].fillna("").to_dict()

    # Parse RestaurantsPriceRange2 from attributes dict per business
    def parse_price(attrs):
        if not isinstance(attrs, dict):
            return None
        v = attrs.get("RestaurantsPriceRange2")
        if v is None or str(v).strip().lower() in ("none", ""):
            return None
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return None

    biz_price = {bid: parse_price(attrs) for bid, attrs in biz_idx["attributes"].items()}

    # Group reviews by user_id
    log.info("  grouping reviews by user_id (this is the slow step)")
    user_biz_groups = reviews.groupby("user_id")["business_id"].agg(lambda x: list(set(x)))
    log.info("  done: %d users with restaurant reviews", len(user_biz_groups))

    cuisine_to_idx = {c: i for i, c in enumerate(cuisine_vocab)}

    # ---- 3.1.2 mean_distance_traveled (haversine pairwise; vectorized inline) ----
    log.info("Computing mean_distance_traveled (haversine pairwise mean per user)")

    def haversine_km_vectorized(lat1, lon1, lat2, lon2):
        """Vectorized haversine — works on numpy arrays. Avoids numba/haversine dep issues."""
        R = 6371.0
        lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    biz_lat_arr = biz_lat_lon["latitude"].to_dict()
    biz_lon_arr = biz_lat_lon["longitude"].to_dict()

    def compute_mean_dist(biz_ids):
        lats, lons = [], []
        for bid in biz_ids:
            if bid in biz_lat_arr:
                lats.append(biz_lat_arr[bid])
                lons.append(biz_lon_arr[bid])
        if len(lats) < 2:
            return 0.0
        # sample to bound runtime
        if len(lats) > 30:
            rng = np.random.default_rng(RANDOM_SEED)
            idxs = rng.choice(len(lats), 30, replace=False)
            lats = [lats[i] for i in idxs]
            lons = [lons[i] for i in idxs]
        lat_arr = np.array(lats)
        lon_arr = np.array(lons)
        # pairwise distances (upper triangle only)
        n = len(lat_arr)
        i, j = np.triu_indices(n, k=1)
        dists = haversine_km_vectorized(lat_arr[i], lon_arr[i], lat_arr[j], lon_arr[j])
        return float(np.log1p(np.mean(dists)))

    # ---- 3.1.3 fav_cuisine_emb (top-3 cuisine pooling over vocab) ----
    log.info("Computing fav_cuisine_emb (top-3 cuisine pooling)")

    def compute_fav_cuisine(biz_ids):
        cnt = Counter()
        for bid in biz_ids:
            cats = biz_categories.get(bid, "")
            for c in (x.strip() for x in cats.split(",")):
                if c in cuisine_to_idx:
                    cnt[c] += 1
        emb = np.zeros(len(cuisine_vocab), dtype=np.float32)
        for c, n in cnt.most_common(3):
            emb[cuisine_to_idx[c]] = n
        s = emb.sum()
        return (emb / s).tolist() if s > 0 else emb.tolist()

    # ---- 3.1.4 price_tolerance_avg ----
    log.info("Computing price_tolerance_avg (mean of price_level / 4)")

    def compute_price_tol(biz_ids):
        prices = [biz_price[bid] for bid in biz_ids if biz_price.get(bid) is not None]
        if not prices:
            return 0.5  # global midrange fallback
        return float(np.mean(prices) / 4.0)

    # Compute aggregations per user
    mean_dists, fav_cuisines, price_tols = [], [], []
    user_id_to_biz = user_biz_groups.to_dict()
    n = len(out)
    for i, uid in enumerate(out["user_id"].values):
        biz_ids = user_id_to_biz.get(uid, [])
        mean_dists.append(compute_mean_dist(biz_ids))
        fav_cuisines.append(compute_fav_cuisine(biz_ids))
        price_tols.append(compute_price_tol(biz_ids))
        if (i + 1) % 50_000 == 0:
            log.info("  processed %d / %d users", i + 1, n)
    out["mean_distance_traveled"] = mean_dists
    out["fav_cuisine_emb"] = fav_cuisines
    out["price_tolerance_avg"] = price_tols

    # Fill any NaN
    out["avg_rating_given"] = out["avg_rating_given"].fillna(0.76)  # global median ≈ 3.8 / 5
    out["days_active"] = out["days_active"].fillna(0.0)

    # Add OOV row for new Taste hunter users (see explainer §6.4)
    oov = pd.DataFrame([{
        "user_id": "<NEW_USER>",
        "avg_rating_given": 0.76,
        "review_count_log": 0.0,
        "days_active": 0.0,
        "elite_flag": 0,
        "mean_distance_traveled": 0.0,
        "fav_cuisine_emb": np.zeros(len(cuisine_vocab), dtype=np.float32).tolist(),
        "price_tolerance_avg": 0.5,
    }])
    out = pd.concat([out, oov], ignore_index=True)

    log.info("  → %d rows (%d real + 1 OOV)", len(out), len(out) - 1)
    return out


# =============================================================================
# Phase 3.2 — Item Features (9 fields)
# =============================================================================
def build_item_features(restaurants: pd.DataFrame, cuisine_vocab: list[str]) -> pd.DataFrame:
    """Build per-restaurant feature table (one row per business_id + 1 OOV row)."""
    log.info("=" * 60)
    log.info("Phase 3.2 — Item Features (9 features)")
    log.info("=" * 60)

    out = pd.DataFrame()
    out["business_id"] = restaurants["business_id"]

    # Bayesian smoothed avg_rating: r̃ = (C * mu_global + sum_r) / (C + n)
    C = 10  # prior strength
    mu_global = restaurants["stars"].mean()
    n = restaurants["review_count"]
    out["avg_rating"] = (C * mu_global + restaurants["stars"] * n) / (C + n) / 5.0  # normalize to [0,1]
    out["review_count_log"] = np.log1p(restaurants["review_count"])

    # Price level (1-4) from attributes.RestaurantsPriceRange2
    def parse_price(attrs):
        if not isinstance(attrs, dict):
            return 2  # midrange default
        v = attrs.get("RestaurantsPriceRange2")
        if v is None or str(v).strip().lower() in ("none", ""):
            return 2
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return 2

    out["price_level"] = restaurants["attributes"].apply(parse_price)
    out["is_open"] = restaurants["is_open"].astype(int)

    # has_outdoor_seating
    def parse_outdoor(attrs):
        if not isinstance(attrs, dict):
            return 0
        v = attrs.get("OutdoorSeating")
        if v is None:
            return 0
        return int(str(v).strip().lower() == "true")

    out["has_outdoor_seating"] = restaurants["attributes"].apply(parse_outdoor)

    # photo_count proxy — use review_count log (correlates with photo abundance);
    # photos.json (5GB) not downloaded, so this is a stand-in
    out["photo_count_log"] = np.log1p(restaurants["review_count"]).clip(upper=10)

    # categories_multi_hot over cuisine_vocab
    log.info("Building categories_multi_hot encoding over %d cuisines", len(cuisine_vocab))
    cuisine_to_idx = {c: i for i, c in enumerate(cuisine_vocab)}

    def encode_categories(cats_str):
        emb = np.zeros(len(cuisine_vocab), dtype=np.int8)
        if not isinstance(cats_str, str):
            return emb.tolist()
        for c in (x.strip() for x in cats_str.split(",")):
            if c in cuisine_to_idx:
                emb[cuisine_to_idx[c]] = 1
        return emb.tolist()

    out["categories_multi_hot"] = restaurants["categories"].apply(encode_categories)

    # city_id (categorical embedding key)
    out["city"] = restaurants["city"].str.strip()
    city_to_idx = {c: i + 1 for i, c in enumerate(sorted(out["city"].unique()))}
    city_to_idx["<UNK>"] = 0
    out["city_id"] = out["city"].map(city_to_idx).fillna(0).astype(int)

    out["lat"] = restaurants["latitude"]
    out["lon"] = restaurants["longitude"]

    # Add OOV row
    oov = pd.DataFrame([{
        "business_id": "<NEW_BUSINESS>",
        "avg_rating": mu_global / 5.0,
        "review_count_log": 0.0,
        "price_level": 2,
        "is_open": 1,
        "has_outdoor_seating": 0,
        "photo_count_log": 0.0,
        "categories_multi_hot": np.zeros(len(cuisine_vocab), dtype=np.int8).tolist(),
        "city": "<UNK>",
        "city_id": 0,
        "lat": 0.0,
        "lon": 0.0,
    }])
    out = pd.concat([out, oov], ignore_index=True)

    log.info("  → %d rows (%d real + 1 OOV)", len(out), len(out) - 1)
    log.info("  city_id mapping: %s", city_to_idx)
    return out, city_to_idx


# =============================================================================
# Phase 3.3 — Region clusters (k-means k=8 over Philadelphia + Tucson + Tampa)
# =============================================================================
def build_region_clusters(restaurants: pd.DataFrame) -> dict:
    """Compute k-means cluster centers per city for region_cluster_id context feature."""
    log.info("=" * 60)
    log.info("Phase 3.3 — Region clusters (k=%d per city)", REGION_K)
    log.info("=" * 60)

    from sklearn.cluster import KMeans

    clusters = {}
    for city in sorted(restaurants["city"].str.strip().unique()):
        if not city:
            continue
        sub = restaurants[restaurants["city"].str.strip() == city][["latitude", "longitude"]].dropna()
        if len(sub) < REGION_K:
            log.info("  %s has only %d points; skip k-means", city, len(sub))
            continue
        km = KMeans(n_clusters=REGION_K, n_init=10, random_state=RANDOM_SEED)
        km.fit(sub.values)
        clusters[city] = {
            "centers": km.cluster_centers_.tolist(),
            "n": len(sub),
            "inertia": float(km.inertia_),
        }
        log.info("  %s: %d points → k=%d, inertia=%.0f", city, len(sub), REGION_K, km.inertia_)

    return clusters


# =============================================================================
# Phase 3.4 — train_with_negatives.parquet (1:4 negative sampling)
# =============================================================================
def build_train_with_negatives(reviews_df: pd.DataFrame, restaurants: pd.DataFrame, ratio: int = NEG_RATIO):
    """For each train positive (rating ≥ 4), sample N negatives from same-city unvisited businesses."""
    log.info("=" * 60)
    log.info("Phase 3.4 — Train with negatives (1:%d sampling)", ratio)
    log.info("=" * 60)

    rng = np.random.default_rng(RANDOM_SEED)

    # Build city → biz_ids index
    biz_city = restaurants.set_index("business_id")["city"].to_dict()
    city_biz = {}
    for bid, c in biz_city.items():
        c = (c or "").strip()
        city_biz.setdefault(c, []).append(bid)
    for c in city_biz:
        city_biz[c] = np.array(city_biz[c])
    log.info("  built city → biz lookup for %d cities", len(city_biz))

    reviews_df = reviews_df.copy()
    reviews_df["city"] = reviews_df["business_id"].map(biz_city).fillna("").str.strip()
    reviews_df["label"] = (reviews_df["stars"] >= 4).astype(int)

    # Keep only positives for negative sampling
    positives = reviews_df[reviews_df["label"] == 1]
    log.info("  total positives: %d", len(positives))

    # User → set of visited biz_ids (for excluding from negatives)
    user_visited = reviews_df.groupby("user_id")["business_id"].agg(set).to_dict()
    log.info("  built user → visited businesses lookup")

    # Sample negatives
    out_rows = []
    for i, row in enumerate(positives.itertuples(index=False)):
        out_rows.append({
            "user_id": row.user_id,
            "business_id": row.business_id,
            "label": 1,
            "stars": row.stars,
            "date": row.date,
            "city": row.city,
        })
        # Sample negatives from same city, excluding visited
        if row.city not in city_biz:
            continue
        candidates = city_biz[row.city]
        visited = user_visited.get(row.user_id, set())
        attempts = 0
        sampled = []
        while len(sampled) < ratio and attempts < ratio * 10:
            picks = rng.choice(candidates, size=ratio * 2, replace=True)
            for bid in picks:
                if bid not in visited and bid != row.business_id:
                    sampled.append(bid)
                    if len(sampled) >= ratio:
                        break
            attempts += 1
        for bid in sampled:
            out_rows.append({
                "user_id": row.user_id,
                "business_id": bid,
                "label": 0,
                "stars": np.nan,
                "date": row.date,  # use positive's date for temporal context
                "city": row.city,
            })
        if (i + 1) % 50_000 == 0:
            log.info("  processed %d / %d positives", i + 1, len(positives))

    out = pd.DataFrame(out_rows)
    log.info("  → %d rows (%d positive + %d negative, ratio %.2f)",
             len(out),
             (out["label"] == 1).sum(),
             (out["label"] == 0).sum(),
             (out["label"] == 0).sum() / max((out["label"] == 1).sum(), 1))
    return out


# =============================================================================
# Phase 3.5 — feature_spec.json
# =============================================================================
def build_feature_spec(cuisine_vocab: list[str], city_map: dict, n_users: int, n_businesses: int):
    """Build the feature_spec.json that all training scripts read for input layer config."""
    spec = {
        "version": "v3.0_2026-05-06",
        "anchor": "PRD §3.3.3 v2.2 (26 features: User 8 + Item 9 + Context 9)",
        "n_users": n_users,
        "n_businesses": n_businesses,
        "cuisine_vocab_size": len(cuisine_vocab),
        "city_id_map": city_map,
        "user_features": [
            {"name": "user_id", "type": "embedding", "vocab_size": n_users + 1, "dim": EMB_DIM_USER, "source": "user.user_id (+ <NEW_USER> OOV)"},
            {"name": "avg_rating_given", "type": "numeric", "range": [0, 1], "source": "user.average_stars / 5"},
            {"name": "review_count_log", "type": "numeric", "source": "log1p(user.review_count)"},
            {"name": "days_active", "type": "numeric", "source": "log1p((today - yelping_since).days)"},
            {"name": "elite_flag", "type": "binary", "source": "user.elite ≠ ''"},
            {"name": "mean_distance_traveled", "type": "numeric", "source": "log1p(haversine pairwise mean over user's biz)"},
            {"name": "fav_cuisine_emb", "type": "vector", "dim": len(cuisine_vocab), "source": "top-3 cuisine pooling over user's reviewed biz"},
            {"name": "price_tolerance_avg", "type": "numeric", "range": [0, 1], "source": "mean(biz.attributes.RestaurantsPriceRange2) / 4"},
        ],
        "item_features": [
            {"name": "business_id", "type": "embedding", "vocab_size": n_businesses + 1, "dim": EMB_DIM_BIZ, "source": "business.business_id (+ <NEW_BUSINESS> OOV)"},
            {"name": "avg_rating", "type": "numeric", "range": [0, 1], "source": "Bayesian smoothed (C=10) business.stars / 5"},
            {"name": "review_count_log", "type": "numeric", "source": "log1p(business.review_count)"},
            {"name": "price_level", "type": "ordinal", "range": [1, 4], "source": "business.attributes.RestaurantsPriceRange2"},
            {"name": "is_open", "type": "binary", "source": "business.is_open"},
            {"name": "has_outdoor_seating", "type": "binary", "source": "business.attributes.OutdoorSeating == True"},
            {"name": "photo_count_log", "type": "numeric", "source": "log1p(business.review_count) clip(0,10) — proxy"},
            {"name": "categories_multi_hot", "type": "vector", "dim": len(cuisine_vocab), "source": "multi-hot over cuisine_vocab"},
            {"name": "city_id", "type": "embedding", "vocab_size": len(city_map), "dim": 4, "source": "business.city → city_id_map"},
        ],
        "context_features": [
            {"name": "distance_from_user_km_log", "type": "numeric", "source": "haversine(user_lat_lon, biz_lat_lon) → log1p"},
            {"name": "hour_bucket", "type": "cyclic", "source": "review.date.hour → sin/cos + 3-bucket (early/lunch/dinner)"},
            {"name": "day_of_week", "type": "categorical", "vocab_size": 7, "source": "review.date.weekday"},
            {"name": "is_weekend", "type": "binary", "source": "day_of_week ∈ {Sat, Sun}"},
            {"name": "trip_day_index", "type": "numeric", "range": [0, 1], "source": "trip context (synthesized for training; real for F2 deploy)"},
            {"name": "region_cluster_id", "type": "embedding", "vocab_size": REGION_K + 1, "dim": 4, "source": "k-means(k=8) on biz lat/lon per city"},
            {"name": "period_id", "type": "categorical", "vocab_size": 3 + 1, "source": "F2 trip period (morning/afternoon/evening) + <UNK> for non-trip"},
            {"name": "activity_emb", "type": "vector", "dim": 32, "source": "sentence-transformer all-MiniLM-L6-v2 → PCA(32) on F2 activity text; zeros for non-trip"},
            {"name": "prior_meals_cuisines", "type": "vector", "dim": len(cuisine_vocab), "source": "multi-hot of cuisines already chosen earlier in trip; zeros for non-trip"},
        ],
        "total_features": 26,
        "total_input_dim_estimate": EMB_DIM_USER + 1 + 1 + 1 + 1 + 1 + len(cuisine_vocab) + 1 + EMB_DIM_BIZ + 1 + 1 + 1 + 1 + 1 + 1 + len(cuisine_vocab) + 4 + 1 + 2 + 7 + 1 + 1 + 4 + 4 + 32 + len(cuisine_vocab),
        "missing_handling": {
            "numeric": "fillna(global median)",
            "categorical": "<UNK> embedding (reserved index 0)",
            "user_id_OOV": "<NEW_USER> reserved index for new Taste hunter users (deploy-time)",
            "trip_features_non_trip": "trip_day_index=0, period_id=<UNK>, activity_emb=zeros, prior_meals_cuisines=zeros",
        },
    }
    return spec


def main():
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Loading Phase 1 + Phase 2 outputs")
    restaurants = pd.read_parquet(CLEANED_DIR / "restaurants_open.parquet")
    reviews_rest = pd.read_parquet(CLEANED_DIR / "reviews_restaurant.parquet")
    users = pd.read_parquet(CLEANED_DIR / "users_target.parquet")
    train = pd.read_parquet(CLEANED_DIR / "train_reviews.parquet")
    cuisine_vocab = load_cuisine_vocab()
    log.info("  cuisine_vocab size: %d", len(cuisine_vocab))

    # Phase 3.1 — User features
    user_features = build_user_features(users, reviews_rest, restaurants, cuisine_vocab)
    user_features.to_parquet(FEATURES_DIR / "user_features.parquet", index=False)
    log.info("  → wrote user_features.parquet (%d rows)", len(user_features))

    # Phase 3.2 — Item features
    item_features, city_map = build_item_features(restaurants, cuisine_vocab)
    item_features.to_parquet(FEATURES_DIR / "item_features.parquet", index=False)
    log.info("  → wrote item_features.parquet (%d rows)", len(item_features))

    # Phase 3.3 — Region clusters
    region_clusters = build_region_clusters(restaurants)
    with open(FEATURES_DIR / "region_clusters.json", "w") as f:
        json.dump(region_clusters, f, indent=2)
    log.info("  → wrote region_clusters.json")

    # Phase 3.4 — train + negatives
    train_neg = build_train_with_negatives(train, restaurants, ratio=NEG_RATIO)
    train_neg.to_parquet(FEATURES_DIR / "train_with_negatives.parquet", index=False)
    log.info("  → wrote train_with_negatives.parquet (%d rows)", len(train_neg))

    # Phase 3.5 — feature_spec.json
    spec = build_feature_spec(cuisine_vocab, city_map, n_users=len(users), n_businesses=len(restaurants))
    with open(FEATURES_DIR / "feature_spec.json", "w") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    log.info("  → wrote feature_spec.json (total estimated input dim: %d)", spec["total_input_dim_estimate"])

    log.info("=" * 60)
    log.info("Phase 3 complete — ready for Phase 4 (baselines) + Phase 5 (DeepFM)")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
