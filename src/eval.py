"""Evaluation metrics for ranking models.

Provides:
- compute_auc(scores, labels): pairwise AUC across all (user, item) pairs
- compute_ranking_metrics(score_matrix, label_matrix, k=10): NDCG@k / Recall@k / Precision@k
  - Inputs are 2D arrays of shape (n_users, n_candidates) where label has 1 positive + (k-1) negatives
- evaluate_full(): runs all metrics + cold-start AUC subset
"""

from __future__ import annotations

import logging

import numpy as np
import torch

log = logging.getLogger(__name__)


def compute_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Pairwise AUC: P(score(positive) > score(negative)) over all positive-negative pairs.

    Approximation: rank-based formula AUC = (rank_sum_positives - n_pos*(n_pos+1)/2) / (n_pos*n_neg).
    """
    pos_mask = labels > 0.5
    n_pos = pos_mask.sum()
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    # rank by score (highest = rank 1, ascending below)
    order = np.argsort(scores)  # ascending
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)  # rank from 1
    rank_sum_pos = ranks[pos_mask].sum()
    auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def ndcg_at_k(score_matrix: np.ndarray, label_matrix: np.ndarray, k: int = 10) -> float:
    """NDCG@k for ranking with (n_users, n_candidates).

    Each row: candidates for one user; label_matrix has 1 at the true positive position(s).
    For our setup with 1 positive + 99 negatives, IDCG@k = 1/log2(2) = 1.
    """
    # Get top-k items per row (descending by score)
    top_k_idx = np.argsort(-score_matrix, axis=1)[:, :k]  # (n_users, k)
    rows = np.arange(score_matrix.shape[0])[:, None]
    top_k_labels = label_matrix[rows, top_k_idx]  # (n_users, k)

    # DCG@k: sum_i (2^rel_i - 1) / log2(i+2)
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = (top_k_labels * discounts).sum(axis=1)

    # IDCG@k: ideal sorted (1 positive in our setup → idcg = 1/log2(2) = 1)
    ideal_labels = -np.sort(-label_matrix, axis=1)[:, :k]
    idcg = (ideal_labels * discounts).sum(axis=1)
    idcg = np.where(idcg > 0, idcg, 1.0)  # avoid div0

    return float(np.mean(dcg / idcg))


def recall_at_k(score_matrix: np.ndarray, label_matrix: np.ndarray, k: int = 10) -> float:
    """Recall@k: fraction of positives captured in top-k.

    For 1-positive-per-user eval: recall@k = 1 if positive is in top-k else 0.
    Average over users.
    """
    top_k_idx = np.argsort(-score_matrix, axis=1)[:, :k]
    rows = np.arange(score_matrix.shape[0])[:, None]
    top_k_labels = label_matrix[rows, top_k_idx]
    # Recall = (correct positives in top-k) / (total positives)
    n_positives_per_row = label_matrix.sum(axis=1)
    correct = top_k_labels.sum(axis=1)
    return float(np.mean(np.where(n_positives_per_row > 0, correct / n_positives_per_row, 0)))


def precision_at_k(score_matrix: np.ndarray, label_matrix: np.ndarray, k: int = 10) -> float:
    """Precision@k: fraction of top-k that are relevant."""
    top_k_idx = np.argsort(-score_matrix, axis=1)[:, :k]
    rows = np.arange(score_matrix.shape[0])[:, None]
    top_k_labels = label_matrix[rows, top_k_idx]
    return float(top_k_labels.mean())


@torch.no_grad()
def score_pairs_with_model(
    model: torch.nn.Module,
    user_idx: np.ndarray,  # (n_users, n_candidates)
    item_idx: np.ndarray,  # (n_users, n_candidates)
    device: str = "cpu",
    batch_size: int = 8192,
    feature_kwargs_fn=None,  # optional callable taking (u_flat, i_flat) → kwargs dict
) -> np.ndarray:
    """Score (user, item) pairs with a model, return (n_users, n_candidates) score matrix."""
    model.eval()
    n, c = user_idx.shape
    flat_u = user_idx.reshape(-1)
    flat_i = item_idx.reshape(-1)
    scores = np.zeros(n * c, dtype=np.float32)

    for start in range(0, len(flat_u), batch_size):
        end = min(start + batch_size, len(flat_u))
        u_b = torch.from_numpy(flat_u[start:end]).to(device)
        i_b = torch.from_numpy(flat_i[start:end]).to(device)
        kwargs = {}
        if feature_kwargs_fn is not None:
            kwargs = feature_kwargs_fn(flat_u[start:end], flat_i[start:end])
            kwargs = {k: v.to(device) for k, v in kwargs.items()}
        s = model(u_b, i_b, **kwargs).cpu().numpy().reshape(-1)
        scores[start:end] = s

    return scores.reshape(n, c)


def evaluate_full(
    model: torch.nn.Module,
    user_idx_eval: np.ndarray,
    item_idx_eval: np.ndarray,
    label_eval: np.ndarray,
    device: str = "cpu",
    feature_kwargs_fn=None,
) -> dict:
    """Full evaluation: AUC + NDCG@10 + Recall@10 + Precision@10."""
    score_matrix = score_pairs_with_model(
        model, user_idx_eval, item_idx_eval, device=device, feature_kwargs_fn=feature_kwargs_fn
    )

    # AUC over all flattened pairs
    auc = compute_auc(score_matrix.reshape(-1), label_eval.reshape(-1))

    metrics = {
        "AUC": auc,
        "NDCG@10": ndcg_at_k(score_matrix, label_eval, k=10),
        "Recall@10": recall_at_k(score_matrix, label_eval, k=10),
        "Precision@10": precision_at_k(score_matrix, label_eval, k=10),
        "Recall@5": recall_at_k(score_matrix, label_eval, k=5),
    }
    return metrics
