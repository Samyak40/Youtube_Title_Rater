import pandas as pd
import numpy as np
import os
import json
import logging
from pathlib import Path
from scipy.stats import spearmanr
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
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
    
    overall_spearman, _ = spearmanr(y_true, y_pred)
    overall_mae = mean_absolute_error(y_true, y_pred)
    results['overall'] = {
        'spearman': float(overall_spearman) if not np.isnan(overall_spearman) else 0.0,
        'mae': float(overall_mae),
        'n': len(y_true)
    }
    
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

def get_embeddings(df, cache_dir):
    """Generates or loads cached sentence embeddings for the dataframe."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    embed_file = cache_dir / "title_embeddings.npy"
    index_file = cache_dir / "title_embeddings_index.csv"
    
    current_ids = df['video_id'].values
    
    if embed_file.exists() and index_file.exists():
        cached_index = pd.read_csv(index_file)['video_id'].values
        if len(cached_index) == len(current_ids) and np.array_equal(cached_index, current_ids):
            logging.info("Loading cached embeddings...")
            return np.load(embed_file)
            
    logging.info("Generating new embeddings with 'all-MiniLM-L6-v2' (this may take a few minutes)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    titles = df['title'].fillna('').tolist()
    embeddings = model.encode(titles, show_progress_bar=True)
    
    np.save(embed_file, embeddings)
    pd.DataFrame({'video_id': current_ids}).to_csv(index_file, index=False)
    logging.info("Embeddings cached.")
    
    return embeddings

def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "processed" / "labeled_dataset.csv"
    baseline_eval_path = base_dir / "models" / "baseline" / "evaluation_results.json"
    models_dir = base_dir / "models" / "embeddings"
    
    models_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)
    df = df.dropna(subset=['engagement_score'])
    
    # 1. Temporal Train/Test Split
    df = df.sort_values(by='published_at').reset_index(drop=True)
    
    # 2. Embeddings Generation / Loading (Do it on full df before split for easier caching)
    full_embeddings = get_embeddings(df, models_dir)
    
    split_idx = int(len(df) * 0.8)
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    X_train_emb_full = full_embeddings[:split_idx]
    X_test_emb = full_embeddings[split_idx:]
    
    # Exclude low confidence baselines from training
    low_conf_mask = train_df['low_confidence_baseline'] == True
    num_low_conf = low_conf_mask.sum()
    if num_low_conf > 0:
        logging.info(f"Excluding {num_low_conf} low confidence baseline rows from training.")
        train_df = train_df[~low_conf_mask]
        X_train_emb = X_train_emb_full[~low_conf_mask]
    else:
        X_train_emb = X_train_emb_full
        
    logging.info(f"Train set: {len(train_df)} rows")
    logging.info(f"Test set: {len(test_df)} rows")
    
    # 3. Feature Engineering
    logging.info("Engineering features...")
    
    # TF-IDF
    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_tfidf = tfidf.fit_transform(train_df['title'].fillna(''))
    X_test_tfidf = tfidf.transform(test_df['title'].fillna(''))
    
    # Numeric features
    train_num_feats = extract_numeric_features(train_df)
    test_num_feats = extract_numeric_features(test_df)
    
    # Feature Matrices
    # Variant 1: Embeddings + Numeric
    X_train_v1 = np.hstack([X_train_emb, train_num_feats.values])
    X_test_v1 = np.hstack([X_test_emb, test_num_feats.values])
    
    # Variant 2: Embeddings + TF-IDF + Numeric (sparse combined with dense)
    X_train_v2 = hstack([csr_matrix(X_train_emb), X_train_tfidf, csr_matrix(train_num_feats.values)])
    X_test_v2 = hstack([csr_matrix(X_test_emb), X_test_tfidf, csr_matrix(test_num_feats.values)])
    
    y_train = train_df['engagement_score'].values
    y_test = test_df['engagement_score'].values
    
    # Train Models
    logging.info("Training Ridge Regression (Embeddings + Numeric)...")
    ridge_v1 = Ridge(alpha=1.0)
    ridge_v1.fit(X_train_v1, y_train)
    preds_v1 = ridge_v1.predict(X_test_v1)
    
    logging.info("Training Ridge Regression (Embeddings + TF-IDF + Numeric)...")
    ridge_v2 = Ridge(alpha=1.0)
    ridge_v2.fit(X_train_v2, y_train)
    preds_v2 = ridge_v2.predict(X_test_v2)
    
    # 4. Evaluation
    logging.info("Evaluating models...")
    eval_v1 = evaluate_model(y_test, preds_v1, test_df['size_tier'])
    eval_v2 = evaluate_model(y_test, preds_v2, test_df['size_tier'])
    
    # Load Phase 3 Baseline results
    if baseline_eval_path.exists():
        with open(baseline_eval_path, 'r') as f:
            baseline_results = json.load(f)
    else:
        baseline_results = {'ridge': {}, 'lgbm': {}}
        
    ridge_b3 = baseline_results.get('ridge', {})
    lgbm_b3 = baseline_results.get('lgbm', {})
    
    print("\n--- Evaluation Results (Spearman Correlation) ---")
    print(f"{'Metric / Tier':<15} | {'Phase 3 Ridge':<15} | {'Phase 3 LGBM':<15} | {'P4 Emb+Num':<15} | {'P4 Emb+TFIDF+Num':<16}")
    print("-" * 85)
    
    tiers = ['overall'] + sorted([k for k in eval_v1.keys() if k != 'overall'])
    for tier in tiers:
        r_b3 = ridge_b3.get(tier, {}).get('spearman')
        l_b3 = lgbm_b3.get(tier, {}).get('spearman')
        v1 = eval_v1.get(tier, {}).get('spearman')
        v2 = eval_v2.get(tier, {}).get('spearman')
        
        r_b3_str = f"{r_b3:.4f}" if r_b3 is not None else "N/A"
        l_b3_str = f"{l_b3:.4f}" if l_b3 is not None else "N/A"
        v1_str = f"{v1:.4f}" if v1 is not None else "N/A"
        v2_str = f"{v2:.4f}" if v2 is not None else "N/A"
        
        n = eval_v1.get(tier, {}).get('n', 'N/A')
        print(f"{tier:<15} | {r_b3_str:<15} | {l_b3_str:<15} | {v1_str:<15} | {v2_str:<16} (n={n})")
        
    # Determine best model from Phase 4
    if eval_v1['overall']['spearman'] > eval_v2['overall']['spearman']:
        best_p4_name = "Phase 4 Ridge (Embeddings + Numeric)"
        best_model = ridge_v1
        best_preds = preds_v1
        best_eval = eval_v1
    else:
        best_p4_name = "Phase 4 Ridge (Embeddings + TF-IDF + Numeric)"
        best_model = ridge_v2
        best_preds = preds_v2
        best_eval = eval_v2
        
    test_df['predicted_engagement'] = best_preds
    
    # 5. Sanity Check
    print(f"\n--- Sanity Check: Predictions (Best Model: {best_p4_name}) ---")
    sorted_test = test_df.sort_values(by='predicted_engagement', ascending=False)
    
    print("\nTop 10 Predicted Titles:")
    for _, row in sorted_test.head(10).iterrows():
        safe_title = str(row['title']).encode('ascii', 'ignore').decode('ascii')
        print(f"Pred: {row['predicted_engagement']:.3f} | Actual: {row['engagement_score']:.3f} | {safe_title}")
        
    print("\nBottom 10 Predicted Titles:")
    for _, row in sorted_test.tail(10).iterrows():
        safe_title = str(row['title']).encode('ascii', 'ignore').decode('ascii')
        print(f"Pred: {row['predicted_engagement']:.3f} | Actual: {row['engagement_score']:.3f} | {safe_title}")
        
    print("\n--- Sanity Check: Nearest Neighbors (Cosine Similarity) ---")
    # Pick 5 random examples from test set
    np.random.seed(42)
    sample_indices = np.random.choice(len(test_df), size=5, replace=False)
    sample_test_df = test_df.iloc[sample_indices]
    sample_test_emb = X_test_emb[sample_indices]
    
    # Compute cosine similarity between 5 test samples and all train samples
    similarities = cosine_similarity(sample_test_emb, X_train_emb)
    
    neighbor_results = []
    
    for i, (_, row) in enumerate(sample_test_df.iterrows()):
        safe_title = str(row['title']).encode('ascii', 'ignore').decode('ascii')
        print(f"\nTarget Title: {safe_title} (Actual Eng: {row['engagement_score']:.3f})")
        
        # Get top 5 indices in training set
        top5_idx = np.argsort(similarities[i])[-5:][::-1]
        
        neighbors = []
        for idx in top5_idx:
            n_row = train_df.iloc[idx]
            n_safe_title = str(n_row['title']).encode('ascii', 'ignore').decode('ascii')
            n_sim = similarities[i][idx]
            n_eng = n_row['engagement_score']
            print(f"  -> [Sim: {n_sim:.3f}] {n_safe_title} (Eng: {n_eng:.3f})")
            
            neighbors.append({
                "title": n_safe_title,
                "similarity": float(n_sim),
                "engagement_score": float(n_eng)
            })
            
        neighbor_results.append({
            "target_title": safe_title,
            "target_engagement": float(row['engagement_score']),
            "neighbors": neighbors
        })
        
    # 6. Save Artifacts
    logging.info("Saving models and artifacts...")
    
    joblib.dump(best_model, models_dir / 'best_model.pkl')
    
    comparison_results = {
        'phase3_ridge': ridge_b3,
        'phase3_lgbm': lgbm_b3,
        'phase4_emb_num': eval_v1,
        'phase4_emb_tfidf_num': eval_v2,
        'best_p4_model': best_p4_name
    }
    
    with open(models_dir / 'comparison_results.json', 'w') as f:
        json.dump(comparison_results, f, indent=4)
        
    with open(models_dir / 'nearest_neighbor_examples.json', 'w') as f:
        json.dump(neighbor_results, f, indent=4)
        
    logging.info(f"All artifacts saved to {models_dir}")
    
    # Final Summary
    best_overall_sp = -1.0
    best_overall_name = ""
    for name, eval_dict in [("Phase 3 Ridge", ridge_b3), ("Phase 3 LightGBM", lgbm_b3), 
                            ("Phase 4 Embeddings+Num", eval_v1), ("Phase 4 Embeddings+TFIDF+Num", eval_v2)]:
        if eval_dict and 'overall' in eval_dict:
            sp = eval_dict['overall'].get('spearman', -1.0)
            if sp > best_overall_sp:
                best_overall_sp = sp
                best_overall_name = name
                
    p3_best = max(ridge_b3.get('overall', {}).get('spearman', 0), lgbm_b3.get('overall', {}).get('spearman', 0))
    p4_best = max(eval_v1['overall']['spearman'], eval_v2['overall']['spearman'])
    
    print("\n================ FINAL SUMMARY ================")
    print(f"The best overall model was: {best_overall_name} with Spearman = {best_overall_sp:.4f}")
    if p4_best > p3_best:
        print(f"Phase 4 beat the Phase 3 baseline by {(p4_best - p3_best):.4f}!")
    elif p3_best > p4_best:
        print(f"Phase 4 did NOT beat the Phase 3 baseline. Phase 3 was better by {(p3_best - p4_best):.4f}.")
    else:
        print("Phase 3 and Phase 4 performed identically.")
    print("===============================================")


if __name__ == "__main__":
    main()
