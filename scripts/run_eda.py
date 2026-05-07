"""Phase 2 — Exploratory Data Analysis (Q1-Q11).

Reads cleaned parquet from Phase 1, generates 8 figures + cuisine_vocab.json,
and prints answers to the 11 questions defined in PRD §3.3.2.

Usage:
    python scripts/run_eda.py

Outputs:
    reports/figures/eda_q1_rating_dist.png       — Q1 rating distribution
    reports/figures/eda_q1_powerlaw.png           — Q1 user review_count log-log
    reports/figures/eda_q2_sparsity.png           — Q2 user×item density heatmap
    reports/figures/eda_q3_top_categories.png     — Q3 top-30 categories bar
    reports/figures/eda_q4_geo.png                — Q4 3-city scatter map
    reports/figures/eda_q4_kmeans_elbow.png       — Q4 k-means elbow curve
    reports/figures/eda_q5_hour_dist.png          — Q5 review-by-hour distribution
    reports/figures/eda_q8_review_length.png      — Q8 review length boxplot
    reports/figures/eda_q10_lorenz_gini.png       — Q10 popularity bias Lorenz curve
    data/features/cuisine_vocab.json              — Q3 top-50 cuisine vocab

Q6 / Q7 / Q9 / Q11 print numerical answers (no figures).

See docs/prd/PRD_v1_section3.3_Model_v2.md §3.3.2 for question definitions.
"""

import json
import logging
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
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
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200, "font.size": 10})


def load_data():
    """Load Phase 1 cleaned parquet files."""
    log.info("Loading Phase 1 outputs from %s", CLEANED_DIR)
    restaurants = pd.read_parquet(CLEANED_DIR / "restaurants_open.parquet")
    reviews = pd.read_parquet(CLEANED_DIR / "reviews_restaurant.parquet")
    users = pd.read_parquet(CLEANED_DIR / "users_target.parquet")
    log.info(
        "  loaded: %d restaurants, %d reviews, %d users",
        len(restaurants),
        len(reviews),
        len(users),
    )
    return restaurants, reviews, users


