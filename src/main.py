import os
from datetime import datetime
import json # For saving final processed data

# Import functions from our modules
from ingestion.scraper import fetch_rss_feeds, fetch_stanford_hai_news_requests, save_articles_to_json as save_raw_articles
from processing.deduplicator import run_deduplication
from processing.classifier import run_classification, CANDIDATE_LABELS_EN
from processing.summarizer import run_summarization
from output.markdown_generator import generate_newsletter_markdown, save_markdown_newsletter
# Define output directory for final processed data
PROCESSED_DATA_DIR = 'data/processed'

def save_final_processed_data(articles, date_str):
    """Saves the final list of fully processed articles."""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    file_path = os.path.join(PROCESSED_DATA_DIR, f'{date_str}_final_ai_news.json')
    
    print(f"\nPipeline: Saving final processed articles to {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Pipeline: Successfully saved {len(articles)} final articles to {file_path}.")
    except Exception as e:
        print(f"Pipeline ERROR: Could not save final processed articles. Error: {e}")

def run_daily_pipeline():
    """
    Runs the full daily pipeline:
    1. Ingest articles (RSS and Scrapers)
    2. Deduplicate articles
    3. Classify articles
    4. Summarize articles
    5. Save final processed data
    """
    print("--- Starting Daily AI News Pipeline ---")
    today_date_obj = datetime.now()
    today_string = datetime.now().strftime('%Y-%m-%d')

    # --- 1. Ingestion ---
    print("\n--- Step 1: Ingesting Articles ---")
    rss_articles = fetch_rss_feeds()
    # For Stanford, let's fetch only 1 page in the main pipeline for now to be quicker
    stanford_articles = fetch_stanford_hai_news_requests(max_pages=1) 
    
    all_ingested_articles = rss_articles + stanford_articles
    if not all_ingested_articles:
        print("Pipeline: No articles ingested. Exiting.")
        return

    # Save raw ingested data (optional, scraper.py already does this if run standalone)
    # We might want a dedicated save function in scraper.py that main.py calls.
    # For now, scraper.py's if __name__ == '__main__' saves it.
    # Let's assume scraper.py was run and 'YYYY-MM-DD_combined_sources_fulltext_articles.json' exists
    # OR, we make scraper functions return data and main.py saves the raw data.
    # For simplicity, let's have main.py also save the "raw" combined list before processing.
    save_raw_articles(all_ingested_articles, filename_prefix=f"{today_string}_main_pipeline_raw_ingested")
    print(f"Pipeline: Ingested a total of {len(all_ingested_articles)} articles.")

    # --- 2. Deduplication ---
    # Input: all_ingested_articles
    # Output: unique_articles
    print("\n--- Step 2: Deduplicating Articles ---")
    # Using a moderate threshold for the pipeline
    unique_articles = run_deduplication(all_ingested_articles, threshold=0.85) 
    if not unique_articles:
        print("Pipeline: No unique articles after deduplication. Exiting.")
        return
    print(f"Pipeline: {len(unique_articles)} articles remaining after deduplication.")

    # --- 3. Classification ---
    # Input: unique_articles
    # Output: classified_articles (articles with 'classification' field)
    print("\n--- Step 3: Classifying Articles ---")
    classified_articles = run_classification(unique_articles, candidate_labels=CANDIDATE_LABELS_EN)
    if not classified_articles: # Should not happen if unique_articles was not empty
        print("Pipeline: No articles after classification. Exiting.")
        return
    print(f"Pipeline: Classification complete for {len(classified_articles)} articles.")

    # --- 4. Summarization ---
    # Input: classified_articles
    # Output: summarized_articles (articles with 'popular_summary' field)
    print("\n--- Step 4: Generating Summaries ---")
    # In pipeline, summarize all articles that passed previous steps.
    # Limit for pipeline run, e.g. 5, to manage API costs during development.
    # Set to None to process all.
    summarized_articles = run_summarization(classified_articles, articles_to_summarize_limit=5) 
    if not summarized_articles: # Should not happen
        print("Pipeline: No articles after summarization. Exiting.")
        return
    print(f"Pipeline: Summarization complete for {len(summarized_articles)} articles (or up to limit).")

    # --- 5. Save Final Processed Data (JSON) ---
    save_final_processed_data(summarized_articles, today_string) # summarized_articles is the fully processed list

    # *** 新增步驟：6. Generate and Save Markdown Newsletter ***
    print("\n--- Step 6: Generating Markdown Newsletter ---")
    if summarized_articles: # Use the fully processed list
        markdown_content = generate_newsletter_markdown(summarized_articles, today_date_obj)
        if markdown_content:
            save_markdown_newsletter(markdown_content, today_date_obj)
            print("Pipeline: Markdown newsletter generated successfully.")
        else:
            print("Pipeline ERROR: Failed to generate Markdown content.")
    else:
        print("Pipeline: No summarized articles to generate newsletter from.")


    print("\n--- Daily AI News Pipeline Finished ---")


if __name__ == '__main__':
    run_daily_pipeline()