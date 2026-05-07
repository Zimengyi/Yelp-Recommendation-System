"""Dataset loaders for training pipeline.

Provides:
- TasteHunterDataset: PyTorch Dataset wrapping train_with_negatives.parquet
- IDEncoder: maps user_id / business_id strings → integer indices
- load_data(): one-call entry returning (train, val, test) DataLoaders + encoders
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"


class IDEncoder:
    """Map string IDs (user_id / business_id) to integer indices.

    Reserves index 0 for <UNK> / <NEW_USER> / <NEW_BUSINESS> OOV cases.
    """

    def __init__(self, ids: list[str], oov_token: str = "<UNK>"):
        self.oov_token = oov_token
        # index 0 reserved for OOV; real ids start at 1
        # filter out any explicit OOV markers in the input list (they map to 0)
        oov_markers = {"<NEW_USER>", "<NEW_BUSINESS>", "<UNK>", oov_token}
        unique_real_ids = sorted({i for i in ids if i not in oov_markers})
        self.id_to_idx: dict[str, int] = {oov_token: 0}
        for idx, _id in enumerate(unique_real_ids, start=1):
            self.id_to_idx[_id] = idx
        # Also map common OOV markers to 0 so encoding "<NEW_USER>" works
        for marker in oov_markers:
            self.id_to_idx.setdefault(marker, 0)
        self.idx_to_id = {0: oov_token}
        for _id, idx in self.id_to_idx.items():
            if idx > 0:
                self.idx_to_id[idx] = _id
        self._size = 1 + len(unique_real_ids)  # OOV + real ids

    def __len__(self) -> int:
        return self._size

    def encode(self, _id: str) -> int:
        return self.id_to_idx.get(_id, 0)  # fallback to OOV

    def encode_array(self, ids: pd.Series) -> np.ndarray:
        return ids.map(self.id_to_idx).fillna(0).astype(np.int64).values


class TasteHunterDataset(Dataset):
    """Wraps a (user_id, business_id, label) parquet for PyTorch training.

    Optionally joins user / item features from the precomputed parquets for FM/DeepFM.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        user_encoder: IDEncoder,
        item_encoder: IDEncoder,
        with_features: bool = False,
        user_features: pd.DataFrame | None = None,
        item_features: pd.DataFrame | None = None,
    ):
        self.user_idx = torch.from_numpy(user_encoder.encode_array(df["user_id"]))
        self.item_idx = torch.from_numpy(item_encoder.encode_array(df["business_id"]))
        self.label = torch.from_numpy(df["label"].astype(np.float32).values)
        self.with_features = with_features

        if with_features:
            assert user_features is not None and item_features is not None
            # Build lookup arrays (idx → feature vector)
            n_users = len(user_encoder)
            n_items = len(item_encoder)

            # User numeric features: 5 direct + 3 aggregated (excluding fav_cuisine_emb which is vector)
            self.user_num = np.zeros((n_users, 6), dtype=np.float32)  # avg_rating_given, review_count_log, days_active, elite_flag, mean_distance_traveled, price_tolerance_avg
            self.user_cuisine = np.zeros((n_users, 50), dtype=np.float32)  # fav_cuisine_emb

            for _, row in user_features.iterrows():
                uidx = user_encoder.encode(row["user_id"])
                self.user_num[uidx] = [
                    row["avg_rating_given"],
                    row["review_count_log"],
                    row["days_active"],
                    row["elite_flag"],
                    row["mean_distance_traveled"],
                    row["price_tolerance_avg"],
                ]
                emb = row["fav_cuisine_emb"]
                if isinstance(emb, list) and len(emb) == 50:
                    self.user_cuisine[uidx] = emb

            # Item numeric: avg_rating, review_count_log, price_level, is_open, has_outdoor_seating, photo_count_log, city_id
            self.item_num = np.zeros((n_items, 7), dtype=np.float32)
            self.item_cat = np.zeros((n_items, 50), dtype=np.float32)  # categories_multi_hot

            for _, row in item_features.iterrows():
                iidx = item_encoder.encode(row["business_id"])
                self.item_num[iidx] = [
                    row["avg_rating"],
                    row["review_count_log"],
                    row["price_level"],
                    row["is_open"],
                    row["has_outdoor_seating"],
                    row["photo_count_log"],
                    row["city_id"],
                ]
                cat = row["categories_multi_hot"]
                if isinstance(cat, list) and len(cat) == 50:
                    self.item_cat[iidx] = cat

            self.user_num_t = torch.from_numpy(self.user_num)
            self.user_cuisine_t = torch.from_numpy(self.user_cuisine)
            self.item_num_t = torch.from_numpy(self.item_num)
            self.item_cat_t = torch.from_numpy(self.item_cat)

    def __len__(self) -> int:
        return len(self.label)

    def __getitem__(self, idx: int) -> dict:
        u = self.user_idx[idx]
        i = self.item_idx[idx]
        item = {"user_idx": u, "item_idx": i, "label": self.label[idx]}
        if self.with_features:
            item["user_num"] = self.user_num_t[u]
            item["user_cuisine"] = self.user_cuisine_t[u]
            item["item_num"] = self.item_num_t[i]
            item["item_cat"] = self.item_cat_t[i]
        return item