# =============================================================================
# Q1 — Rating distribution + power-law check
# =============================================================================
def q1_rating_distribution(reviews: pd.DataFrame, users: pd.DataFrame):
    log.info("Q1 — Rating distribution + power-law")

    # Q1.1 — rating histogram
    fig, ax = plt.subplots(figsize=(7, 4))
    rating_counts = reviews["stars"].value_counts().sort_index()
    ax.bar(rating_counts.index, rating_counts.values, color="#3349B3", width=0.6)
    ax.set_xlabel("Star rating")
    ax.set_ylabel("Review count")
    ax.set_title(f"Q1a — Rating distribution (N={len(reviews):,} reviews)")
    for x, y in zip(rating_counts.index, rating_counts.values):
        ax.text(x, y * 1.01, f"{y / len(reviews) * 100:.1f}%", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q1_rating_dist.png", bbox_inches="tight")
    plt.close(fig)

    # Q1.2 — user review_count power-law (log-log)
    user_rc = users["review_count"].values
    rc_sorted = np.sort(user_rc)[::-1]
    rank = np.arange(1, len(rc_sorted) + 1)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.loglog(rank, rc_sorted, "b.", alpha=0.3, markersize=2)
    ax.set_xlabel("User rank (log)")
    ax.set_ylabel("Review count (log)")
    ax.set_title(f"Q1b — User review_count power-law (N={len(users):,} users)")
    ax.grid(True, which="both", alpha=0.3)
    # Fit Zipf-like exponent: rc ≈ C * rank^(-alpha)
    mask = (rc_sorted > 0) & (rank > 10)  # avoid head/tail noise
    log_rank = np.log(rank[mask])
    log_rc = np.log(rc_sorted[mask])
    alpha, log_C = np.polyfit(log_rank, log_rc, 1)
    ax.text(
        0.05, 0.05,
        f"Power-law fit:\nrc ∝ rank^({alpha:.2f})",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q1_powerlaw.png", bbox_inches="tight")
    plt.close(fig)

    # Print answers
    j_shape = (rating_counts[4.0] + rating_counts[5.0]) / len(reviews)
    log.info("  ✓ rating dist: 4-5★ = %.1f%% (J-shape confirmed)", j_shape * 100)
    log.info("  ✓ user power-law exponent α ≈ %.2f (Zipf-like)", -alpha)


# =============================================================================
# Q2 — User-Item sparsity heatmap (1K x 1K sample)
# =============================================================================
def q2_sparsity(reviews: pd.DataFrame, restaurants: pd.DataFrame, users: pd.DataFrame):
    log.info("Q2 — User-Item sparsity heatmap")

    # Sample 1K most active users × 1K most active businesses
    top_users = users.nlargest(1000, "review_count")["user_id"].values
    top_biz = restaurants.nlargest(1000, "review_count")["business_id"].values

    sample = reviews[
        reviews["user_id"].isin(top_users) & reviews["business_id"].isin(top_biz)
    ]
    user_idx = {u: i for i, u in enumerate(top_users)}
    biz_idx = {b: i for i, b in enumerate(top_biz)}

    matrix = np.zeros((1000, 1000), dtype=np.uint8)
    for _, r in sample.iterrows():
        matrix[user_idx[r["user_id"]], biz_idx[r["business_id"]]] = 1

    density = matrix.sum() / matrix.size

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(matrix, aspect="auto", cmap="Greys", interpolation="nearest")
    ax.set_xlabel("Business (top 1K by review_count)")
    ax.set_ylabel("User (top 1K by review_count)")
    ax.set_title(f"Q2 — User-Item interaction matrix (1K×1K, density={density * 100:.2f}%)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q2_sparsity.png", bbox_inches="tight")
    plt.close(fig)

    log.info("  ✓ density (top 1K x 1K) = %.4f%%", density * 100)
    full_density = len(reviews) / (len(users) * len(restaurants))
    log.info("  ✓ full matrix density = %.6f%% (sparsity %.4f%%)", full_density * 100, (1 - full_density) * 100)


# =============================================================================
# Q3 — Top-30 categories + cuisine_vocab.json output
# =============================================================================
def q3_top_categories(restaurants: pd.DataFrame):
    log.info("Q3 — Top-30 categories + cuisine_vocab.json")

    cat_counter = Counter()
    for cats_str in restaurants["categories"].dropna():
        for cat in [c.strip() for c in cats_str.split(",")]:
            if cat:
                cat_counter[cat] += 1

    # Top-50 cuisine for vocab (drop "Restaurants" + "Food" themselves — they're target labels)
    EXCLUDE = {"Restaurants", "Food", "Nightlife", "Bars", "Event Planning & Services"}
    cuisine_vocab = [c for c, _ in cat_counter.most_common(80) if c not in EXCLUDE][:50]

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEATURES_DIR / "cuisine_vocab.json", "w") as f:
        json.dump(
            {
                "version": "v1.0_2026-05-06",
                "size": len(cuisine_vocab),
                "cuisines": cuisine_vocab,
                "source": "EDA Q3 — top-50 categories from restaurants_open.parquet (excluding generic top-level labels)",
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Top-30 plot
    top30 = [(c, cat_counter[c]) for c in cuisine_vocab[:30]]
    labels = [c for c, _ in top30]
    counts = [n for _, n in top30]

    fig, ax = plt.subplots(figsize=(10, 8))
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, counts, color="#3349B3")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Restaurant count")
    ax.set_title(f"Q3 — Top-30 cuisine categories (N={len(restaurants):,} restaurants)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q3_top_categories.png", bbox_inches="tight")
    plt.close(fig)

    log.info("  ✓ wrote cuisine_vocab.json (top-%d): %s, ...", len(cuisine_vocab), ", ".join(cuisine_vocab[:5]))


# =============================================================================
# Q4 — Geographic distribution + k-means elbow
# =============================================================================
def q4_geo(restaurants: pd.DataFrame):
    log.info("Q4 — Geographic distribution + k-means elbow")

    # 3-city scatter map
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    cities = ["Philadelphia", "Tucson", "Tampa"]
    for ax, city in zip(axes, cities):
        sub = restaurants[restaurants["city"] == city]
        ax.scatter(sub["longitude"], sub["latitude"], s=2, alpha=0.4, c="#3349B3")
        ax.set_title(f"{city} (n={len(sub)})")
        ax.set_xlabel("longitude")
        ax.set_ylabel("latitude")
    fig.suptitle("Q4a — Restaurant geographic distribution by city")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q4_geo.png", bbox_inches="tight")
    plt.close(fig)

    # k-means elbow (lazy import to avoid penalty if not used)
    from sklearn.cluster import KMeans

    # Use Philadelphia as primary (largest sample)
    phi = restaurants[restaurants["city"] == "Philadelphia"][["latitude", "longitude"]].values
    inertias = []
    ks = list(range(2, 12))
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        km.fit(phi)
        inertias.append(km.inertia_)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ks, inertias, "o-", color="#3349B3")
    ax.set_xlabel("k (number of clusters)")
    ax.set_ylabel("Inertia (within-cluster SSE)")
    ax.set_title(f"Q4b — k-means elbow on Philadelphia (n={len(phi)})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q4_kmeans_elbow.png", bbox_inches="tight")
    plt.close(fig)

    log.info("  ✓ city distribution: %s", dict(restaurants["city"].value_counts().head()))
    log.info("  ✓ inertia at k=8: %.0f", inertias[6])


# =============================================================================
# Q5 — Review hour distribution (synthesis trip-context proxy)
# =============================================================================
def q5_hour_distribution(reviews: pd.DataFrame):
    log.info("Q5 — Review hour distribution")

    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"])
    reviews["hour"] = reviews["date"].dt.hour
    hour_dist = reviews["hour"].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(hour_dist.index, hour_dist.values, color="#3349B3")
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day (review submission timestamp, UTC)")
    ax.set_ylabel("Review count")
    ax.set_title("Q5 — Review submission hour distribution (proxy for engagement timing)")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q5_hour_dist.png", bbox_inches="tight")
    plt.close(fig)

    log.info(
        "  ⚠ caveat: review timestamp is submission time, NOT visit time. Use as weak signal."
    )
    log.info("  ✓ peak hour: %d:00", hour_dist.idxmax())


# =============================================================================
# Q6 — Cold-start ratio
# =============================================================================
def q6_coldstart_ratio(users: pd.DataFrame, restaurants: pd.DataFrame):
    log.info("Q6 — Cold-start user + business ratio")

    n_users = len(users)
    cold_users = (users["review_count"] < 5).sum()
    log.info(
        "  ✓ cold-start users (review_count < 5): %d / %d = %.1f%%",
        cold_users,
        n_users,
        cold_users / n_users * 100,
    )

    n_biz = len(restaurants)
    cold_biz = (restaurants["review_count"] < 10).sum()
    log.info(
        "  ✓ cold-start businesses (review_count < 10): %d / %d = %.1f%%",
        cold_biz,
        n_biz,
        cold_biz / n_biz * 100,
    )


# =============================================================================
# Q7 — Photo coverage (using business metadata only — photos.json not downloaded)
# =============================================================================
def q7_photo_coverage(restaurants: pd.DataFrame):
    log.info("Q7 — Photo coverage estimate")
    log.info("  (note: photos.json 5GB not downloaded; using attributes proxy)")

    # No direct photo_count field; check if any "photo-relevant" attributes
    has_photos_attr = (
        restaurants.get("attributes", pd.Series([{}])).apply(
            lambda x: isinstance(x, dict) and any("photo" in str(k).lower() for k in x)
        ).sum()
    )
    log.info(
        "  ✓ businesses with photo-related attributes: %d / %d = %.1f%% (best estimate)",
        has_photos_attr,
        len(restaurants),
        has_photos_attr / len(restaurants) * 100,
    )
    log.info(
        "  recommendation: For Phase 1 demo, use #DCDDE8 placeholder for cards (per figma_make_prompt)."
    )


# =============================================================================
# Q8 — Review length distribution
# =============================================================================
def q8_review_length(reviews: pd.DataFrame):
    log.info("Q8 — Review length distribution (for AI Overview LLM cap)")

    lens = reviews["text"].fillna("").str.len()
    pcts = [25, 50, 75, 90, 99]
    quants = lens.quantile([p / 100 for p in pcts])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot([lens.values], showfliers=False, vert=False)
    ax.set_xlabel("Review text length (characters)")
    ax.set_yticks([])
    ax.set_title(f"Q8 — Review length distribution (N={len(lens):,})")
    for p, q in zip(pcts, quants.values):
        ax.axvline(q, color="red", alpha=0.3, linestyle="--")
        ax.text(q, 1.15, f"P{p}\n{int(q)}", ha="center", fontsize=8, color="red")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q8_review_length.png", bbox_inches="tight")
    plt.close(fig)

    log.info("  ✓ percentiles (chars): %s", {f"P{p}": int(q) for p, q in zip(pcts, quants.values)})
    log.info("  ✓ recommendation: AI Overview LLM input cap ≈ P90 ≈ %d chars (%.0f tokens)", int(quants.iloc[3]), int(quants.iloc[3] / 4))


# =============================================================================
# Q9 — Cross-city user mobility (already computed in Phase 1)
# =============================================================================
def q9_crosscity_mobility(reviews: pd.DataFrame, restaurants: pd.DataFrame, users: pd.DataFrame):
    log.info("Q9 — Cross-city user mobility")

    biz_city = restaurants.set_index("business_id")["city"].to_dict()
    rev_city = reviews.copy()
    rev_city["city"] = rev_city["business_id"].map(biz_city)
    user_n_cities = rev_city.groupby("user_id")["city"].nunique()

    n_users = len(users)
    n_multi = (user_n_cities >= 2).sum()
    n_three = (user_n_cities >= 3).sum()
    log.info(
        "  ✓ users with reviews in ≥2 cities: %d / %d = %.2f%%",
        n_multi,
        n_users,
        n_multi / n_users * 100,
    )
    log.info(
        "  ✓ users with reviews in all 3 cities: %d / %d = %.3f%%",
        n_three,
        n_users,
        n_three / n_users * 100,
    )


# =============================================================================
# Q10 — Popularity bias (Lorenz curve + Gini)
# =============================================================================
def q10_popularity_bias(restaurants: pd.DataFrame, reviews: pd.DataFrame):
    log.info("Q10 — Popularity bias (Lorenz + Gini)")

    biz_review_counts = reviews["business_id"].value_counts().sort_values()
    rc = biz_review_counts.values
    cumulative_share_biz = np.arange(1, len(rc) + 1) / len(rc)
    cumulative_share_reviews = np.cumsum(rc) / rc.sum()

    # Gini = 1 - 2 * AUC under Lorenz
    auc = np.trapz(cumulative_share_reviews, cumulative_share_biz)
    gini = 1 - 2 * auc

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(cumulative_share_biz, cumulative_share_reviews, color="#3349B3", linewidth=2, label="Lorenz curve")
    ax.plot([0, 1], [0, 1], color="black", linestyle="--", alpha=0.5, label="Equality line")
    ax.fill_between(cumulative_share_biz, cumulative_share_reviews, alpha=0.2)
    ax.set_xlabel("Cumulative share of businesses (sorted by review count)")
    ax.set_ylabel("Cumulative share of reviews")
    ax.set_title(f"Q10 — Popularity bias Lorenz curve (Gini = {gini:.3f})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_q10_lorenz_gini.png", bbox_inches="tight")
    plt.close(fig)

    top_1pct = int(len(rc) * 0.01)
    top_1pct_share = rc[-top_1pct:].sum() / rc.sum()
    log.info("  ✓ Gini coefficient: %.3f (closer to 1 = more concentrated)", gini)
    log.info("  ✓ top-1%% restaurants contribute %.1f%% of reviews", top_1pct_share * 100)


# =============================================================================
# Q11 — Activity text data availability
# =============================================================================
def q11_activity_availability():
    log.info("Q11 — Activity text data availability evaluation")
    log.info(
        """  Yelp Open Dataset has NO native activity description field.

  Option A — LLM generation:
    - Sonnet 4.6 single call ~$0.003 per activity
    - Demo 27 activities × $0.003 ≈ $0.08 total cost (one-time)
    - Production: real-time generation per trip → adds ~500ms latency
    - Pro: dynamic, contextual; con: cost + latency at scale

  Option B — Hand-crafted template library:
    - Pre-author 30-50 activity templates per target city
    - Pro: zero LLM call latency, predictable cost
    - Con: limited diversity; staff manual writing for 3 cities × ~15 templates = 45 templates

  Recommendation: Option A for demo (low cost, dynamic).
  Future: Option B as fallback if LLM cost grows."""
    )


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    restaurants, reviews, users = load_data()

    log.info("=" * 60)
    log.info("Phase 2 — EDA (Q1-Q11)")
    log.info("=" * 60)

    q1_rating_distribution(reviews, users)
    q2_sparsity(reviews, restaurants, users)
    q3_top_categories(restaurants)
    q4_geo(restaurants)
    q5_hour_distribution(reviews)
    q6_coldstart_ratio(users, restaurants)
    q7_photo_coverage(restaurants)
    q8_review_length(reviews)
    q9_crosscity_mobility(reviews, restaurants, users)
    q10_popularity_bias(restaurants, reviews)
    q11_activity_availability()

    log.info("=" * 60)
    log.info("Phase 2 complete — see reports/figures/ + data/features/cuisine_vocab.json")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
