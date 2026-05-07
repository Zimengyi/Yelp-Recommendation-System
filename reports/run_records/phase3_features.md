# Phase 3 Run Record — 特征工程

**Date**: 2026-05-06 · **Commit**: `194f8e2` · **Status**: ✅

## Command
```bash
python scripts/build_features.py
```

## Inputs
- `data/cleaned/restaurants_open.parquet`
- `data/cleaned/users_target.parquet`
- `data/cleaned/train_reviews.parquet`
- `data/features/cuisine_vocab.json`（Phase 2 产物）

## Outputs
| Path | Size | Rows |
|---|---|---|
| `data/features/user_features.parquet` | 15 MB | 359,007 |
| `data/features/item_features.parquet` | 515 KB | 9,022 |
| `data/features/train_with_negatives.parquet` | 19 MB | **2,074,945** (415K正 + 1.66M负, 1:4) |
| `data/features/feature_spec.json` | 4.6 KB | 26 features 定义 |
| `data/features/region_clusters.json` | 2.0 KB | k=8 / 城 |

> Note: `*.parquet` gitignored，re-run 命令复现。

## Key numbers
- **26 features**: 8 user + 9 item + 9 context
- **234-dim** total input estimate
- **Negative ratio 1:4**（每正样本配 4 个 same-city 未访问负样本）
- Region clusters per city: Philadelphia n=4373 / Tampa n=2502 / Tucson n=2147

## 关键修复
1. **haversine numba bug** → 改写为 inline numpy + `np.triu_indices`
2. **IDEncoder OOV 冲撞** → 过滤 OOV markers 后从 idx 1 起枚举（src/data.py:34-50）

## Stdout log
**Not captured retroactively**.

## See also
- 全部讨论：`docs/phase_implementation_notes.md` §3
