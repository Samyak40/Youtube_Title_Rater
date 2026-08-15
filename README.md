# TitlePulse (formerly TitleRater)

TitlePulse is an ML system that predicts how well a YouTube title will perform, normalized for channel size.

## How It Works (Phases 1-5)
This project is built in phases to create an end-to-end ML application:
1. **Data Collection**: Discovers channels and collects video metadata via the YouTube Data API v3.
2. **Label Engineering**: Normalizes raw views to create an `engagement_score` (log1p of views / channel's leave-one-out average views). This isolates the title's effect from the channel's inherent audience size.
3. **Baseline Modeling**: Hand-crafted numeric features combined with TF-IDF. 
   - **Headline Result**: Ridge Regression achieved an overall Spearman correlation of **0.246** on a held-out temporal test set.
4. **Embeddings Modeling**: Tested `all-MiniLM-L6-v2` sentence-transformer embeddings. 
   - **Model Choice Rationale**: The embeddings alone underperformed (0.135 Spearman), and combining them with TF-IDF offered only a marginal improvement (0.252) over TF-IDF alone (0.246). We chose the **Phase 3 TF-IDF Ridge model** for production due to its near-identical performance with drastically lower inference complexity and latency.
5. **Web Application**: A live scoring demo using FastAPI and React.

## Setup Instructions

### 1. Backend (FastAPI)
The backend loads the Phase 3 Ridge model and serves predictions.

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install backend requirements
pip install -r backend/requirements.txt

# Run the API server
uvicorn backend.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 2. Frontend (React / Vite)
The frontend provides a dark-themed UI to score titles.

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```
The web app will be available at `http://localhost:5173`.
