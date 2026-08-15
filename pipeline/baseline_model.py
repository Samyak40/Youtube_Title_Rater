import pandas as pd
import numpy as np
import os
import json
import logging
from pathlib import Path
from scipy.stats import spearmanr
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
import lightgbm as lgb
import joblib
import sys

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def extract_numeric_features(df):
    """Extracts handcrafted numeric features from the title column."""
    features = pd.DataFrame(index=df.index)
    titles = df['title'].fillna('')
    
    features['title_length'] = titles.str.len()
    features['word_count'] = titles.str.split().str.len().fillna(0)
    features['has_number'] = titles.str.contains(r'\d', regex=True).astype(int)
    features['has_question_mark'] = titles.str.contains(r'\?', regex=True).astype(int)
    
    def count_all_caps(text):
        return sum(1 for word in str(text).split() if word.isupper() and len(word) > 1)
    
    features['all_caps_word_count'] = titles.apply(count_all_caps)
    features['starts_with_number'] = titles.str.match(r'^\d').astype(int)
    
    return features

def evaluate_model(y_true, y_pred, size_tiers):
    """Computes Spearman correlation and MAE overall and by size tier."""
    results = {}
    
    # Overall
    overall_spearman, _ = spearmanr(y_true, y_pred)
    overall_mae = mean_absolute_error(y_true, y_pred)
    results['overall'] = {
        'spearman': float(overall_spearman) if not np.isnan(overall_spearman) else 0.0,
        'mae': float(overall_mae),
        'n': len(y_true)
    }
    
    # By size tier
    tiers = size_tiers.unique()
    for tier in tiers:
        mask = (size_tiers == tier)
        y_t = y_true[mask]
        y_p = y_pred[mask]
        
        n_samples = len(y_t)
        if n_samples < 2:
            sp = np.nan
        else:
            sp, _ = spearmanr(y_t, y_p)
            
        mae = mean_absolute_error(y_t, y_p) if n_samples > 0 else np.nan
        
        results[str(tier)] = {
            'spearman': float(sp) if not np.isnan(sp) else None,
            'mae': float(mae) if not np.isnan(mae) else None,
            'n': int(n_samples)
        }
        
    return results

