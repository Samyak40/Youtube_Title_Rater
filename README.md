# TitleRater

TitleRater is an ML system that predicts how well a YouTube title will perform, normalized for channel size.

## Phase 1 Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your YouTube Data API v3 key:
   ```
   YOUTUBE_API_KEY=your_api_key_here
   ```
4. Review and edit `NICHE_KEYWORDS` in `pipeline/config.py` if desired.

## Running Phase 1

First, discover channels based on niche keywords:
```bash
python -m pipeline.discover_channels
```

Then, collect recent videos for those discovered channels:
```bash
python -m pipeline.collect
```

*Note: This is Phase 1 of a multi-phase project. Later phases will include label engineering, modeling, and web application interfaces.*
