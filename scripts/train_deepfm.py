"""Phase 5 — DeepFM main training + hyperparameter sweep.

Implements DeepFM (Guo et al. 2017): FM 2nd-order + DNN deep, sharing embeddings.
Architecture:
    FM branch: 1st order (linear) + 2nd order (pairwise inner product, efficient form)
    DNN branch: concat of all embeddings + side features → MLP [256, 128, 64] → sigmoid
    Output: sigmoid(FM + DNN)

Usage:
    # Single run with explicit config
    python scripts/train_deepfm.py \\
        --emb-dim 8 --dropout 0.2 --l2 1e-4 --neg-ratio 4 --epochs 10

    # Sweep mode (Stage A: embedding_dim grid)
    python scripts/train_deepfm.py --sweep emb_dim

    # Sweep mode (Stage B: dropout × L2 grid, fixed best dim)
    python scripts/train_deepfm.py --sweep dropout_l2 --emb-dim 8

    # Final config retrain on train+val merged
    python scripts/train_deepfm.py --final --emb-dim 8 --dropout 0.2 --l2 1e-4

    # Ablation: drop user_id embedding (verify H6)
    python scripts/train_deepfm.py --ablation no_user_id

Outputs:
    models/deepfm_{tag}.pt           — model checkpoints per config
    models/deepfm_{tag}_history.json — training curve per config
    models/deepfm_sweep_{stage}.json — sweep summary
    reports/figures/training_deepfm_*.png  — learning curves + sweep heatmaps
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

SEED = 42
DEVICE = (
    "mps" if torch.backends.mps.is_available()
    else "cuda" if torch.cuda.is_available()
    else "cpu"
)


# =============================================================================
# DeepFM model
# =============================================================================
class DeepFM(nn.Module):
    """DeepFM = FM + DNN, sharing embedding layer.

    Key feature dimensions (from feature_spec.json):
      - user_id (cardinality ~359K) → embedding (emb_dim)
      - item_id (cardinality ~9K) → embedding (emb_dim)
      - user_num: 6 numeric scalar features
      - user_cuisine: 50-dim multi-hot (fav_cuisine_emb)
      - item_num: 7 numeric scalar features
      - item_cat: 50-dim multi-hot (categories)

    For FM 2nd-order, we use the simplest reliable form:
      - 4 'fields' get pairwise inner product:
        user_emb, item_emb, user_num_proj, item_num_proj
      where user_num_proj / item_num_proj are linear projections of numeric features
      to emb_dim space. Multi-hot features feed into the linear (1st-order) and DNN
      branches but not pairwise FM (would explode the term count).

    Reference: Guo et al. 2017 — DeepFM.
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        emb_dim: int = 8,
        user_num_dim: int = 6,
        user_cuisine_dim: int = 50,
        item_num_dim: int = 7,
        item_cat_dim: int = 50,
        dnn_hidden: tuple[int, ...] = (256, 128, 64),
        dropout: float = 0.2,
        ablate_user_id: bool = False,
    ):
        super().__init__()
        self.emb_dim = emb_dim
        self.ablate_user_id = ablate_user_id

        # Shared embeddings for FM + DNN
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)

        # Project numeric features to emb_dim space (so FM 2nd-order works)
        self.user_num_proj = nn.Linear(user_num_dim, emb_dim)
        self.item_num_proj = nn.Linear(item_num_dim, emb_dim)

        # 1st-order linear weights (FM order-1)
        feat_dim_linear = (
            user_num_dim + item_num_dim + user_cuisine_dim + item_cat_dim
        )
        self.linear_features = nn.Linear(feat_dim_linear, 1)
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        # DNN branch: input is flattened concat of 4 emb fields + 2 multi-hot
        dnn_input_dim = (
            emb_dim * 4 + user_cuisine_dim + item_cat_dim
        )  # user_emb + item_emb + user_num_proj + item_num_proj + user_cuisine + item_cat
        layers = []
        prev = dnn_input_dim
        for h in dnn_hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.dnn = nn.Sequential(*layers)

        # Init
        nn.init.normal_(self.user_emb.weight, std=0.01)
        nn.init.normal_(self.item_emb.weight, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.item_bias.weight)

    def forward(
        self,
        user_idx: torch.Tensor,
        item_idx: torch.Tensor,
        user_num: torch.Tensor,
        user_cuisine: torch.Tensor,
        item_num: torch.Tensor,
        item_cat: torch.Tensor,
    ) -> torch.Tensor:
        B = user_idx.size(0)

        # ---- Embedding lookup ----
        u_emb = self.user_emb(user_idx)            # (B, k)
        i_emb = self.item_emb(item_idx)            # (B, k)
        un_emb = self.user_num_proj(user_num)      # (B, k)
        in_emb = self.item_num_proj(item_num)      # (B, k)

        if self.ablate_user_id:
            u_emb = torch.zeros_like(u_emb)

        # ---- FM order-1: linear over numeric + multi-hot features ----
        feat_concat = torch.cat([user_num, item_num, user_cuisine, item_cat], dim=-1)
        order1 = self.linear_features(feat_concat).squeeze(-1)            # (B,)
        bu = self.user_bias(user_idx).squeeze(-1)
        bi = self.item_bias(item_idx).squeeze(-1)
        if self.ablate_user_id:
            bu = torch.zeros_like(bu)

        # ---- FM order-2: pairwise inner product over 4 emb fields ----
        # Efficient form: 0.5 * [(sum)² - sum(²)]
        embs = torch.stack([u_emb, i_emb, un_emb, in_emb], dim=1)  # (B, 4, k)
        sum_sq = embs.sum(dim=1) ** 2                              # (B, k)
        sq_sum = (embs ** 2).sum(dim=1)                            # (B, k)
        order2 = 0.5 * (sum_sq - sq_sum).sum(dim=-1)               # (B,)

        # ---- DNN: concat all → MLP ----
        dnn_input = torch.cat(
            [u_emb, i_emb, un_emb, in_emb, user_cuisine, item_cat], dim=-1
        )
        dnn_output = self.dnn(dnn_input).squeeze(-1)               # (B,)

        return torch.sigmoid(order1 + order2 + dnn_output + bu + bi + self.global_bias)