def build_encoders(user_features: pd.DataFrame, item_features: pd.DataFrame) -> Tuple[IDEncoder, IDEncoder]:
    """Build id encoders from precomputed feature tables (so OOV rows are included)."""
    user_encoder = IDEncoder(user_features["user_id"].tolist(), oov_token="<NEW_USER>")
    item_encoder = IDEncoder(item_features["business_id"].tolist(), oov_token="<NEW_BUSINESS>")
    log.info("Built encoders: %d users, %d items", len(user_encoder), len(item_encoder))
    return user_encoder, item_encoder


def make_val_eval_pairs(
    val_df: pd.DataFrame,
    user_encoder: IDEncoder,
    item_encoder: IDEncoder,
    item_features: pd.DataFrame,
    n_negs: int = 99,
    rng_seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build (user × candidates) eval pairs for ranking metrics.

    For each val positive (rating ≥ 4), generate 1 + n_negs candidates.
    Returns:
        all_user_idx: (n_val × (1+n_negs),) int64
        all_item_idx: (n_val × (1+n_negs),) int64
        all_label:    (n_val × (1+n_negs),) float32 — first column is 1, rest 0
    Reshape to (n_val, 1+n_negs) for per-user ranking.
    """
    rng = np.random.default_rng(rng_seed)

    # Filter val to positives only
    val_pos = val_df[val_df["stars"] >= 4].copy()
    log.info("Val positives: %d", len(val_pos))

    # Build city → biz lookup for negative sampling
    biz_city = item_features.set_index("business_id")["city"].to_dict()
    val_pos["city"] = val_pos["business_id"].map(biz_city).fillna("<UNK>")
    city_biz = {}
    for bid, c in biz_city.items():
        if c == "<UNK>":
            continue
        city_biz.setdefault(c, []).append(bid)
    for c in city_biz:
        city_biz[c] = np.array(city_biz[c])

    n = len(val_pos)
    all_user, all_item, all_label = [], [], []
    for row in val_pos.itertuples(index=False):
        if row.city not in city_biz:
            continue
        # 1 positive + n_negs negatives
        candidates_pool = city_biz[row.city]
        sampled = rng.choice(candidates_pool, size=n_negs * 2, replace=True)
        # Filter out the actual positive
        negs = [b for b in sampled if b != row.business_id][:n_negs]
        if len(negs) < n_negs:
            continue
        items = [row.business_id] + negs
        all_user.append([user_encoder.encode(row.user_id)] * (n_negs + 1))
        all_item.append([item_encoder.encode(b) for b in items])
        all_label.append([1.0] + [0.0] * n_negs)

    user_arr = np.array(all_user, dtype=np.int64)
    item_arr = np.array(all_item, dtype=np.int64)
    label_arr = np.array(all_label, dtype=np.float32)
    log.info(
        "Built eval pairs: %d val users × %d candidates each",
        user_arr.shape[0],
        user_arr.shape[1],
    )
    return user_arr, item_arr, label_arr


def load_train_loader(
    user_encoder: IDEncoder,
    item_encoder: IDEncoder,
    user_features: pd.DataFrame | None = None,
    item_features: pd.DataFrame | None = None,
    with_features: bool = False,
    batch_size: int = 4096,
    num_workers: int = 0,
) -> DataLoader:
    """Load train_with_negatives.parquet → DataLoader."""
    train_df = pd.read_parquet(FEATURES_DIR / "train_with_negatives.parquet")
    log.info("Loaded %d training rows from train_with_negatives.parquet", len(train_df))
    ds = TasteHunterDataset(
        train_df,
        user_encoder,
        item_encoder,
        with_features=with_features,
        user_features=user_features,
        item_features=item_features,
    )
    return DataLoader(ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
