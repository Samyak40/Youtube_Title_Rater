import pandas as pd
import numpy as np
import json
import logging
import joblib
import re
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error
from scipy.sparse import hstack

from langdetect import detect, DetectorFactory
# Seed for deterministic results
DetectorFactory.seed = 0

from pipeline.baseline_model import extract_numeric_features
from pipeline.hinglish_keywords import HINGLISH_KEYWORDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def detect_language_safe(text):
    """
    Attempts to detect language using langdetect.
    Note: langdetect is heuristic and often mislabels short or code-mixed text like Hinglish.
    """
    try:
        if not text or str(text).strip() == "":
            return "unknown"
        return detect(str(text))
    except Exception:
        return "unknown"

def check_likely_hinglish(text, keywords):
    """
    Flags titles as likely Hinglish if they contain specific heuristic keywords.
    """
    if not isinstance(text, str):
        return False
    
    text_lower = text.lower()
    # Simple word boundary check
    words = re.findall(r'\b\w+\b', text_lower)
    
    for kw in keywords:
        if kw in words:
            return True
            
    return False

def evaluate_subset(y_true, y_pred, subset_name):
    """Computes Spearman correlation and MAE for a subset."""
    n_samples = len(y_true)
    if n_samples < 2:
        return {'spearman': None, 'mae': None, 'n': n_samples}
    
    sp, _ = spearmanr(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    
    return {
        'spearman': float(sp) if not np.isnan(sp) else None,
        'mae': float(mae),
        'n': n_samples
    }

def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data" / "processed"
    models_dir = base_dir / "models" / "baseline"
    
    data_path = data_dir / "labeled_dataset.csv"
    output_csv = data_dir / "labeled_dataset_with_language.csv"
    output_json = data_dir / "language_diagnostic.json"
    
    logging.info(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)
    
    # Step 1: Language Classification
    logging.info("Applying language detection...")
    df['detected_language'] = df['title'].apply(detect_language_safe)
    
    logging.info("Flagging likely Hinglish...")
    df['likely_hinglish'] = df['title'].apply(lambda x: check_likely_hinglish(x, HINGLISH_KEYWORDS))
    
    # Step 2: Quantify Composition
    lang_counts = df['detected_language'].value_counts()
    lang_pcts = df['detected_language'].value_counts(normalize=True) * 100
    
    hinglish_count = df['likely_hinglish'].sum()
    hinglish_pct = (hinglish_count / len(df)) * 100
    
    # Overlap cross-tab
    non_en_hinglish_overlap = df[(df['detected_language'] != 'en') & (df['likely_hinglish'] == True)].shape[0]
    
    # By size tier
    size_tier_breakdown = {}
    if 'size_tier' in df.columns:
        for tier in df['size_tier'].unique():
            tier_df = df[df['size_tier'] == tier]
            tier_hinglish = tier_df['likely_hinglish'].sum()
            size_tier_breakdown[tier] = {
                'count': int(tier_hinglish),
                'percent': float((tier_hinglish / len(tier_df)) * 100) if len(tier_df) > 0 else 0
            }
    
    # Step 3: Evaluate Model Performance Split by Language
    logging.info("Evaluating model performance on test set...")
    
    # Drop NaNs
    df_eval = df.dropna(subset=['engagement_score']).copy()
    
    # Temporal Split (using existing logic)
    df_eval = df_eval.sort_values(by='published_at').reset_index(drop=True)
    split_idx = int(len(df_eval) * 0.8)
    
    test_df = df_eval.iloc[split_idx:].copy()
    
    # Load Models
    ridge = joblib.load(models_dir / 'ridge_model.pkl')
    tfidf = joblib.load(models_dir / 'tfidf_vectorizer.pkl')
    
    # Transform test set
    X_test_tfidf = tfidf.transform(test_df['title'].fillna(''))
    test_num_feats = extract_numeric_features(test_df)
    X_test = hstack([X_test_tfidf, test_num_feats.values])
    y_test = test_df['engagement_score'].values
    
    y_pred = ridge.predict(X_test)
    
    # Split metrics
    hinglish_mask = test_df['likely_hinglish'] == True
    
    results_hinglish = evaluate_subset(y_test[hinglish_mask], y_pred[hinglish_mask], "Hinglish")
    results_english = evaluate_subset(y_test[~hinglish_mask], y_pred[~hinglish_mask], "Non-Hinglish")
    
    # Package Output
    diagnostic_results = {
        'composition': {
            'total_rows': len(df),
            'detected_language_counts': lang_counts.to_dict(),
            'detected_language_percents': lang_pcts.to_dict(),
            'likely_hinglish': {
                'count': int(hinglish_count),
                'percent': float(hinglish_pct)
            },
            'overlap_non_en_and_hinglish': int(non_en_hinglish_overlap),
            'hinglish_by_size_tier': size_tier_breakdown
        },
        'test_set_performance': {
            'hinglish_titles': results_hinglish,
            'non_hinglish_titles': results_english
        }
    }
    
    # Save outputs
    with open(output_json, 'w') as f:
        json.dump(diagnostic_results, f, indent=4)
        
    df.to_csv(output_csv, index=False)
    
    logging.info(f"Results saved to {output_json} and {output_csv}")
    
    # Print Summary
    print("\n" + "="*50)
    print("LANGUAGE DIAGNOSTIC SUMMARY")
    print("="*50)
    print(f"Total Videos: {len(df)}")
    print(f"Likely Hinglish: {hinglish_count} ({hinglish_pct:.2f}%)")
    print(f"Overlap (Non-EN & Hinglish): {non_en_hinglish_overlap}")
    print("\n--- Test Set Performance Split (Ridge Baseline) ---")
    
    h_sp = results_hinglish['spearman']
    h_n = results_hinglish['n']
    e_sp = results_english['spearman']
    e_n = results_english['n']
    
    h_sp_str = f"{h_sp:.4f}" if h_sp is not None else "N/A"
    e_sp_str = f"{e_sp:.4f}" if e_sp is not None else "N/A"
    
    diff = "N/A"
    if h_sp is not None and e_sp is not None:
        diff = f"{(e_sp - h_sp):.4f}"
    
    print(f"Hinglish titles:     n={h_n:<5}, Spearman={h_sp_str}")
    print(f"Non-Hinglish titles: n={e_n:<5}, Spearman={e_sp_str}")
    print(f"Difference: {diff}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
