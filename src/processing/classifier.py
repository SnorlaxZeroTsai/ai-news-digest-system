import json
import os
from datetime import datetime
from transformers import pipeline # For zero-shot classification

# Define the path to the processed data (output from ingestion/deduplication)
# For now, we'll read from the raw data directory
RAW_DATA_DIR = 'data/raw' 
# Later, this might be 'data/processed' after deduplication

# Define our classification schema (candidate labels)
# These should be in English for better model compatibility with common pre-trained models
CANDIDATE_LABELS_EN = [
    "Research & Breakthroughs",
    "Industry Applications & Case Studies",
    "Ethics, Governance & Policy",
    "AI Tools, Platforms & Resources",
    "Market Trends & Investments",
    "Academic Conferences & Community Events"
]

# You can also provide Chinese labels if your model supports it well,
# or if you plan to translate. For now, English is safer with most general models.
CANDIDATE_LABELS_ZH = [
    "研究與突破",
    "產業應用與案例",
    "倫理、治理與政策",
    "AI工具、平台與資源",
    "市場動態與投資",
    "學術會議與社區活動"
]


def load_articles(date_str):
    """
    Loads articles from the combined JSON file for a specific date.
    """
    file_path = os.path.join(RAW_DATA_DIR, f'{date_str}_combined_sources_articles.json')
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        print(f"Please ensure 'src/ingestion/scraper.py' has been run to generate this file.")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Could not load or parse the file {file_path}. Error: {e}")
        return []

def classify_articles_zero_shot(articles_to_classify, candidate_labels):
    """
    Classifies articles using a zero-shot classification pipeline from Hugging Face.
    
    Args:
        articles_to_classify (list): A list of article dictionaries.
        candidate_labels (list): A list of strings representing the potential categories.

    Returns:
        list: The list of articles, with classification results added to each article dict.
    """
    if not articles_to_classify:
        print("No articles to classify.")
        return []

    print("Initializing zero-shot classification pipeline...")
    # This will download the model on the first run (e.g., facebook/bart-large-mnli)
    # You can specify a different model if needed: model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli" for more languages
    classifier = pipeline("zero-shot-classification", device=-1) # device=-1 for CPU, 0 for GPU 0
    print("Pipeline initialized.")

    classified_articles = []
    for i, article in enumerate(articles_to_classify):
        title = article.get('title', '')
        summary = article.get('summary', '')
        
        # Ensure summary is a string
        summary = summary if isinstance(summary, str) else ''
        
        sequence_to_classify = title + ". " + summary[:1024] # Use a good chunk of summary
        
        if not sequence_to_classify.strip() or sequence_to_classify.strip() == ".":
            print(f"Skipping article {i+1} ('{title[:50]}...') due to empty content for classification.")
            article['classification'] = {'labels': ['Unclassified'], 'scores': [0.0]}
            classified_articles.append(article)
            continue

        print(f"\nClassifying article {i+1}/{len(articles_to_classify)}: '{title[:80]}...'")
        
        try:
            # multi_label=True allows an article to belong to multiple categories
            # You can set it to False if you want only the single best category
            classification_result = classifier(sequence_to_classify, candidate_labels, multi_label=True)
            
            # The result contains 'sequence', 'labels', and 'scores'
            # 'labels' are sorted by 'scores' in descending order
            article['classification'] = {
                'labels': classification_result['labels'],
                'scores': classification_result['scores']
            }
            
            print(f"  Top label: {article['classification']['labels'][0]} (Score: {article['classification']['scores'][0]:.4f})")
            if len(article['classification']['labels']) > 1:
                 print(f"  Second label: {article['classification']['labels'][1]} (Score: {article['classification']['scores'][1]:.4f})")

        except Exception as e:
            print(f"ERROR: Could not classify article '{title[:50]}...'. Error: {e}")
            article['classification'] = {'labels': ['Error'], 'scores': [0.0]}
        
        classified_articles.append(article)

    return classified_articles


if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # For testing, you might want to manually set this to a date for which you know a file exists,
    # e.g., today_string = '2025-05-30' 
    
    articles_data = load_articles(today_string)
    
    if articles_data:
        # We use English labels here as most zero-shot models are trained primarily on English
        # and perform better with English labels.
        classified_results = classify_articles_zero_shot(articles_data, CANDIDATE_LABELS_EN)
        
        print("\n--- Classification Test Output (First 3 Articles) ---")
        for i, article in enumerate(classified_results[:3]):
            print(f"\nArticle Title: {article.get('title', 'N/A')}")
            print(f"  Source: {article.get('source', 'N/A')}")
            if 'classification' in article:
                print(f"  Predicted Labels: {article['classification']['labels']}")
                print(f"  Scores: {[round(s, 4) for s in article['classification']['scores']]}")
            else:
                print("  No classification data.")
        
        # Next step would be to save these classified_results to a new file
        # in 'data/processed/' or update the existing objects.
        # For now, we are just printing.
        print(f"\nProcessed {len(classified_results)} articles.")