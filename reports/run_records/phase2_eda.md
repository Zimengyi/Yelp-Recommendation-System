# Phase 2 Run Record — EDA

**Date**: 2026-05-06 · **Commit**: `f336e07` · **Status**: ✅

## Command
```bash
python scripts/run_eda.py
```

## Inputs
- `data/cleaned/restaurants_open.parquet`
- `data/cleaned/reviews_restaurant.parquet`
- `data/cleaned/users_target.parquet`

## Outputs
**Figures (9 PNG, all tracked):**
- `reports/figures/eda_q1_powerlaw.png` — review_count 长尾
- `reports/figures/eda_q1_rating_dist.png` — rating 分布偏斜
- `reports/figures/eda_q2_sparsity.png` — user-item 稀疏度
- `reports/figures/eda_q3_top_categories.png` — top 50 categories（cuisine 词表来源）
- `reports/figures/eda_q4_geo.png` — 三城地理散点
- `reports/figures/eda_q4_kmeans_elbow.png` — k=8 选择
- `reports/figures/eda_q5_hour_dist.png` — hour-of-day 双峰
- `reports/figures/eda_q8_review_length.png` — review 长度分布
- `reports/figures/eda_q10_lorenz_gini.png` — 用户活跃度 Lorenz 曲线

**Data spec:**
- `data/features/cuisine_vocab.json` (50 cuisines, v1.0_2026-05-06)

## Key findings (latest notebook run)
- 4-5 star share: **69.8%** — confirms `stars >= 4` is a usable positive label threshold
- User review_count power-law exponent ≈ **1.46** (Zipf-like long tail)
- Sparsity: full user-item matrix **99.97%** sparse; top-1K × 1K slice **0.91%** density
- Popularity bias: Gini = **0.681**, top 1% restaurants get **15.2%** of reviews
- Cuisine vocab top 5: Sandwiches / Coffee & Tea / Fast Food / American (Traditional) / Pizza
- K-means elbow at k=8 (Philadelphia subset, inertia ≈ 2)
- Cold-start: **33.2%** users have review_count<5; **16.0%** restaurants have review_count<10
- Cross-city: **1.46%** users wrote in ≥2 of our cities; **0.045%** in all three
- Review length percentiles: P50=401 / P75=712 / P90=**1,149** / P99=2,483 chars
- Review submission peak hour: 1:00 UTC (submission time, not visit time — used as weak engagement signal only)

## Stdout log
**Not captured retroactively**.

## See also
- 全部讨论：`docs/phase_implementation_notes.md` §2
