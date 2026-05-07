# Phase 5 Run Record — DeepFM 主训练 + Sweep

**Status**: 🟡 进行中

---

## Stage 5.1 — Sanity Check

**Date**: 2026-05-07 13:30–13:47 · **Commit**: `6354456` · **Status**: ✅

### Command
```bash
python scripts/train_deepfm.py --epochs 10
# 默认 config: emb_dim=8, dropout=0.2, l2=1e-4, lr=1e-3, batch=4096
```

### Outputs
- `models/deepfm_emb8_drop0.2_l20.0001.pt` (13.6 MB, gitignored)
- `models/deepfm_emb8_drop0.2_l20.0001_history.json` (1.3 KB, **tracked**)

### Final metrics

| Metric | Best | Final | vs FM Δ |
|---|---|---|---|
| Val AUC | 0.8330 (epoch 9) | 0.8329 | +0.003 |
| Val NDCG@10 | 0.3182 (epoch 10) | 0.3182 | **+0.046** |
| Val Recall@10 | 0.5397 (epoch 9) | 0.5387 | **+0.065** |

### Stdout log
**Not captured for sanity run** (training_logs/ infrastructure added after this).

---

## Stage 5.2 — emb_dim Sweep

**Date**: 2026-05-07 13:48 起 · **Status**: 🟡 跑中（PID 82569）

### Command
```bash
python scripts/train_deepfm.py --sweep emb_dim --epochs 10 2>&1 | tee /tmp/deepfm_stageA.log
# Sweep emb_dim ∈ {4, 8, 16, 32}, 其余固定 dropout=0.2 / l2=1e-4 / lr=1e-3
```

### Live log
**`reports/training_logs/phase5.2_stageA_emb_dim_sweep.log`**（实时跟随，每 2 min 同步一次）

### Progress (截至本 record 写作)

| emb_dim | 状态 | Best NDCG@10 | Best Recall@10 | Best AUC |
|---|---|---|---|---|
| 4 | ✅ 14:04 | 0.3079 | 0.5224 | 0.8194 |
| 8 | ✅ 14:20 | **0.3198** | **0.5397** | 0.8318 |
| 16 | 🟡 epoch 5/10 | tracking | tracking | tracking |
| 32 | ⏳ 排队 | — | — | — |

ETA 完成：~15:05–15:10

---

## Stage 5.3 — dropout × L2 Grid

**Status**: ⏳ 待跑（5.2 完成后）

预期命令：
```bash
python scripts/train_deepfm.py --sweep dropout_l2 --emb_dim <best_from_5.2> --epochs 10
# 5×4 = 20 configs, ~5-10 hours 隔夜跑
```

---

## Stage 5.4 — Final Retrain on train+val

**Status**: ⏳ 待跑

---

## Stage 5.5 — Ablation: drop user_id embedding (验证 H6)

**Status**: ⏳ 待跑

---

## See also
- 全部讨论：`docs/phase_implementation_notes.md` §5
