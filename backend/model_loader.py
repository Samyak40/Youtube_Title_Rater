import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = None
vectorizer = None
train_scores = None

def load_models():
    global model, vectorizer, train_scores
    
    base_dir = Path(__file__).resolve().parent.parent
    models_dir = base_dir / "models" / "baseline"
    data_path = base_dir / "data" / "processed" / "labeled_dataset.csv"
    
    logger.info("Loading Phase 3 Ridge model and TF-IDF vectorizer...")
    try:
        model = joblib.load(models_dir / "ridge_model.pkl")
        vectorizer = joblib.load(models_dir / "tfidf_vectorizer.pkl")
    except Exception as e:
        logger.error(f"Failed to load models. Ensure Phase 3 has been run. Error: {e}")
        raise
    
    logger.info("Computing training dataset score distribution for percentiles...")
    try:
        df = pd.read_csv(data_path)
        df = df.dropna(subset=['engagement_score'])
        df = df.sort_values(by='published_at').reset_index(drop=True)
        
        # 80% train split (exactly as Phase 3)
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        
        # Exclude low confidence
        train_df = train_df[train_df['low_confidence_baseline'] == False]
        
        train_scores = train_df['engagement_score'].values
        train_scores.sort()
        
        logger.info(f"Loaded {len(train_scores)} training scores for percentile calculation.")
    except Exception as e:
        logger.error(f"Failed to load dataset for percentiles. Error: {e}")
        train_scores = np.array([])

def get_percentile(score: float) -> float:
    if train_scores is None or len(train_scores) == 0:
        return 50.0
    return float(stats.percentileofscore(train_scores, score))
