import json
import os
from datetime import datetime
from openai import OpenAI
import time

RAW_DATA_DIR = 'data/raw' # For standalone testing
PROCESSED_DATA_DIR = 'data/processed'

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# ... (LLM Config remains same) ...
DEFAULT_OPENAI_MODEL_NAME = "gpt-3.5-turbo"
MAX_TOKENS_TO_SAMPLE = 1024
TEMPERATURE = 0.2

def load_articles_for_summarization_test(date_str, filename_pattern="{}_combined_sources_fulltext_articles.json"): # For standalone testing
    """Loads articles for summarization testing."""
    file_path = os.path.join(RAW_DATA_DIR, filename_pattern.format(date_str)) # Default to raw for testing input
    # ... (load logic remains same) ...
    if not os.path.exists(file_path):
        print(f"ERROR: Summarizer - File not found at {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Summarizer: Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e:
        print(f"ERROR: Summarizer - Could not load file {file_path}. Error: {e}")
        return []

# construct_popular_science_prompt_for_openai remains the same
# generate_summary_with_openai remains the same

def construct_popular_science_prompt_for_openai(article_title, article_content):
    # ... (same as before) ...
    system_message_content = (
        "You are an expert AI science communicator. Your task is to summarize the provided AI-related news article "
        "for a general audience with no prior technical AI knowledge (e.g., curious high school students, "
        "educated adults from non-technical fields). The summary must be accurate, easy to understand, engaging, "
        "and objective. It is crucial to avoid overgeneralization and hype."
    )
    user_message_content = f"""Please create a popular science summary for the following article:
Article Title: "{article_title}"
Article Content:
---
{article_content}
---
When generating the summary, please adhere STRICTLY to the following guidelines:
1.  Accuracy and Faithfulness: The summary MUST be factually accurate and faithfully represent the core findings, significance, and any explicitly stated limitations or caveats from the original article. Do NOT add external information or your own opinions.
2.  Target Audience & Clarity: Write in clear, simple, and concise language. Avoid jargon. If a technical term is absolutely essential, explain it briefly in a very simple way or use an analogy. The goal is to make complex AI topics accessible.
3.  Content Focus:
    * Identify the main problem or question the article addresses.
    * Briefly explain the core AI technology or method used in simple terms.
    * Highlight the key results or developments.
    * Clearly state the significance or potential impact of these developments for a general reader.
4.  Avoid Overgeneralization and Hype: Do NOT exaggerate claims or make predictions beyond what the article supports. If the research is preliminary or has limitations, this MUST be subtly reflected in the summary (e.g., "researchers suggest this could potentially lead to...", "while promising, more research is needed to confirm...").
5.  Structure & Length:
    * Start with a one-sentence key takeaway or the most interesting finding.
    * Follow with 2-4 short paragraphs (or 3-5 bullet points if more appropriate for the content) explaining the main points.
    * Aim for a total summary length of approximately 150-250 words.
6.  Tone: Objective, neutral, yet engaging and informative.
Output ONLY the popular science summary. Do not include any preambles or conversational text beyond the summary itself.
"""
    return system_message_content, user_message_content

def generate_summary_with_openai(article_title, article_content, 
                                 client, model_name=DEFAULT_OPENAI_MODEL_NAME, 
                                 max_tokens=MAX_TOKENS_TO_SAMPLE, temp=TEMPERATURE):
    # ... (same as before) ...
    if not client: return "Error: API client not initialized."
    system_prompt, user_prompt = construct_popular_science_prompt_for_openai(article_title, article_content)
    try:
        print(f"\nSummarizer: Requesting summary for: '{article_title[:80]}...'")
        response = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}], max_tokens=max_tokens, temperature=temp, n=1, stop=None)
        if response.choices and len(response.choices) > 0: return response.choices[0].message.content.strip()
        else: print(f"ERROR: Summarizer - No choices in OpenAI response. Response: {response}"); return "Error: No summary from API."
    except Exception as e: print(f"ERROR: Summarizer - OpenAI API error: {e}"); import traceback; print(traceback.format_exc()); return "Error: API call failed."


def run_summarization(articles_list, articles_to_summarize_limit=None): # Renamed and added limit
    """
    Generates popular science summaries for a list of articles.
    Adds 'popular_summary' key to each processed article dictionary.
    """
    if not articles_list:
        print("Summarizer: No articles provided to summarize.")
        return articles_list
    
    if not OPENAI_API_KEY:
        print("Summarizer: OPENAI_API_KEY not set. Skipping summarization.")
        # Add a placeholder summary or skip adding the key
        for article in articles_list:
            article['popular_summary'] = "Summarization skipped: API key not configured."
        return articles_list

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("Summarizer: OpenAI client initialized.")

    # Determine how many articles to process
    limit = articles_to_summarize_limit if articles_to_summarize_limit is not None else len(articles_list)
    
    for i, article in enumerate(articles_list):
        if i >= limit:
            print(f"Summarizer: Reached limit of {limit} articles for summarization in this run.")
            article['popular_summary'] = "Summarization skipped: processing limit reached."
            continue # Skip summarization for remaining articles but keep them in the list

        title = article.get('title', 'N/A')
        content_to_summarize = article.get('full_text', '')
        if not content_to_summarize or len(content_to_summarize.strip()) < 50:
            content_to_summarize = article.get('summary_from_feed', article.get('summary_from_list', ''))
            if not content_to_summarize and title != 'N/A': content_to_summarize = title
            elif title != 'N/A' and content_to_summarize: content_to_summarize = title + ". " + content_to_summarize
        
        if not content_to_summarize or not content_to_summarize.strip() or content_to_summarize.strip() == ".":
            print(f"Summarizer: Skipping article '{title}' due to insufficient content.")
            article['popular_summary'] = "Content insufficient for summarization."
            continue
            
        generated_summary = generate_summary_with_openai(title, content_to_summarize, openai_client)
        article['popular_summary'] = generated_summary
        
        if i < limit -1 : # Avoid sleeping after the last item if limit is effective
             time.sleep(1) # Be respectful to API rate limits

    return articles_list


# save_processed_articles remains the same, but it will be called from main.py now
def save_processed_articles_test(articles, date_str): # For standalone testing
    """Saves the list of articles to data/processed/ for testing."""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    file_path = os.path.join(PROCESSED_DATA_DIR, f'{date_str}_summarized_articles_test.json')
    # ... (save logic same as before) ...
    print(f"\nSummarizer Test: Saving processed articles to {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Summarizer Test: Successfully saved {len(articles)} articles.")
    except Exception as e:
        print(f"ERROR: Summarizer Test - Could not save. Error: {e}")


if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # e.g., today_string = '2025-05-31'
    
    articles_from_file = load_articles_for_summarization_test(today_string)
    if articles_from_file:
        # Process only a few articles for standalone testing to save API calls
        summarized_articles_result = run_summarization(articles_from_file, articles_to_summarize_limit=2) 
        
        print("\n--- Standalone Summarizer Test Output (Processed Articles) ---")
        for i, article in enumerate(summarized_articles_result):
            if i < 2 : # Print details only for those we attempted to summarize
                print(f"\nArticle Title: {article.get('title', 'N/A')}")
                print(f"  Source: {article.get('source', 'N/A')}")
                print(f"  Popular Summary: {article.get('popular_summary', 'N/A')}")
            if i == 1 and len(summarized_articles_result) > 2:
                print(f"\n  ... and {len(summarized_articles_result) - 2} more articles processed with summary placeholders (if limit was hit).")
                break

        # For testing, save the result of this standalone run
        save_processed_articles_test(summarized_articles_result, today_string)