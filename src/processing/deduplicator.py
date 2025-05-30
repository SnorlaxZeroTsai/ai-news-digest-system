import json
import os
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
# import numpy as np # numpy 目前在 util.cos_sim 中隱式使用，但如果直接操作 tensor 可能需要

RAW_DATA_DIR = 'data/raw'
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_articles(date_str):
    """
    Loads articles from a JSON file for a specific date.
    Now looks for the combined sources file.
    """
    # *** 主要修改處 ***
    file_path = os.path.join(RAW_DATA_DIR, f'{date_str}_combined_sources_articles.json')
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        print(f"Please ensure 'src/ingestion/scraper.py' has been run to generate this file for date {date_str}.")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Could not load or parse the file {file_path}. Error: {e}")
        return []

# ... find_semantic_duplicates() 函數保持不變 ...
def find_semantic_duplicates(articles, threshold=0.85):
    """
    Finds semantically similar articles using sentence embeddings.
    """
    if not articles:
        return []
    print(f"Initializing SentenceTransformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    # Consider using titles + summaries for better semantic capture
    # Ensure all articles have 'title' and 'summary' keys, or handle missing ones
    sentences = []
    for article in articles:
        title = article.get('title', '')
        summary = article.get('summary', '')
        # Ensure summary is a string
        summary = summary if isinstance(summary, str) else ''
        sentences.append(title + ". " + summary[:512])


    print("Generating embeddings for all articles. This may take a moment...")
    embeddings = model.encode(sentences, convert_to_tensor=True, show_progress_bar=True)
    print("Calculating similarity scores...")
    cosine_scores = util.cos_sim(embeddings, embeddings)
    duplicate_pairs = []
    for i in range(len(cosine_scores) - 1):
        for j in range(i + 1, len(cosine_scores)):
            if cosine_scores[i][j] >= threshold:
                # Check if titles are not exactly the same but content might be similar
                # This prevents flagging an article as duplicate of itself if by chance titles are identical for different entries
                # Although our current data structure implies different entries are different articles
                if articles[i].get('link') != articles[j].get('link'): # A simple check
                    print(f"Found a potential duplicate pair with score {cosine_scores[i][j]:.4f}:")
                    print(f"  - Article {i+1} ({articles[i]['source']}): '{articles[i]['title']}' ({articles[i]['link']})")
                    print(f"  - Article {j+1} ({articles[j]['source']}): '{articles[j]['title']}' ({articles[j]['link']})")
                    duplicate_pairs.append((i, j))
    
    if not duplicate_pairs:
        print(f"No duplicates found above the threshold of {threshold}.")
    return duplicate_pairs


if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # For testing, you might want to manually set this to a date you know has a file,
    # e.g., today_string = '2025-05-27' # Make sure this file exists with combined data
    
    articles_to_process = load_articles(today_string)
    
    if articles_to_process:
        # You can experiment with the threshold
        duplicates = find_semantic_duplicates(articles_to_process, threshold=0.80) 
        print(f"\nDuplicate finding process complete. Found {len(duplicates)} pairs with threshold 0.80.")
        # duplicates_strict = find_semantic_duplicates(articles_to_process, threshold=0.90)
        # print(f"Duplicate finding process complete. Found {len(duplicates_strict)} pairs with threshold 0.90.")