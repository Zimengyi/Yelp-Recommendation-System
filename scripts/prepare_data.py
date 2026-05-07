"""Phase 1 — Data preparation pipeline.

Reads raw Yelp Open Dataset JSON files, filters to target cities, restaurants only,
and produces parquet outputs for downstream phases.

Usage:
    python scripts/prepare_data.py [--cities Philadelphia,Tucson,Tampa]

Outputs to data/cleaned/:
    - businesses_target.parquet     (Phase 1.1: city-filtered businesses)
    - reviews_target.parquet         (Phase 1.1: corresponding reviews)
    - restaurants_open.parquet       (Phase 1.2: restaurant + is_open subset)
    - reviews_restaurant.parquet     (Phase 1.2: corresponding reviews)
    - users_target.parquet           (Phase 1.3: user records)
    - train_reviews.parquet          (Phase 1.3: temporal split, ≤ P70)
    - val_reviews.parquet            (Phase 1.3: temporal split, P70-P80)
    - test_reviews.parquet           (Phase 1.3: temporal split, > P80)
    - coldstart_test_reviews.parquet (Phase 1.3: review_count < 5 users held out)
    - crosscity_test_reviews.parquet (Phase 1.3: ≥2-city users — travel proxy)

See docs/training_pipeline_plan.md §1 for design.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_CITIES = ["Philadelphia", "Tucson", "Tampa"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yelp_dataset_link"
OUT_DIR = PROJECT_ROOT / "data" / "cleaned"


def stream_json_lines(path: Path):
    """Yield one parsed JSON object per line. Streams without loading entire file."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def filter_businesses_by_city(business_path: Path, cities: list[str]) -> pd.DataFrame:
    """Phase 1.1.3 — Stream businesses, keep only those in target cities."""
    log.info("Filtering businesses to cities: %s", cities)
    cities_set = set(cities)
    rows = []
    seen = 0
    for biz in stream_json_lines(business_path):
        seen += 1
        if seen % 50_000 == 0:
            log.info("  scanned %d businesses, kept %d", seen, len(rows))
        if (biz.get("city") or "").strip() in cities_set:
            rows.append(biz)
    log.info("  done: %d kept of %d total", len(rows), seen)
    return pd.DataFrame(rows)


def filter_reviews_by_business_ids(
    review_path: Path, business_ids: set[str]
) -> pd.DataFrame:
    """Phase 1.1.4 — Stream reviews, keep only those for target businesses."""
    log.info("Filtering reviews against %d target businesses", len(business_ids))
    rows = []
    seen = 0
    for r in stream_json_lines(review_path):
        seen += 1
        if seen % 500_000 == 0:
            log.info("  scanned %d reviews, kept %d", seen, len(rows))
        if r.get("business_id") in business_ids:
            rows.append(r)
    log.info("  done: %d kept of %d total", len(rows), seen)
    return pd.DataFrame(rows)


def filter_users_by_ids(user_path: Path, user_ids: set[str]) -> pd.DataFrame:
    """Phase 1.3.1 — Stream users, keep only those who reviewed target businesses."""
    log.info("Filtering users against %d unique reviewers", len(user_ids))
    rows = []
    seen = 0
    for u in stream_json_lines(user_path):
        seen += 1
        if seen % 200_000 == 0:
            log.info("  scanned %d users, kept %d", seen, len(rows))
        if u.get("user_id") in user_ids:
            rows.append(u)
    log.info("  done: %d kept of %d total", len(rows), seen)
    return pd.DataFrame(rows)


def filter_to_restaurants(businesses: pd.DataFrame) -> pd.DataFrame:
    """Phase 1.2 — Keep only categories ⊃ Restaurants/Food and is_open=1."""
    log.info("Filtering to restaurants (categories ⊃ Restaurants/Food, is_open=1)")
    cat = businesses["categories"].fillna("")
    is_food = cat.str.contains("Restaurants", case=False, na=False) | cat.str.contains(
        "Food", case=False, na=False
    )
    is_open = businesses["is_open"] == 1
    out = businesses.loc[is_food & is_open].reset_index(drop=True)
    log.info(
        "  done: %d open restaurants from %d total target businesses",
        len(out),
        len(businesses),
    )
    return out


