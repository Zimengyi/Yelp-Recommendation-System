# Taste hunter — Yelp Recommendation System

> ML2 (ADSP 31018) Spring 2026 final project · Prof. Arnab Bose · UChicago MS-ADS
> **Team**: Haobo Yang (model + PRD) · Zimeng (EDA) · Cindy (EDA)
> **Deadline**: 2026-05-23 · **Repo**: https://github.com/Zimengyi/Yelp-Recommendation-System

---

## What this is

A **conversational restaurant recommender system** built on the Yelp Open Dataset. Architecture:

- **Single DeepFM ranker** trained on ~7M Yelp reviews — covers ML2 rubric "deep learning OR recommender system (hybrid or factorization machine)" both keywords
- **Dual-path recall** sharing one DeepFM精排:
  - **S1 push路** (user lands on home screen): Two-Tower / DSSM dense retrieval (stretch)
  - **S2/S6 conversational路**: LLM intent extraction → SQL-style hard filter → DeepFM
- **MMR re-ranking** (stretch): for F2 trip-plan per-period top-3 candidate diversity
- **LLM agent** (Anthropic claude-sonnet-4-6): intent extraction + response synthesis

Full design docs in [`docs/`](docs/). See [`docs/training_pipeline_plan.md`](docs/training_pipeline_plan.md) for the 18-day implementation plan.

## Project structure

```
.
├── docs/                  # PRD + explainer + plan + design notes
│   ├── prd/               # PRD v1 + 4 v2 sections
│   ├── recommender_training_explainer.md
│   ├── training_pipeline_plan.md
│   └── ...
├── data/
│   ├── raw/               # Yelp Open Dataset JSON files (gitignored, ~9GB)
│   ├── cleaned/           # Phase 1 output: filtered parquet
│   └── features/          # Phase 3 output: feature tables + cuisine_vocab
├── notebooks/             # EDA + sweep result analysis
├── scripts/               # Reproducible training / eval scripts
├── src/                   # Reusable library code
├── tests/                 # Unit tests for data prep functions
├── models/                # Trained checkpoints (gitignored)
└── reports/               # Final report draft + figures
```

## Setup

### 1. Python environment

```bash
# Create venv (Python 3.10+)
python3 -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### 2. Get Yelp data

The Yelp Open Dataset is **not committed** (~9GB). Download from https://www.yelp.com/dataset and extract:

```bash
# Place the tar in data/raw/
mkdir -p data/raw
mv ~/Downloads/yelp_dataset.tar data/raw/
cd data/raw && tar -xf yelp_dataset.tar
```

You should end up with:
- `data/raw/yelp_academic_dataset_business.json` (~113MB, 150K rows)
- `data/raw/yelp_academic_dataset_user.json` (~3.1GB, 2M rows)
- `data/raw/yelp_academic_dataset_review.json` (~5GB, 7M rows)
- `data/raw/yelp_academic_dataset_tip.json` (~228MB, 908K rows)
- `data/raw/yelp_academic_dataset_checkin.json` (~408MB, 131K rows)

### 3. Run Phase 1 data prep

```bash
python scripts/prepare_data.py --cities Philadelphia,Tucson,Tampa
```

This produces `data/cleaned/{businesses_target,reviews_restaurant,users_target,train,val,test,coldstart_test,crosscity_test}.parquet`.

## Implementation phases

Per [`docs/training_pipeline_plan.md`](docs/training_pipeline_plan.md):

| Phase | Date | Deliverable | Owner |
|---|---|---|---|
| 1. Data prep | 5/6–5/8 | filter parquet | Haobo |
| 2. EDA | 5/6–5/11 | 11 Q answers + 8 figures | Zimeng + Cindy |
| 3. Feature engineering | 5/9–5/11 | feature tables + spec | Haobo |
| 4. Baselines (MF/FM) | 5/12–5/13 | val metrics | Haobo |
| 5. DeepFM + sweep | 5/14–5/16 | final config + ablation | Haobo |
| 6. Two-Tower + MMR | 5/17–5/18 | stretch | Haobo |
| 7. Test eval | 5/19 | hold-out metrics | Haobo |
| 8. Agent + demo | 5/20–5/21 | Streamlit + Likert | All |
| 9. Writeup | 5/22 | final report | Haobo |
| 10. Submit | 5/23 | Canvas submission | Haobo |

## Target cities

We target **3 US cities** with sufficient Yelp coverage:

| City | State | Business count |
|---|---|---|
| Philadelphia | PA | 14,570 |
| Tucson | AZ | 9,252 |
| Tampa | FL | 9,051 |

(Decision rationale: see [`docs/training_pipeline_plan.md`](docs/training_pipeline_plan.md) §1.4 + risk R3)

## Contributing

For Zimeng / Cindy:

- **EDA notebooks**: place in `notebooks/01_eda_*.ipynb`
- **Branching**: feature branches off `main`, PR to merge (small project = lightweight workflow)
- **Style**: format with `black .`, lint with `ruff check .` before commit

## License

Class project — internal use only. Yelp Open Dataset usage is governed by the [Yelp Open Dataset Terms](https://www.yelp.com/dataset/download).
