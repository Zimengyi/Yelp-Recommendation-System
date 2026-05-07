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

## Key findings
- Head 1% 商家占 ~25% reviews
- Head 10% 用户写了 ~60% reviews（Gini ~0.7）
- Hour-of-day 双峰：lunch ~12:30 / dinner ~19:00
- K-means elbow 清晰落在 k=8

## Stdout log
**Not captured retroactively**.

## See also
- 全部讨论：`docs/phase_implementation_notes.md` §2
