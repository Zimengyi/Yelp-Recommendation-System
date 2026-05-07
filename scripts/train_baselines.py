"""Phase 4 — Train MF + FM baselines.

Trains two PyTorch models in sequence:
- MF: pure matrix factorization (user_emb · item_emb + biases) — no side features
- FM: factorization machine with all 26 features (user 8 + item 9 + simple interactions)

Both produce metrics on val set (sampled NDCG@10 with 1+99 candidates).

Usage:
    python scripts/train_baselines.py [--model mf|fm|both]

Outputs:
    models/mf.pt + models/mf_metrics.json
    models/fm.pt + models/fm_metrics.json
    reports/figures/training_baselines_curves.png
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from src.data import IDEncoder, TasteHunterDataset, build_encoders, make_val_eval_pairs
from src.eval import evaluate_full

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"
MODELS_DIR = PROJECT_ROOT / "models"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

# Hyperparameters
SEED = 42
EMB_DIM = 8           # user_id / item_id embedding dim (matches feature_spec.json)
LR = 5e-3
WEIGHT_DECAY = 1e-5   # L2
EPOCHS_MF = 10
EPOCHS_FM = 10
BATCH_SIZE = 8192
DEVICE = (
    "mps" if torch.backends.mps.is_available()
    else "cuda" if torch.cuda.is_available()
    else "cpu"
)


# =============================================================================
# Models
# =============================================================================
class MF(nn.Module):
    """Matrix factorization: y = sigma(u·v + b_u + b_v + b)."""

    def __init__(self, n_users: int, n_items: int, emb_dim: int = EMB_DIM):
        super().__init__()
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))
        nn.init.normal_(self.user_emb.weight, std=0.01)
        nn.init.normal_(self.item_emb.weight, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.item_bias.weight)

    def forward(self, user_idx: torch.Tensor, item_idx: torch.Tensor, **kwargs) -> torch.Tensor:
        u = self.user_emb(user_idx)            # (B, k)
        v = self.item_emb(item_idx)            # (B, k)
        dot = (u * v).sum(dim=-1)               # (B,)
        bu = self.user_bias(user_idx).squeeze(-1)
        bi = self.item_bias(item_idx).squeeze(-1)
        return torch.sigmoid(dot + bu + bi + self.global_bias)


class FM(nn.Module):
    """Factorization machine over user_id, item_id, + all 26 features.

    Implementation simplified for class project: linear layer on flattened features
    + bilinear u·v term (the FM 2nd-order). Captures most of FM's expressiveness
    without full O(d²) pairwise term computation.
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        emb_dim: int = EMB_DIM,
        user_num_dim: int = 6,
        user_cuisine_dim: int = 50,
        item_num_dim: int = 7,
        item_cat_dim: int = 50,
    ):
        super().__init__()
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        # Linear layer over all numeric features (user 6 + item 7 + cuisine multi-hot 50 + cat multi-hot 50)
        feat_dim = user_num_dim + item_num_dim + user_cuisine_dim + item_cat_dim
        self.linear = nn.Linear(feat_dim, 1)

        nn.init.normal_(self.user_emb.weight, std=0.01)
        nn.init.normal_(self.item_emb.weight, std=0.01)

    def forward(
        self,
        user_idx: torch.Tensor,
        item_idx: torch.Tensor,
        user_num: torch.Tensor = None,
        user_cuisine: torch.Tensor = None,
        item_num: torch.Tensor = None,
        item_cat: torch.Tensor = None,
    ) -> torch.Tensor:
        # FM second-order: u · v
        u = self.user_emb(user_idx)
        v = self.item_emb(item_idx)
        order2 = (u * v).sum(dim=-1)
        bu = self.user_bias(user_idx).squeeze(-1)
        bi = self.item_bias(item_idx).squeeze(-1)

        # Linear over side features
        feat_concat = torch.cat([user_num, item_num, user_cuisine, item_cat], dim=-1)
        order1 = self.linear(feat_concat).squeeze(-1)

        return torch.sigmoid(order1 + order2 + bu + bi + self.global_bias)