def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "processed" / "labeled_dataset.csv"
    models_dir = base_dir / "models" / "baseline"
    
    models_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)
    
    # Drop rows with NaN engagement_score
    df = df.dropna(subset=['engagement_score'])
    
    # 1. Temporal Train/Test Split
    df = df.sort_values(by='published_at').reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    train_start, train_end = train_df['published_at'].min(), train_df['published_at'].max()
    test_start, test_end = test_df['published_at'].min(), test_df['published_at'].max()
    
    logging.info(f"Train set: {len(train_df)} rows ({train_start} to {train_end})")
    logging.info(f"Test set: {len(test_df)} rows ({test_start} to {test_end})")
    
    # Exclude low confidence baselines from training
    low_conf_mask = train_df['low_confidence_baseline'] == True
    num_low_conf = low_conf_mask.sum()
    if num_low_conf > 0:
        logging.info(f"Excluding {num_low_conf} low confidence baseline rows from training.")
        train_df = train_df[~low_conf_mask]
        
    # 2. Feature Engineering
    logging.info("Engineering features...")
    
    # TF-IDF
    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_tfidf = tfidf.fit_transform(train_df['title'].fillna(''))
    X_test_tfidf = tfidf.transform(test_df['title'].fillna(''))
    
    # Numeric features
    train_num_feats = extract_numeric_features(train_df)
    test_num_feats = extract_numeric_features(test_df)
    
    # Combine
    X_train = hstack([X_train_tfidf, train_num_feats.values])
    X_test = hstack([X_test_tfidf, test_num_feats.values])
    
    y_train = train_df['engagement_score'].values
    y_test = test_df['engagement_score'].values
    
    # 3. Train Models
    logging.info("Training Ridge Regression...")
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    
    logging.info("Training LightGBM Regressor...")
    lgbm = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=42)
    lgbm.fit(X_train, y_train)
    
    # 4. Evaluation
    logging.info("Evaluating models...")
    ridge_preds = ridge.predict(X_test)
    lgbm_preds = lgbm.predict(X_test)
    
    ridge_eval = evaluate_model(y_test, ridge_preds, test_df['size_tier'])
    lgbm_eval = evaluate_model(y_test, lgbm_preds, test_df['size_tier'])
    
    # Print Comparison Table
    print("\n--- Evaluation Results ---")
    print(f"{'Metric / Tier':<20} | {'Ridge (n)':<25} | {'LightGBM (n)':<25}")
    print("-" * 75)
    
    for tier in ['overall'] + sorted([k for k in ridge_eval.keys() if k != 'overall']):
        r_sp = ridge_eval[tier]['spearman']
        r_sp_str = f"{r_sp:.4f}" if r_sp is not None else "N/A"
        l_sp = lgbm_eval[tier]['spearman']
        l_sp_str = f"{l_sp:.4f}" if l_sp is not None else "N/A"
        n = ridge_eval[tier]['n']
        
        print(f"Spearman: {tier:<10} | {r_sp_str:<12} (n={n:<5}) | {l_sp_str:<12} (n={n:<5})")
        
    print("-" * 75)
    for tier in ['overall'] + sorted([k for k in ridge_eval.keys() if k != 'overall']):
        r_mae = ridge_eval[tier]['mae']
        r_mae_str = f"{r_mae:.4f}" if r_mae is not None else "N/A"
        l_mae = lgbm_eval[tier]['mae']
        l_mae_str = f"{l_mae:.4f}" if l_mae is not None else "N/A"
        n = ridge_eval[tier]['n']
        print(f"MAE: {tier:<15} | {r_mae_str:<12} (n={n:<5}) | {l_mae_str:<12} (n={n:<5})")
        
    # Determine better model
    best_model_name = "LightGBM" if lgbm_eval['overall']['spearman'] > ridge_eval['overall']['spearman'] else "Ridge"
    logging.info(f"Best model based on overall Spearman: {best_model_name}")
    
    best_preds = lgbm_preds if best_model_name == "LightGBM" else ridge_preds
    test_df['predicted_engagement'] = best_preds
    
    # 5. Sanity Check
    print("\n--- Sanity Check: Predictions ---")
    sorted_test = test_df.sort_values(by='predicted_engagement', ascending=False)
    
    print("\nTop 10 Predicted Titles:")
    for _, row in sorted_test.head(10).iterrows():
        print(f"Pred: {row['predicted_engagement']:.3f} | Actual: {row['engagement_score']:.3f} | {row['title']}")
        
    print("\nBottom 10 Predicted Titles:")
    for _, row in sorted_test.tail(10).iterrows():
        print(f"Pred: {row['predicted_engagement']:.3f} | Actual: {row['engagement_score']:.3f} | {row['title']}")
        
    print("\n--- Sanity Check: Ridge TF-IDF Features ---")
    # tfidf weights are the first 5000 coefs
    vocab = {v: k for k, v in tfidf.vocabulary_.items()}
    num_tfidf_features = len(vocab)
    ridge_tfidf_coefs = ridge.coef_[:num_tfidf_features]
    
    sorted_indices = np.argsort(ridge_tfidf_coefs)
    top_indices = sorted_indices[-20:][::-1]
    bottom_indices = sorted_indices[:20]
    
    print("\nTop 20 highest-weighted TF-IDF features:")
    for idx in top_indices:
        print(f"  {vocab[idx]}: {ridge_tfidf_coefs[idx]:.4f}")
        
    print("\nBottom 20 lowest-weighted TF-IDF features:")
    for idx in bottom_indices:
        print(f"  {vocab[idx]}: {ridge_tfidf_coefs[idx]:.4f}")
        
    # 6. Save Artifacts
    logging.info("Saving models and artifacts...")
    
    joblib.dump(ridge, models_dir / 'ridge_model.pkl')
    joblib.dump(lgbm, models_dir / 'lgbm_model.pkl')
    joblib.dump(tfidf, models_dir / 'tfidf_vectorizer.pkl')
    
    eval_results = {
        'ridge': ridge_eval,
        'lgbm': lgbm_eval,
        'best_model': best_model_name
    }
    with open(models_dir / 'evaluation_results.json', 'w') as f:
        json.dump(eval_results, f, indent=4)
        
    sanity_check_df = pd.concat([sorted_test.head(10), sorted_test.tail(10)])
    sanity_check_df.to_csv(models_dir / 'sanity_check_titles.csv', index=False)
    
    logging.info(f"All artifacts saved to {models_dir}")

if __name__ == "__main__":
    main()
