import json
import os
from datetime import datetime
from transformers import pipeline

RAW_DATA_DIR = 'data/raw' # For standalone testing
PROCESSED_DATA_DIR = 'data/processed' # For future saving

CANDIDATE_LABELS_EN = [
    "Research & Breakthroughs", "Industry Applications & Case Studies",
    "Ethics, Governance & Policy", "AI Tools, Platforms & Resources",
    "Market Trends & Investments", "Academic Conferences & Community Events"
]

def load_articles_for_classification(date_str, filename_pattern="{}_combined_sources_fulltext_articles.json"): # For standalone testing
    """Loads articles for classification testing."""
    file_path = os.path.join(RAW_DATA_DIR, filename_pattern.format(date_str))
    # ... (load logic remains same) ...
    if not os.path.exists(file_path):
        print(f"ERROR: Classifier - File not found at {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Classifier: Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Classifier - Could not load file {file_path}. Error: {e}")
        return []

def run_classification(articles_list, candidate_labels=CANDIDATE_LABELS_EN): # Renamed function
    """
    Classifies a list of articles using a zero-shot classification pipeline.
    Adds 'classification' key to each article dictionary.
    """
    if not articles_list:
        print("Classifier: No articles provided to classify.")
        return articles_list

    print("Classifier: Initializing zero-shot classification pipeline...")
    classifier_pipeline = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
    print("Classifier: Pipeline initialized.")

    for i, article in enumerate(articles_list):
        title = article.get('title', '')
        # Use full_text if available and substantial, otherwise fallback
        content_for_classification = article.get('full_text', article.get('summary_from_feed', article.get('summary_from_list', '')))
        content_for_classification = content_for_classification if isinstance(content_for_classification, str) else ''
        
        sequence_to_classify = title + ". " + content_for_classification[:1024]
        
        if not sequence_to_classify.strip() or sequence_to_classify.strip() == ".":
            print(f"Classifier: Skipping article {i+1} ('{title[:50]}...') due to empty content.")
            article['classification'] = {'labels': ['Unclassified'], 'scores': [0.0]}
            continue

        print(f"\nClassifier: Classifying article {i+1}/{len(articles_list)}: '{title[:80]}...'")
        try:
            classification_result = classifier_pipeline(sequence_to_classify, candidate_labels, multi_label=True)
            article['classification'] = {
                'labels': classification_result['labels'],
                'scores': classification_result['scores']
            }
            print(f"  Top label: {article['classification']['labels'][0]} (Score: {article['classification']['scores'][0]:.4f})")
        except Exception as e:
            print(f"ERROR: Classifier - Could not classify article '{title[:50]}...'. Error: {e}")
            article['classification'] = {'labels': ['Error'], 'scores': [0.0]}
            
    return articles_list # Return the list with 'classification' added

if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # e.g., today_string = '2025-05-31'
    
    articles_from_file = load_articles_for_classification(today_string)
    if articles_from_file:
        classified_articles_result = run_classification(articles_from_file)
        print("\n--- Standalone Classifier Test Output (First 3 Articles) ---")
        for i, article in enumerate(classified_articles_result[:3]):
            # ... (print logic remains same) ...
            print(f"\nArticle Title: {article.get('title', 'N/A')}")
            print(f"  Source: {article.get('source', 'N/A')}")
            if 'classification' in article:
                print(f"  Predicted Labels: {article['classification']['labels']}")
                print(f"  Scores: {[round(s, 4) for s in article['classification']['scores']]}")
            else:
                print("  No classification data.")