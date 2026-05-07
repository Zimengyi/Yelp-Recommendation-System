# ML2 Class Project — Proposals (drafted 2026-05-01)

**Course**: ADSP 31018 Machine Learning II (Arnab Bose, Spring 2026)
**Weight**: 40% of final grade (40 points, 8 criteria × 5 pts)

## Rubric (must hit each in writeup)

1. Problem Statement
2. Assumptions / Hypotheses about data and model
3. Exploratory Data Analysis
4. Feature Engineering & Data Transformations
5. Proposed Approaches (Model) **with checks for overfitting/underfitting**
6. Proposed Solution (Model Selection) **with regularization, if needed**
7. Results (Accuracy) and Learnings from the methodology
8. Future Work

## Curriculum already covered (w1–w6, as of 2026-05-01)

- Bias-variance / overfitting / cross-validation (w1–w2)
- **Recommenders — Factorization Machines** (w3) ← project-eligible track
- ANN, backprop, weight init, batchnorm, L1/L2, dropout, hyperparam tuning (w3–w4)
- CNN + transfer learning + zero-shot (w5)
- RNN/LSTM/GRU + time-series forecasting + double descent (w6)

**Coming**: Transformers/embeddings/ViT (w7), VAE/GAN/LLM (w8), RL/causal/fairness (w9).

The project rubric says "deep learning OR recommender (hybrid / factorization machine)" — both routes are explicitly fair game.

---

## Proposal A — Pitch-by-pitch hit/miss prediction (CNN+LSTM hybrid on MLB Statcast)

**Problem**: Given a pitcher's prior pitch sequence + ball trajectory features at release, predict the binary outcome of the next pitch (hit-in-play vs miss/strike). Data: MLB Statcast (free via `pybaseball`), ~700K pitches per season.

**Why this fits the rubric well**:
- Sequence model (LSTM on prior 5–10 pitches) + dense head — covers w6 directly
- Strong overfitting/underfitting story (pitcher-level vs global model)
- Clear baseline (logistic regression on pitch type + velocity) → improved by deep model
- Class imbalance + temporal split for honest validation = easy "Assumptions" + "Feature Engineering" sections

**Risk**: Domain knowledge required. Haobo doesn't watch baseball. Skip if you don't enjoy the domain — rubric grades clarity, not topic coolness.

**Time**: 25–35h. Data is clean, lots of Kaggle precedents.

---

## Proposal B — Hybrid Recommender for Steam/MovieLens (Factorization Machine + DeepFM) ⭐ rubric-perfect

**Problem**: Recommend games (Steam-200K) or movies (MovieLens-25M) given user history. Build a **hybrid** that combines collaborative-filtering FM with content features (genre, tags, price) using **DeepFM** (FM + MLP shared embeddings).

**Why this is the highest-EV track**:
- Hits the syllabus literally — "Develop a deep learning **or recommender system (hybrid or factorization machine)** model"
- The professor wrote "factorization machine" into the rubric itself — strong signal he wants to see this
- Class 3 covered FM directly. DeepFM extends with deep network → "deep learning" component too. Two-for-one.
- Public dataset, no procurement risk
- Easy regularization story (L2 on embeddings, dropout in MLP)
- Easy overfitting story (train/val/test temporal split, holdout users)
- Metrics rubric: AUC + Recall@K + NDCG → "Results" criterion covered

**8-criteria coverage**:
1. Problem: cold-start + ranking on sparse implicit feedback
2. Hypotheses: latent factors capture preference, content helps cold-start
3. EDA: user/item activity distributions, sparsity heatmap, popularity bias
4. Feature eng: time-decay weights, genre TF-IDF, log-transform of price
5. Approach: FM baseline → DeepFM → sanity-check on overfit (train AUC vs val AUC gap)
6. Selection: dropout sweep, embedding-dim sweep, L2 weight, choose by val NDCG@10
7. Results: AUC / NDCG@10 / coverage / popularity-bias diagnostic
8. Future: contextual (session-based GRU4Rec), graph neural recommender

**Time**: 20–30h. Plenty of reference notebooks. Lowest risk, highest grade ceiling.

**Recommended dataset**: MovieLens-25M (clean, well-documented, stable) — or Steam if you want spice.

---

## Proposal C — Equity short-horizon return prediction (LSTM + tabular DNN ensemble) — your domain

**Problem**: Predict next-1-day directional return (up/down) for S&P 500 stocks using OHLCV + technical indicators + sector + sentiment features. Frame as binary classification with class-weighted log-loss.

**Why it's tempting**:
- Your domain (options trading, you already use yfinance/Alpaca daily)
- LSTM on 30-day price window + DNN on tabular features → ensemble. Hits w6 + w4.
- You can use *your own trade journal* in the discussion section — distinctive

**Why I'd pause**:
- Financial returns are notoriously low signal-to-noise. You can easily end up with AUC ~0.52 and a writeup that reads "DL didn't beat baseline" — which is *correct science* but harder to land an A on Criterion 7 (Results) without careful framing.
- Mitigation: **frame it as a regime-aware model**. Train per-sector + add a "market regime" feature (VIX bucket / breadth bucket). The story becomes "vanilla DL fails; regime-conditioned DL recovers signal in trending regimes" — that's a strong narrative even if accuracy is modest.

**Time**: 30–40h. Higher risk but rewarding if you nail the regime story.

---

## Proposal D — Vocal embedding-based singer-style classifier (CNN + Transformer head) — Capstone synergy

**Problem**: Classify singer-style attributes (gender, register, vibrato presence, breathiness) from short vocal clips using your existing **AF-Next encoder embeddings** as frozen features + a learned classifier head.

**Why this is the synergy play**:
- You already have AF-Next embeddings extracted (per memory `reference_af_next_vocalset_embed_shapes`) — most of the data work is done
- VocalSet has rich style labels — can frame as multi-task classification
- Transfer learning + zero-shot story (w5 covered both)
- Counts toward your **Capstone** too — kill two birds. Get explicit professor approval first since dual-submission rules vary.

**Risk**: small dataset (VocalSet ~10 singers) → easy to overfit. That's actually *good* for the rubric — gives you something to write about in Criteria 5 & 6.

**Time**: 20–25h since data prep is largely done.

---

## Recommendation

**Default pick: Proposal B (DeepFM hybrid recommender)**. Rubric-perfect, public data, lowest risk, professor explicitly invited recommenders. Plus Class 3 already gave you the FM scaffolding.

**If you want domain alignment** + can stomach modest accuracy: Proposal C (financial DL) with the regime-conditioning twist.

**If you want Capstone synergy** + low data risk: Proposal D — but **email Bose first** to confirm dual-submission is OK.

Skip Proposal A unless the baseball angle excites you.

---

## Next steps

1. Pick one (or tell me to draft Problem-Statement+EDA-plan for two of them in parallel)
2. Email Bose during his office hours to validate scope (he wrote "I am available to work with students on their project problem formulation and objectives" right above the grading scale — take him up on it)
3. Lock in dataset by end of next week so you have w7–w9 to build and write
