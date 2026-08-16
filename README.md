# TitlePulse

Predicting YouTube title engagement, normalized for channel size — isolating what a *title* actually contributes to a video's performance, separate from a channel's existing audience or reach.

> **Status:** Model training and evaluation complete. Backend/frontend built and functional locally. Live deployment is currently paused while I finalize a hosting setup — see [Running Locally](#running-locally) below in the meantime.

## The Problem

YouTube performance is heavily shaped by title and thumbnail quality, but creators have no data-driven way to evaluate a title before publishing. Raw view count is a bad measure of "good title" on its own — it mostly reflects channel size and existing subscriber reach, not the title itself. TitlePulse isolates the title's effect by normalizing engagement against each channel's own typical performance.

## What It Does

Paste in a YouTube title, get back:
- A predicted **engagement score** (how the title is likely to perform relative to the channel's own baseline)
- A **percentile ranking** against ~11,000 real YouTube videos in the training dataset
- A plain-language interpretation (e.g. "above average")

## Results

| Metric | Value |
|---|---|
| Spearman correlation (predicted vs. actual, held-out test set) | **0.246** |
| Test set size | 2,235 videos (temporal split — most recent 20%) |
| Training set size | ~8,900 videos |

**0.246 is a real, statistically robust signal**, not a strong one — and that's expected. The model uses *title text alone*, deliberately excluding thumbnail, publish timing, algorithm/recommendation dynamics, and trending context — all of which meaningfully drive virality but aren't captured here. A much higher correlation from text alone would actually be more suspicious (likely data leakage) than reassuring.

### Model comparison

| Model | Overall Spearman | Notes |
|---|---|---|
| Ridge Regression (TF-IDF + numeric features) | **0.246** | **Production model** — chosen for near-identical performance to LightGBM with much lower complexity |
| LightGBM (same features) | 0.244 | Near-identical to Ridge, suggesting the underlying relationship is largely linear |
| Sentence embeddings only (MiniLM) | 0.135 | Underperformed TF-IDF — general-purpose semantic embeddings don't capture the literal phrasing/keyword patterns that seem to matter most for this task |
| Embeddings + TF-IDF combined | 0.252 | Marginal improvement over TF-IDF alone, not judged worth the added inference complexity for a small gain |

Performance also varies by channel size tier — strongest on small/mid-sized channels (Spearman ~0.26–0.29), weaker on large/outlier-tier channels (~0.17–0.19), where breakout virality is likely driven more by algorithmic push and external reach than title text.

### A specific limitation, measured directly

~20% of the collected dataset consists of **Hinglish titles** (Hindi vocabulary written in Latin script, common among Indian YouTube channels). The model performs measurably worse on this subset:

| Group | Spearman | MAE | n |
|---|---|---|---|
| Non-Hinglish titles | 0.264 | 0.273 | 1,857 |
| Hinglish titles | 0.175 | 0.338 | 378 |

This likely stems from two compounding issues: TF-IDF fragments inconsistent Latin-script transliterations of Hindi words into sparse, low-signal tokens, and the sentence embedding model (trained predominantly on English text) handles code-mixed input poorly. Adding a `likely_hinglish` binary flag as a model feature was tested as a low-cost mitigation. This is flagged as a known limitation and a natural direction for future work (e.g. spelling normalization, a multilingual tokenizer/embedding model).

## How It Works

1. **Channel discovery & data collection** — YouTube Data API v3, automated discovery across niche keywords (tech, gaming, and related categories), filtered by subscriber count into size tiers rather than manually curated
2. **Label engineering** — for each video, computed `views / channel's leave-one-out average views` (excluding that video from its own baseline to avoid a single viral hit inflating/distorting its own reference point), then log-transformed to tame the heavy right-skew typical of view-count data
3. **Baseline modeling** — TF-IDF (title text) + hand-crafted features (length, word count, punctuation/capitalization patterns) → Ridge Regression, evaluated on a **temporal** train/test split (train on older videos, test on newer ones) to mimic real deployment and avoid leakage
4. **Embedding experiment** — tested sentence-transformer embeddings as an alternative/addition; kept the simpler model after embeddings failed to justify their added complexity
5. **Diagnostic pass** — measured performance across channel size tiers and language composition to understand *where* the model does and doesn't work, rather than reporting a single blended number

## Tech Stack

- **Data & modeling:** Python, YouTube Data API v3, pandas, scikit-learn, LightGBM, sentence-transformers, scipy
- **Backend:** FastAPI
- **Frontend:** React, TypeScript, Vite, Tailwind CSS

## Project Structure

```
titlepulse/
├── data/
│   ├── raw/                  # collected channel/video data (gitignored)
│   └── processed/            # labeled, model-ready datasets
├── pipeline/
│   ├── youtube_client.py     # YouTube Data API wrapper
│   ├── discover_channels.py  # automated channel discovery
│   ├── collect.py            # video metadata collection
│   ├── label_engineering.py  # normalization + label construction
│   ├── baseline_model.py     # TF-IDF + Ridge/LightGBM training & eval
│   ├── embedding_model.py    # sentence-transformer experiment
│   └── language_diagnostic.py# Hinglish/language composition analysis
├── models/
│   └── baseline/             # trained model artifacts, evaluation results
├── backend/                  # FastAPI serving layer
├── frontend/                 # React/Vite demo UI
└── notebooks/
    └── eda.ipynb             # exploratory data analysis
```

## Running Locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_URL=http://localhost:8000
npm run dev
```

### Regenerating the dataset / retraining

Requires a free YouTube Data API v3 key ([console.cloud.google.com](https://console.cloud.google.com) → enable "YouTube Data API v3" → create an API key).

```bash
cp .env.example .env   # add YOUTUBE_API_KEY
python -m pipeline.discover_channels
python -m pipeline.collect
python -m pipeline.label_engineering
python -m pipeline.baseline_model
```

## Known Limitations & Future Work

- **Title text only** — no thumbnail, publish timing, or trend signal, which are known to meaningfully affect real-world performance
- **Hinglish/code-mixed titles** — measurably weaker performance on this ~20% subset (see above); a multilingual-aware tokenizer or spelling normalization is the natural next step
- **Subscriber counts are current, not historical** — collected at time of data pull, not at each video's original publish date, introducing some noise for older videos
- **No live deployment yet** — backend/frontend work locally end-to-end; hosting is being finalized

## Author

Built solo by Samyak Kapse as a portfolio project — data engineering, label design, baseline modeling, and full-stack delivery.
