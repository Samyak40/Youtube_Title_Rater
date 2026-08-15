import pandas as pd
import numpy as np
import glob
import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Constants
MIN_VIDEOS_FOR_BASELINE = 5

def main():
    base_dir = Path(__file__).resolve().parent.parent
    raw_dir = base_dir / "data" / "raw"
    processed_dir = base_dir / "data" / "processed"
    
    # Ensure processed directory exists
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    csv_files = glob.glob(str(raw_dir / "*.csv"))
    if not csv_files:
        logging.error(f"No CSV files found in {raw_dir}")
        return
        
    logging.info(f"Found {len(csv_files)} CSV files. Loading data...")
    
    dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            logging.error(f"Failed to read {file}: {e}")
            
    if not dfs:
        logging.error("No valid data loaded.")
        return
        
    df = pd.concat(dfs, ignore_index=True)
    initial_count = len(df)
    
    # Identify and drop malformed rows
    logging.info("Cleaning data (dropping malformed rows)...")
    
    # 1. Missing titles
    missing_titles = df['title'].isna()
    if missing_titles.sum() > 0:
        logging.warning(f"Dropping {missing_titles.sum()} rows with missing titles")
        df = df[~missing_titles]
        
    # 2. 0 views (or missing)
    zero_or_missing_views = df['view_count'].isna() | (df['view_count'] <= 0)
    if zero_or_missing_views.sum() > 0:
        logging.warning(f"Dropping {zero_or_missing_views.sum()} rows with <=0 or missing views")
        df = df[~zero_or_missing_views]
        
    # 3. Missing published_at
    missing_pub = df['published_at'].isna()
    if missing_pub.sum() > 0:
        logging.warning(f"Dropping {missing_pub.sum()} rows with missing published_at")
        df = df[~missing_pub]
        
    # 4. Duplicate video_ids
    duplicates = df.duplicated(subset=['video_id'], keep='first')
    if duplicates.sum() > 0:
        logging.warning(f"Dropping {duplicates.sum()} duplicate video_ids")
        df = df[~duplicates]
        
    cleaned_count = len(df)
    logging.info(f"Retained {cleaned_count}/{initial_count} rows after cleaning.")
    
    # Label Engineering
    logging.info("Computing channel baselines and engagement scores...")
    
    # Group by channel to compute total views and video count per channel
    channel_stats = df.groupby('channel_id').agg(
        channel_total_views=('view_count', 'sum'),
        channel_video_count=('video_id', 'count')
    ).reset_index()
    
    df = df.merge(channel_stats, on='channel_id', how='left')
    
    # Compute leave-one-out average
    # (Total Channel Views - This Video's Views) / (Channel Video Count - 1)
    df['channel_avg_views_leave_one_out'] = np.where(
        df['channel_video_count'] > 1,
        (df['channel_total_views'] - df['view_count']) / (df['channel_video_count'] - 1),
        np.nan # Undefined for channels with only 1 video
    )
    
    # Compute raw engagement ratio
    df['raw_engagement_ratio'] = df['view_count'] / df['channel_avg_views_leave_one_out']
    
    # Apply log1p transform
    # We use log1p because:
    # 1. The raw_engagement_ratio can be heavily right-skewed (viral videos have massive ratios).
    # 2. The ratio is bounded below at 0 but unbounded above.
    # 3. We want a target variable that is closer to normally distributed for regression models in Phase 3.
    df['engagement_score'] = np.log1p(df['raw_engagement_ratio'])
    
    # Flag channels with fewer than MIN_VIDEOS_FOR_BASELINE videos
    df['low_confidence_baseline'] = df['channel_video_count'] < MIN_VIDEOS_FOR_BASELINE
    
    # Select final columns
    output_cols = [
        'video_id', 'title', 'channel_id', 'channel_title', 'subscriber_count', 
        'view_count', 'published_at', 'category_id', 'size_tier', 'niche_tags', 
        'channel_avg_views_leave_one_out', 'raw_engagement_ratio', 'engagement_score', 
        'low_confidence_baseline'
    ]
    
    # Note: category_id might be missing in some datasets, let's make sure it's present or default to NaN
    if 'category_id' not in df.columns:
        df['category_id'] = np.nan
        
    df_out = df[output_cols].copy()
    
    output_csv = processed_dir / "labeled_dataset.csv"
    df_out.to_csv(output_csv, index=False)
    logging.info(f"Saved labeled dataset to {output_csv}")
    
    # Generate summary stats
    # Filter out NaNs for engagement score stats
    valid_scores = df_out['engagement_score'].dropna()
    
    summary = {
        "total_rows": len(df_out),
        "low_confidence_rows": int(df_out['low_confidence_baseline'].sum()),
        "engagement_score_stats": {
            "min": float(valid_scores.min()) if not valid_scores.empty else None,
            "max": float(valid_scores.max()) if not valid_scores.empty else None,
            "mean": float(valid_scores.mean()) if not valid_scores.empty else None,
            "median": float(valid_scores.median()) if not valid_scores.empty else None,
            "std": float(valid_scores.std()) if not valid_scores.empty else None,
        },
        "size_tier_breakdown": df_out['size_tier'].value_counts().to_dict()
    }
    
    output_json = processed_dir / "data_summary.json"
    with open(output_json, "w") as f:
        json.dump(summary, f, indent=4)
        
    logging.info(f"Saved data summary to {output_json}")
    logging.info("Summary Statistics:")
    logging.info(f"  Total rows: {summary['total_rows']}")
    logging.info(f"  Low confidence baseline rows: {summary['low_confidence_rows']}")
    logging.info(f"  Engagement Score (mean): {summary['engagement_score_stats']['mean']:.4f}")

if __name__ == "__main__":
    main()
