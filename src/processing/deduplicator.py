import json
import os
from datetime import datetime
from sentence_transformers import SentenceTransformer, util

RAW_DATA_DIR = 'data/raw' # This might not be needed if data is passed in
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_articles_for_deduplication(date_str, filename_pattern="{}_combined_sources_fulltext_articles.json"): # Keep for standalone testing
    """Loads articles from a JSON file for a specific date for deduplication testing."""
    file_path = os.path.join(RAW_DATA_DIR, filename_pattern.format(date_str))
    if not os.path.exists(file_path):
        print(f"ERROR: Deduplicator - File not found at {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Deduplicator: Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Deduplicator - Could not load or parse file {file_path}. Error: {e}")
        return []

def run_deduplication(articles_list, threshold=0.85): # Renamed function, takes list as input
    """
    Identifies and marks or filters duplicate articles from a given list.
    For now, it prints duplicates. In a real pipeline, it would return a filtered list
    or articles marked with duplication info.
    """
    if not articles_list:
        print("Deduplicator: No articles provided to deduplicate.")
        return articles_list # Return original list if empty

    print(f"Deduplicator: Initializing SentenceTransformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    sentences = []
    valid_articles_for_dedup = [] # Store articles that have enough content for embedding
    original_indices = [] # Keep track of original indices for mapping back

    for idx, article in enumerate(articles_list):
        title = article.get('title', '')
        # Use full_text if available and substantial, otherwise fallback
        content_for_embedding = article.get('full_text', article.get('summary_from_feed', article.get('summary_from_list', '')))
        content_for_embedding = content_for_embedding if isinstance(content_for_embedding, str) else ''
        
        text_to_embed = title + ". " + content_for_embedding[:1024] # Limit context for embedding
        if len(text_to_embed.strip()) > 10: # Ensure some content
            sentences.append(text_to_embed)
            valid_articles_for_dedup.append(article)
            original_indices.append(idx)
        else:
            print(f"Deduplicator: Skipping article with title '{title[:50]}...' due to insufficient content for embedding.")

    if not sentences:
        print("Deduplicator: No articles with sufficient content to generate embeddings.")
        return articles_list # Return original if no valid articles for deduplication

    print(f"Deduplicator: Generating embeddings for {len(sentences)} articles...")
    embeddings = model.encode(sentences, convert_to_tensor=True, show_progress_bar=True)
    
    print("Deduplicator: Calculating similarity scores...")
    cosine_scores = util.cos_sim(embeddings, embeddings)
    
    duplicates_to_remove_indices = set() # Store original indices of articles to be considered duplicates

    for i in range(len(cosine_scores) - 1):
        if original_indices[i] in duplicates_to_remove_indices:
            continue # This article is already marked as a duplicate of an earlier one
        for j in range(i + 1, len(cosine_scores)):
            if original_indices[j] in duplicates_to_remove_indices:
                continue # This one is already marked

            if cosine_scores[i][j] >= threshold:
                if valid_articles_for_dedup[i].get('link') != valid_articles_for_dedup[j].get('link'):
                    print(f"Deduplicator: Potential duplicate pair with score {cosine_scores[i][j]:.4f}:")
                    print(f"  - Article ({valid_articles_for_dedup[i]['source']}): '{valid_articles_for_dedup[i]['title']}'")
                    print(f"  - Article ({valid_articles_for_dedup[j]['source']}): '{valid_articles_for_dedup[j]['title']}'")
                    # Mark the one with less content (or by other criteria, e.g. source priority) as duplicate
                    # For now, let's mark the second one (j) as duplicate
                    duplicates_to_remove_indices.add(original_indices[j]) 
    
    if duplicates_to_remove_indices:
        print(f"Deduplicator: Identified {len(duplicates_to_remove_indices)} articles as duplicates to be filtered.")
        # Filter out duplicates
        unique_articles = [
            article for idx, article in enumerate(articles_list) 
            if idx not in duplicates_to_remove_indices
        ]
        print(f"Deduplicator: Returning {len(unique_articles)} unique articles.")
        return unique_articles
    else:
        print(f"Deduplicator: No duplicates found above the threshold of {threshold}.")
        return articles_list # Return original list if no duplicates

if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # e.g., today_string = '2025-05-31'
    
    articles_from_file = load_articles_for_deduplication(today_string)
    if articles_from_file:
        unique_articles_result = run_deduplication(articles_from_file, threshold=0.80)
        print(f"\nStandalone Deduplicator Test: Ended up with {len(unique_articles_result)} unique articles.")