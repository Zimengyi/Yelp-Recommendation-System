# Phase 4 Run Record — MF + FM Baselines

**Date**: 2026-05-07 · **Commit**: `1a12f23` · **Status**: ✅

## Commands
```bash
# MF (10 epoch on MPS)
python scripts/train_baselines.py --model mf --epochs 10
# FM (10 epoch on MPS)
python scripts/train_baselines.py --model fm --epochs 10
```

## Hyperparams
- `emb_dim=8` · `lr=1e-3` (Adam) · `batch_size=4096` · `loss=BCE` · `device=mps`
- Negative sampling 1:4（与 Phase 3 train_with_negatives 一致）

## Outputs
| Path | Size |
|---|---|
| `models/mf.pt` | 13 MB（gitignored） |
| `models/fm.pt` | 13 MB（gitignored） |
| `models/mf_history.json` | 656 B（**tracked** — 每 epoch metric） |
| `models/fm_history.json` | 1.1 KB（**tracked**） |
| `models/baseline_metrics.json` | 253 B（**tracked** — 最终汇总） |
| `reports/figures/training_baselines_curves.png` | 142 KB（**tracked** — 训练曲线对照） |

## Final metrics

| Model | Val AUC | Val NDCG@10 | Val Recall@10 |
|---|---|---|---|
| MF | 0.7854 | 0.2677 | 0.4651 |
| FM | **0.8302** | 0.2720 | 0.4749 |
| Δ FM−MF | +0.0448 | +0.0043 | +0.0098 |

**Key finding**: FM 加了 113-dim side feature linear，单纯线性融合即把 AUC 拉高 4.5 点。

## 关键修复
- **MPS device 错配** → `src/eval.py` 加 `kwargs = {k: v.to(device) for k, v in kwargs.items()}`

## Stdout log
**Not captured retroactively**.

## See also
- 全部讨论：`docs/phase_implementation_notes.md` §4（含 MF / FM 机制教学性解释）
