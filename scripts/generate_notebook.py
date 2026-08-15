import nbformat as nbf

nb = nbf.v4.new_notebook()

# Markdown and code cells
cells = [
    nbf.v4.new_markdown_cell("# TitlePulse Phase 2: Exploratory Data Analysis\n\nThis notebook loads the raw video data from Phase 1, performs basic cleaning, and explores the distributions of key variables like views, subscribers, and channels."),
    
    nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport glob\nimport os\n\n# Set plot style\nsns.set_theme(style=\"whitegrid\")"),
    
    nbf.v4.new_markdown_cell("## 1. Load Data\n\nLoad all raw CSV files into a single DataFrame."),
    
    nbf.v4.new_code_cell("raw_dir = '../data/raw'\ncsv_files = glob.glob(os.path.join(raw_dir, '*.csv'))\n\ndfs = []\nfor f in csv_files:\n    df = pd.read_csv(f)\n    dfs.append(df)\n    \ndf = pd.concat(dfs, ignore_index=True)\nprint(f\"Loaded {len(df)} total videos from {len(csv_files)} files.\")"),
    
    nbf.v4.new_markdown_cell("## 2. Basic Dataset Summary\n\nLet's look at total videos, total unique channels, and breakdowns by `niche_tags` and `size_tier`."),
    
    nbf.v4.new_code_cell("print(f\"Total Videos: {len(df)}\")\nprint(f\"Total Unique Channels: {df['channel_id'].nunique()}\")\nprint(\"\\n--- Breakdown by Size Tier ---\")\nprint(df['size_tier'].value_counts())\nprint(\"\\n--- Breakdown by Niche Tags ---\")\nprint(df['niche_tags'].value_counts())"),
    
    nbf.v4.new_markdown_cell("## 3. Data Quality & Malformed Rows\n\nIdentify broken rows: missing titles, 0 views, duplicate video_ids, missing published_at."),
    
    nbf.v4.new_code_cell("missing_titles = df['title'].isna().sum()\nzero_views = (df['view_count'] <= 0).sum() | df['view_count'].isna().sum()\nmissing_pub = df['published_at'].isna().sum()\nduplicates = df.duplicated(subset=['video_id']).sum()\n\nprint(f\"Missing Titles: {missing_titles}\")\nprint(f\"Zero or Missing Views: {zero_views}\")\nprint(f\"Missing Published Date: {missing_pub}\")\nprint(f\"Duplicate Video IDs: {duplicates}\")"),
    
    nbf.v4.new_markdown_cell("Let's drop these for the rest of the visual analysis."),
    
    nbf.v4.new_code_cell("df_clean = df.dropna(subset=['title', 'published_at']).copy()\ndf_clean = df_clean[df_clean['view_count'] > 0]\ndf_clean = df_clean.drop_duplicates(subset=['video_id'])\nprint(f\"Videos remaining after cleaning: {len(df_clean)}\")"),
    
    nbf.v4.new_markdown_cell("## 4. Distribution of Raw View Count\n\nThis distribution is expected to be heavily right-skewed, as a few videos get massive amounts of views while most get very few."),
    
    nbf.v4.new_code_cell("plt.figure(figsize=(10, 6))\nsns.histplot(df_clean['view_count'], bins=50, kde=True)\nplt.title('Distribution of Raw View Count')\nplt.xlabel('View Count')\nplt.ylabel('Frequency')\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 5. Distribution of Log1p View Count\n\nApplying a `log1p` transform (log(1 + x)) should make the distribution look much closer to normal, which is better for modeling."),
    
    nbf.v4.new_code_cell("df_clean['log_view_count'] = np.log1p(df_clean['view_count'])\nplt.figure(figsize=(10, 6))\nsns.histplot(df_clean['log_view_count'], bins=50, kde=True)\nplt.title('Distribution of Log1p View Count')\nplt.xlabel('Log1p(View Count)')\nplt.ylabel('Frequency')\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 6. Distribution of Subscriber Count Across Channels\n\nLet's see the distribution of channel sizes."),
    
    nbf.v4.new_code_cell("channel_df = df_clean.drop_duplicates(subset=['channel_id'])\nplt.figure(figsize=(10, 6))\nsns.histplot(channel_df['subscriber_count'], bins=50, kde=True)\nplt.title('Distribution of Subscriber Count (Unique Channels)')\nplt.xlabel('Subscriber Count')\nplt.ylabel('Frequency')\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 7. Subscribers vs. Views (Log-Log Scale)\n\nDo bigger channels get more views? Let's check the correlation. We use a log-log scale due to the wide variance."),
    
    nbf.v4.new_code_cell("plt.figure(figsize=(10, 6))\nsns.scatterplot(data=df_clean, x='subscriber_count', y='view_count', alpha=0.3)\nplt.xscale('log')\nplt.yscale('log')\nplt.title('Subscriber Count vs. View Count (Log-Log Scale)')\nplt.xlabel('Subscriber Count (Log)')\nplt.ylabel('View Count (Log)')\nplt.show()"),
    
    nbf.v4.new_markdown_cell("## 8. Per-Channel Video Count Distribution\n\nWe need to flag channels with too few videos (e.g., < 5), as their \"rolling average\" baseline won't be reliable."),
    
    nbf.v4.new_code_cell("video_counts = df_clean.groupby('channel_id')['video_id'].count()\n\nplt.figure(figsize=(10, 6))\nsns.histplot(video_counts, bins=range(1, video_counts.max() + 2), discrete=True)\nplt.title('Distribution of Videos per Channel')\nplt.xlabel('Number of Videos')\nplt.ylabel('Frequency (Channels)')\nplt.xlim(0, 50)\nplt.show()\n\nlow_video_channels = (video_counts < 5).sum()\nprint(f\"Channels with fewer than 5 videos: {low_video_channels} out of {len(video_counts)} ({(low_video_channels/len(video_counts))*100:.2f}%)\")")
]

nb['cells'] = cells

with open('notebooks/eda.ipynb', 'w') as f:
    nbf.write(nb, f)
