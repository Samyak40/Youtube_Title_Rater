import pandas as pd

def extract_numeric_features(df):
    """Extracts handcrafted numeric features from the title column (matches Phase 3)."""
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
