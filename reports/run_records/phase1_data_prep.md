# Phase 1 Run Record — 数据准备

**Date**: 2026-05-06 · **Commit**: `1cb2230` · **Status**: ✅

## Command
```bash
python scripts/prepare_data.py
```

## Inputs
- `data/raw/yelp_dataset/yelp_academic_dataset_business.json` (~150K lines)
- `data/raw/yelp_dataset/yelp_academic_dataset_review.json` (~7M lines)
- `data/raw/yelp_dataset/yelp_academic_dataset_user.json` (~2M lines)

## Outputs
| Path | Size | Rows |
|---|---|---|
| `data/cleaned/businesses_target.parquet` | 3.7 MB | — |
| `data/cleaned/restaurants_open.parquet` | 1.0 MB | **9,022** |
| `data/cleaned/reviews_target.parquet` | 770 MB | — |
| `data/cleaned/reviews_restaurant.parquet` | 408 MB | — |
| `data/cleaned/users_target.parquet` | 563 MB | **359,007** |
| `data/cleaned/train_reviews.parquet` | 238 MB | ~722K |
| `data/cleaned/val_reviews.parquet` | 31 MB | ~103K |
| `data/cleaned/test_reviews.parquet` | 60 MB | ~206K |
| `data/cleaned/coldstart_test_reviews.parquet` | 45 MB | — |
| `data/cleaned/crosscity_test_reviews.parquet` | 24 MB | — |

> Note: `data/cleaned/*.parquet` is gitignored (regenerable from raw). To re-create on a fresh clone, place Yelp Open Dataset under `data/raw/yelp_dataset/` and re-run the command above.

## Key numbers
- **3 target cities**: Philadelphia (4,373 restaurants) / Tampa (2,502) / Tucson (2,147) = 9,022 total
- **1,032,056** reviews split P70 / P80 / P100 by date

## Stdout log
**Not captured retroactively** — Phase 1 was run before training_logs/ infrastructure existed (added 2026-05-07).

## See also
- Full discussion + 5-section analysis: `docs/phase_implementation_notes.md` §1