def temporal_split(reviews: pd.DataFrame, p_train: float = 0.7, p_val: float = 0.8):
    """Phase 1.3.2 — Split reviews by date quantiles (≤P70 / P70-P80 / >P80).

    Returns (train, val, test) dataframes. Sorted by date as side effect.
    """
    log.info("Temporal split: P%.0f / P%.0f-P%.0f / >P%.0f", p_train * 100, p_train * 100, p_val * 100, p_val * 100)
    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"])
    reviews = reviews.sort_values("date").reset_index(drop=True)
    cut_train = reviews["date"].quantile(p_train)
    cut_val = reviews["date"].quantile(p_val)
    log.info("  train cut date: %s", cut_train)
    log.info("  val cut date:   %s", cut_val)
    train = reviews[reviews["date"] <= cut_train]
    val = reviews[(reviews["date"] > cut_train) & (reviews["date"] <= cut_val)]
    test = reviews[reviews["date"] > cut_val]
    log.info("  split sizes: train=%d / val=%d / test=%d", len(train), len(val), len(test))
    return train, val, test


def extract_coldstart_subset(
    reviews: pd.DataFrame, users: pd.DataFrame, threshold: int = 5
) -> pd.DataFrame:
    """Phase 1.3.4 — Extract reviews from users with review_count < threshold.

    These users' ALL reviews are held out from train (per H6 cold-start design).
    """
    log.info("Extracting cold-start subset (review_count < %d)", threshold)
    cold_user_ids = set(users.loc[users["review_count"] < threshold, "user_id"])
    out = reviews[reviews["user_id"].isin(cold_user_ids)].copy()
    log.info("  done: %d reviews from %d cold-start users", len(out), len(cold_user_ids))
    return out


def extract_crosscity_subset(reviews: pd.DataFrame, businesses: pd.DataFrame) -> pd.DataFrame:
    """Phase 1.3.5 — Extract reviews from users who reviewed ≥2 different cities.

    These users serve as travel proxy for cross-city generalization eval.
    """
    log.info("Extracting cross-city subset (users with ≥2 cities)")
    biz_city = businesses.set_index("business_id")["city"].to_dict()
    rev_with_city = reviews.copy()
    rev_with_city["city"] = rev_with_city["business_id"].map(biz_city)
    user_cities = rev_with_city.groupby("user_id")["city"].nunique()
    multi_city_users = set(user_cities[user_cities >= 2].index)
    out = reviews[reviews["user_id"].isin(multi_city_users)].copy()
    log.info(
        "  done: %d reviews from %d multi-city users",
        len(out),
        len(multi_city_users),
    )
    return out