# =============================================================================
# Train + eval loop
# =============================================================================
def train_one_model(
    model: nn.Module,
    train_loader: DataLoader,
    user_idx_eval: np.ndarray,
    item_idx_eval: np.ndarray,
    label_eval: np.ndarray,
    epochs: int,
    lr: float = LR,
    wd: float = WEIGHT_DECAY,
    device: str = DEVICE,
    name: str = "model",
    feature_kwargs_fn=None,
) -> dict:
    """Train + eval per epoch. Returns history dict with train_loss + val metrics."""
    log.info("Training %s on %s", name, device)
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    bce = nn.BCELoss()

    history = {"epoch": [], "train_loss": [], "val_auc": [], "val_ndcg10": [], "val_recall10": []}

    for epoch in range(1, epochs + 1):
        model.train()
        loss_sum = 0.0
        n_batch = 0
        t0 = time.time()
        for batch in train_loader:
            u = batch["user_idx"].to(device)
            i = batch["item_idx"].to(device)
            y = batch["label"].to(device)

            kwargs = {}
            for key in ("user_num", "user_cuisine", "item_num", "item_cat"):
                if key in batch:
                    kwargs[key] = batch[key].to(device)

            pred = model(u, i, **kwargs)
            loss = bce(pred, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            loss_sum += loss.item()
            n_batch += 1

        train_loss = loss_sum / max(n_batch, 1)
        elapsed = time.time() - t0

        # Eval
        metrics = evaluate_full(
            model, user_idx_eval, item_idx_eval, label_eval, device=device,
            feature_kwargs_fn=feature_kwargs_fn,
        )

        log.info(
            "  epoch %02d | %.0fs | train_loss=%.4f | val AUC=%.4f NDCG@10=%.4f Recall@10=%.4f",
            epoch, elapsed, train_loss, metrics["AUC"], metrics["NDCG@10"], metrics["Recall@10"],
        )

        history["epoch"].append(epoch)
        history["train_loss"].append(train_loss)
        history["val_auc"].append(metrics["AUC"])
        history["val_ndcg10"].append(metrics["NDCG@10"])
        history["val_recall10"].append(metrics["Recall@10"])

    return history


def make_feature_kwargs_fn(dataset: TasteHunterDataset):
    """Closure: given user/item idx arrays, look up feature tensors."""
    def fn(u_arr, i_arr):
        u_t = torch.from_numpy(u_arr)
        i_t = torch.from_numpy(i_arr)
        return {
            "user_num": dataset.user_num_t[u_t],
            "user_cuisine": dataset.user_cuisine_t[u_t],
            "item_num": dataset.item_num_t[i_t],
            "item_cat": dataset.item_cat_t[i_t],
        }
    return fn


# =============================================================================
# Main
# =============================================================================
def main(which: str = "both"):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Loading features + val data")
    user_features = pd.read_parquet(FEATURES_DIR / "user_features.parquet")
    item_features = pd.read_parquet(FEATURES_DIR / "item_features.parquet")
    val_df = pd.read_parquet(CLEANED_DIR / "val_reviews.parquet")

    user_encoder, item_encoder = build_encoders(user_features, item_features)
    n_users = len(user_encoder)
    n_items = len(item_encoder)
    log.info("Encoders: %d users (incl OOV), %d items (incl OOV)", n_users, n_items)

    # Build val eval pairs (1 positive + 99 negatives per user)
    log.info("Building val eval pairs (1 + 99 candidates per positive)")
    user_idx_eval, item_idx_eval, label_eval = make_val_eval_pairs(
        val_df, user_encoder, item_encoder, item_features, n_negs=99,
    )

    # Build train loader with features (used by FM; MF ignores feature kwargs)
    log.info("Building train DataLoader (with features for FM)")
    train_df = pd.read_parquet(FEATURES_DIR / "train_with_negatives.parquet")
    log.info("  train: %d rows", len(train_df))
    train_ds = TasteHunterDataset(
        train_df, user_encoder, item_encoder,
        with_features=True,
        user_features=user_features,
        item_features=item_features,
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)

    feature_kwargs_fn = make_feature_kwargs_fn(train_ds)

    metrics_summary = {}
    histories = {}

    if which in ("mf", "both"):
        log.info("=" * 60)
        log.info("Phase 4.1 — MF baseline (pure user × item bilinear, no side features)")
        log.info("=" * 60)
        mf = MF(n_users, n_items, emb_dim=EMB_DIM)
        h = train_one_model(
            mf, train_loader, user_idx_eval, item_idx_eval, label_eval,
            epochs=EPOCHS_MF, name="MF",
            feature_kwargs_fn=None,  # MF doesn't use features
        )
        torch.save(mf.state_dict(), MODELS_DIR / "mf.pt")
        with open(MODELS_DIR / "mf_history.json", "w") as f:
            json.dump(h, f, indent=2)
        # Final metrics = last epoch
        metrics_summary["MF"] = {
            "AUC": h["val_auc"][-1],
            "NDCG@10": h["val_ndcg10"][-1],
            "Recall@10": h["val_recall10"][-1],
            "epochs_trained": len(h["epoch"]),
        }
        histories["MF"] = h
        log.info(
            "  → MF saved: AUC=%.4f NDCG@10=%.4f Recall@10=%.4f",
            metrics_summary["MF"]["AUC"], metrics_summary["MF"]["NDCG@10"], metrics_summary["MF"]["Recall@10"],
        )

    if which in ("fm", "both"):
        log.info("=" * 60)
        log.info("Phase 4.2 — FM baseline (user × item bilinear + 26 side features linear)")
        log.info("=" * 60)
        fm = FM(n_users, n_items, emb_dim=EMB_DIM)
        h = train_one_model(
            fm, train_loader, user_idx_eval, item_idx_eval, label_eval,
            epochs=EPOCHS_FM, name="FM",
            feature_kwargs_fn=feature_kwargs_fn,
        )
        torch.save(fm.state_dict(), MODELS_DIR / "fm.pt")
        with open(MODELS_DIR / "fm_history.json", "w") as f:
            json.dump(h, f, indent=2)
        metrics_summary["FM"] = {
            "AUC": h["val_auc"][-1],
            "NDCG@10": h["val_ndcg10"][-1],
            "Recall@10": h["val_recall10"][-1],
            "epochs_trained": len(h["epoch"]),
        }
        histories["FM"] = h
        log.info(
            "  → FM saved: AUC=%.4f NDCG@10=%.4f Recall@10=%.4f",
            metrics_summary["FM"]["AUC"], metrics_summary["FM"]["NDCG@10"], metrics_summary["FM"]["Recall@10"],
        )

    # Save combined metrics
    with open(MODELS_DIR / "baseline_metrics.json", "w") as f:
        json.dump(metrics_summary, f, indent=2)

    # Plot learning curves
    log.info("Plotting baseline learning curves")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for name, h in histories.items():
        axes[0].plot(h["epoch"], h["train_loss"], "o-", label=name)
        axes[1].plot(h["epoch"], h["val_auc"], "o-", label=name)
        axes[2].plot(h["epoch"], h["val_ndcg10"], "o-", label=name)
    axes[0].set_title("Train BCE loss")
    axes[1].set_title("Val AUC")
    axes[2].set_title("Val NDCG@10")
    for ax in axes:
        ax.set_xlabel("Epoch")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "training_baselines_curves.png", bbox_inches="tight")
    plt.close(fig)
    log.info("  → wrote training_baselines_curves.png")

    log.info("=" * 60)
    log.info("Phase 4 complete — Summary:")
    log.info("=" * 60)
    for name, m in metrics_summary.items():
        log.info("  %s: AUC=%.4f / NDCG@10=%.4f / Recall@10=%.4f",
                 name, m["AUC"], m["NDCG@10"], m["Recall@10"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["mf", "fm", "both"], default="both")
    args = parser.parse_args()
    main(args.model)