# =============================================================================
# Training + eval (reused from train_baselines pattern)
# =============================================================================
def make_feature_kwargs_fn(dataset: TasteHunterDataset):
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


def train_one_config(
    config: dict,
    n_users: int,
    n_items: int,
    train_loader: DataLoader,
    user_idx_eval, item_idx_eval, label_eval,
    feature_kwargs_fn,
    device: str = DEVICE,
) -> dict:
    """Train DeepFM with given config, return history."""
    log.info("Training DeepFM with config: %s", config)
    torch.manual_seed(SEED)
    model = DeepFM(
        n_users, n_items,
        emb_dim=config["emb_dim"],
        dropout=config["dropout"],
        ablate_user_id=config.get("ablate_user_id", False),
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.get("lr", 1e-3),
        weight_decay=config["l2"],
    )
    bce = nn.BCELoss()
    epochs = config.get("epochs", 10)
    history = {"epoch": [], "train_loss": [], "val_auc": [], "val_ndcg10": [], "val_recall10": []}
    best_ndcg = -1
    patience = config.get("patience", 3)
    bad_epochs = 0

    for epoch in range(1, epochs + 1):
        model.train()
        loss_sum, n_batch = 0.0, 0
        t0 = time.time()
        for batch in train_loader:
            u = batch["user_idx"].to(device)
            i = batch["item_idx"].to(device)
            y = batch["label"].to(device)
            kwargs = {k: batch[k].to(device) for k in ("user_num", "user_cuisine", "item_num", "item_cat")}
            pred = model(u, i, **kwargs)
            loss = bce(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            loss_sum += loss.item()
            n_batch += 1
        train_loss = loss_sum / max(n_batch, 1)
        elapsed = time.time() - t0

        metrics = evaluate_full(
            model, user_idx_eval, item_idx_eval, label_eval,
            device=device, feature_kwargs_fn=feature_kwargs_fn,
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

        # Early stopping on val NDCG@10
        if metrics["NDCG@10"] > best_ndcg:
            best_ndcg = metrics["NDCG@10"]
            bad_epochs = 0
            history["best_state_dict"] = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                log.info("  early stopping at epoch %d (no NDCG@10 improvement for %d epochs)", epoch, patience)
                break

    history["best_ndcg10"] = best_ndcg
    history["config"] = config
    return history


def setup_data():
    """One-time data load shared across configs."""
    user_features = pd.read_parquet(FEATURES_DIR / "user_features.parquet")
    item_features = pd.read_parquet(FEATURES_DIR / "item_features.parquet")
    val_df = pd.read_parquet(CLEANED_DIR / "val_reviews.parquet")
    train_df = pd.read_parquet(FEATURES_DIR / "train_with_negatives.parquet")

    user_encoder, item_encoder = build_encoders(user_features, item_features)
    n_users, n_items = len(user_encoder), len(item_encoder)
    log.info("Encoders: %d users, %d items", n_users, n_items)

    user_idx_eval, item_idx_eval, label_eval = make_val_eval_pairs(
        val_df, user_encoder, item_encoder, item_features, n_negs=99,
    )

    train_ds = TasteHunterDataset(
        train_df, user_encoder, item_encoder,
        with_features=True, user_features=user_features, item_features=item_features,
    )
    train_loader = DataLoader(train_ds, batch_size=8192, shuffle=True, num_workers=0, pin_memory=True)
    feature_kwargs_fn = make_feature_kwargs_fn(train_ds)

    return n_users, n_items, train_loader, user_idx_eval, item_idx_eval, label_eval, feature_kwargs_fn


def run_single(args):
    """Single config run."""
    n_users, n_items, train_loader, ue, ie, le, fkfn = setup_data()
    config = {
        "emb_dim": args.emb_dim,
        "dropout": args.dropout,
        "l2": args.l2,
        "neg_ratio": args.neg_ratio,
        "epochs": args.epochs,
        "lr": args.lr,
    }
    h = train_one_config(config, n_users, n_items, train_loader, ue, ie, le, fkfn)
    tag = f"emb{args.emb_dim}_drop{args.dropout}_l2{args.l2}"
    if args.ablation:
        tag += f"_ablate-{args.ablation}"
    save_history_and_model(h, tag)


def run_sweep_emb_dim(args):
    """Stage A: sweep embedding_dim in {4, 8, 16, 32}."""
    n_users, n_items, train_loader, ue, ie, le, fkfn = setup_data()
    results = []
    for emb_dim in [4, 8, 16, 32]:
        log.info("=" * 60)
        log.info("Sweep — emb_dim = %d", emb_dim)
        log.info("=" * 60)
        config = {
            "emb_dim": emb_dim,
            "dropout": 0.2,
            "l2": 1e-4,
            "epochs": args.epochs,
        }
        h = train_one_config(config, n_users, n_items, train_loader, ue, ie, le, fkfn)
        tag = f"emb{emb_dim}_drop0.2_l21e-4"
        save_history_and_model(h, tag)
        results.append({"emb_dim": emb_dim, "best_ndcg10": h["best_ndcg10"], "tag": tag})

    with open(MODELS_DIR / "deepfm_sweep_emb_dim.json", "w") as f:
        json.dump(results, f, indent=2)
    log.info("Stage A complete:")
    for r in results:
        log.info("  emb_dim=%d → best_ndcg10=%.4f", r["emb_dim"], r["best_ndcg10"])
    best = max(results, key=lambda x: x["best_ndcg10"])
    log.info("  → best emb_dim = %d", best["emb_dim"])


def run_sweep_dropout_l2(args):
    """Stage B: sweep dropout × L2 grid (fixed emb_dim from Stage A)."""
    n_users, n_items, train_loader, ue, ie, le, fkfn = setup_data()
    grid = [(d, l) for d in [0.1, 0.2, 0.3, 0.4, 0.5] for l in [1e-5, 1e-4, 5e-4, 1e-3]]
    log.info("Stage B sweep: %d configs", len(grid))
    results = []
    for d, l in grid:
        log.info("  dropout=%.2f, l2=%.0e", d, l)
        config = {
            "emb_dim": args.emb_dim,
            "dropout": d,
            "l2": l,
            "epochs": args.epochs,
        }
        h = train_one_config(config, n_users, n_items, train_loader, ue, ie, le, fkfn)
        tag = f"emb{args.emb_dim}_drop{d}_l2{l}"
        save_history_and_model(h, tag)
        results.append({"emb_dim": args.emb_dim, "dropout": d, "l2": l, "best_ndcg10": h["best_ndcg10"], "tag": tag})

    with open(MODELS_DIR / "deepfm_sweep_dropout_l2.json", "w") as f:
        json.dump(results, f, indent=2)
    log.info("Stage B complete:")
    for r in sorted(results, key=lambda x: -x["best_ndcg10"])[:5]:
        log.info("  emb=%d drop=%.2f l2=%.0e → best_ndcg10=%.4f",
                 r["emb_dim"], r["dropout"], r["l2"], r["best_ndcg10"])

    plot_sweep_heatmap(results)


def run_ablation(args):
    """Phase 5.5: H6 ablation — drop user_id embedding, eval on cold-start subset."""
    n_users, n_items, train_loader, ue, ie, le, fkfn = setup_data()
    log.info("=" * 60)
    log.info("Ablation: drop user_id embedding (verify H6)")
    log.info("=" * 60)
    config = {
        "emb_dim": args.emb_dim,
        "dropout": args.dropout,
        "l2": args.l2,
        "epochs": args.epochs,
        "ablate_user_id": True,
    }
    h = train_one_config(config, n_users, n_items, train_loader, ue, ie, le, fkfn)
    tag = "ablation_no_user_id"
    save_history_and_model(h, tag)


def save_history_and_model(history: dict, tag: str):
    state = history.pop("best_state_dict", None)
    if state is not None:
        torch.save(state, MODELS_DIR / f"deepfm_{tag}.pt")
    with open(MODELS_DIR / f"deepfm_{tag}_history.json", "w") as f:
        json.dump(history, f, indent=2)
    log.info("  saved: models/deepfm_%s.pt + _history.json", tag)


def plot_sweep_heatmap(results: list[dict]):
    dropouts = sorted({r["dropout"] for r in results})
    l2s = sorted({r["l2"] for r in results})
    M = np.zeros((len(dropouts), len(l2s)))
    for r in results:
        M[dropouts.index(r["dropout"]), l2s.index(r["l2"])] = r["best_ndcg10"]
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(M, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(l2s)))
    ax.set_xticklabels([f"{l:.0e}" for l in l2s])
    ax.set_yticks(range(len(dropouts)))
    ax.set_yticklabels(dropouts)
    ax.set_xlabel("L2 weight")
    ax.set_ylabel("Dropout")
    ax.set_title("Stage B sweep: best NDCG@10 over (dropout × L2)")
    for i in range(len(dropouts)):
        for j in range(len(l2s)):
            ax.text(j, i, f"{M[i,j]:.3f}", ha="center", va="center", color="white", fontsize=9)
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "training_deepfm_sweep_heatmap.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--emb-dim", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--neg-ratio", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--sweep", choices=["emb_dim", "dropout_l2"], default=None)
    parser.add_argument("--ablation", choices=["no_user_id"], default=None)
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if args.sweep == "emb_dim":
        run_sweep_emb_dim(args)
    elif args.sweep == "dropout_l2":
        run_sweep_dropout_l2(args)
    elif args.ablation:
        run_ablation(args)
    else:
        run_single(args)