def main(cities: list[str]):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    business_path = RAW_DIR / "yelp_academic_dataset_business.json"
    review_path = RAW_DIR / "yelp_academic_dataset_review.json"
    user_path = RAW_DIR / "yelp_academic_dataset_user.json"

    for p in (business_path, review_path, user_path):
        if not p.exists():
            log.error("Missing raw file: %s", p)
            sys.exit(1)

    # Phase 1.1 — city filter on businesses + reviews
    log.info("=" * 60)
    log.info("Phase 1.1 — City filter")
    log.info("=" * 60)
    businesses = filter_businesses_by_city(business_path, cities)
    businesses.to_parquet(OUT_DIR / "businesses_target.parquet", index=False)
    log.info("  → wrote %d rows to businesses_target.parquet", len(businesses))

    biz_ids = set(businesses["business_id"])
    reviews = filter_reviews_by_business_ids(review_path, biz_ids)
    reviews.to_parquet(OUT_DIR / "reviews_target.parquet", index=False)
    log.info("  → wrote %d rows to reviews_target.parquet", len(reviews))

    # Phase 1.2 — restaurant + is_open filter
    log.info("=" * 60)
    log.info("Phase 1.2 — Restaurant subset filter")
    log.info("=" * 60)
    restaurants = filter_to_restaurants(businesses)
    restaurants.to_parquet(OUT_DIR / "restaurants_open.parquet", index=False)
    log.info("  → wrote %d rows to restaurants_open.parquet", len(restaurants))

    rest_ids = set(restaurants["business_id"])
    reviews_rest = reviews[reviews["business_id"].isin(rest_ids)].reset_index(drop=True)
    reviews_rest.to_parquet(OUT_DIR / "reviews_restaurant.parquet", index=False)
    log.info("  → wrote %d rows to reviews_restaurant.parquet", len(reviews_rest))

    # Phase 1.3 — user filter + temporal split + subsets
    log.info("=" * 60)
    log.info("Phase 1.3 — User subset + temporal split + held-out subsets")
    log.info("=" * 60)
    user_ids = set(reviews_rest["user_id"].unique())
    users = filter_users_by_ids(user_path, user_ids)
    users.to_parquet(OUT_DIR / "users_target.parquet", index=False)
    log.info("  → wrote %d rows to users_target.parquet", len(users))

    # Cold-start subset (held out before temporal split)
    coldstart_test = extract_coldstart_subset(reviews_rest, users)
    coldstart_test.to_parquet(OUT_DIR / "coldstart_test_reviews.parquet", index=False)
    log.info("  → wrote %d rows to coldstart_test_reviews.parquet", len(coldstart_test))

    # Cross-city subset (held out before temporal split, restaurants only)
    crosscity_test = extract_crosscity_subset(reviews_rest, restaurants)
    crosscity_test.to_parquet(OUT_DIR / "crosscity_test_reviews.parquet", index=False)
    log.info("  → wrote %d rows to crosscity_test_reviews.parquet", len(crosscity_test))

    # Temporal split on remaining reviews (excluding both held-out subsets)
    held_out_user_ids = set(coldstart_test["user_id"]).union(set(crosscity_test["user_id"]))
    main_reviews = reviews_rest[~reviews_rest["user_id"].isin(held_out_user_ids)].reset_index(drop=True)
    log.info(
        "  main pool for temporal split: %d reviews (excluded %d held-out user reviews)",
        len(main_reviews),
        len(reviews_rest) - len(main_reviews),
    )
    train, val, test = temporal_split(main_reviews)
    train.to_parquet(OUT_DIR / "train_reviews.parquet", index=False)
    val.to_parquet(OUT_DIR / "val_reviews.parquet", index=False)
    test.to_parquet(OUT_DIR / "test_reviews.parquet", index=False)
    log.info("  → wrote train_reviews.parquet (%d rows)", len(train))
    log.info("  → wrote val_reviews.parquet   (%d rows)", len(val))
    log.info("  → wrote test_reviews.parquet  (%d rows)", len(test))

    # Summary
    log.info("=" * 60)
    log.info("Phase 1 complete")
    log.info("=" * 60)
    log.info("Target cities:   %s", cities)
    log.info("Open restaurants: %d", len(restaurants))
    log.info("Total reviews:    %d (restaurant only)", len(reviews_rest))
    log.info("Unique users:     %d", len(users))
    log.info("Train / Val / Test: %d / %d / %d", len(train), len(val), len(test))
    log.info("Cold-start test:  %d (review_count < 5 users)", len(coldstart_test))
    log.info("Cross-city test:  %d (≥2-city users)", len(crosscity_test))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--cities",
        type=str,
        default=",".join(DEFAULT_CITIES),
        help=f"Comma-separated list of target cities. Default: {DEFAULT_CITIES}",
    )
    args = parser.parse_args()
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    main(cities)
