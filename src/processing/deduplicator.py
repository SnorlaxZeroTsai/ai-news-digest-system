import json
import os
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Define the path to the raw data directory
RAW_DATA_DIR = 'data/raw'

# Specify the pre-trained model we'll use for creating embeddings.
# 'all-MiniLM-L6-v2' is a great starting point: fast and performs well.
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_articles(date_str):
    """
    Loads articles from a JSON file for a specific date.
    """
    file_path = os.path.join(RAW_DATA_DIR, f'{date_str}_rss_articles.json')
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Could not load or parse the file {file_path}. Error: {e}")
        return []

def find_semantic_duplicates(articles, threshold=0.85):
    """
    Finds semantically similar articles using sentence embeddings.
    
    Args:
        articles (list): A list of article dictionaries.
        threshold (float): The similarity score threshold to consider articles as duplicates.

    Returns:
        list: A list of tuples, where each tuple contains the indices of duplicate articles.
    """
    if not articles:
        return []

    print(f"Initializing SentenceTransformer model: {MODEL_NAME}...")
    # Initialize the model. This might download the model on the first run.
    model = SentenceTransformer(MODEL_NAME)

    # We'll create embeddings based on the title and a portion of the summary.
    # This provides a good balance of specificity and context.
    sentences = [article['title'] + ". " + article['summary'][:512] for article in articles]

    print("Generating embeddings for all articles. This may take a moment...")
    # Generate embeddings for all sentences.
    embeddings = model.encode(sentences, convert_to_tensor=True, show_progress_bar=True)

    print("Calculating similarity scores...")
    # Calculate the cosine similarity between all pairs of embeddings.
    # The result is a matrix of similarity scores.
    cosine_scores = util.cos_sim(embeddings, embeddings)

    # Find pairs with similarity above the threshold.
    duplicate_pairs = []
    # We iterate through the upper triangle of the similarity matrix to avoid duplicate pairs (i,j) and (j,i)
    # and self-comparisons (i,i).
    for i in range(len(cosine_scores) - 1):
        for j in range(i + 1, len(cosine_scores)):
            if cosine_scores[i][j] >= threshold:
                print(f"Found a potential duplicate pair with score {cosine_scores[i][j]:.4f}:")
                print(f"  - Article {i+1}: '{articles[i]['title']}'")
                print(f"  - Article {j+1}: '{articles[j]['title']}'")
                duplicate_pairs.append((i, j))
    
    if not duplicate_pairs:
        print("No duplicates found above the threshold.")

    return duplicate_pairs


if __name__ == '__main__':
    # Get today's date string to find the correct file.
    today_string = datetime.now().strftime('%Y-%m-%d')
    
    # For testing, you might want to manually set this to a date you know has a file,
    # e.g., today_string = '2025-05-27'
    
    # 1. Load the articles
    articles_to_process = load_articles(today_string)
    
    # 2. Find duplicates within the loaded articles
    if articles_to_process:
        duplicates = find_semantic_duplicates(articles_to_process, threshold=0.85)
        print(f"\nDuplicate finding process complete. Found {len(duplicates)} pairs.")