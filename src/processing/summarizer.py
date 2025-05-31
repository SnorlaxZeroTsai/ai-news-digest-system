import json
import os
from datetime import datetime
from openai import OpenAI
import time

# Define the path to the data
RAW_DATA_DIR = 'data/raw' 
PROCESSED_DATA_DIR = 'data/processed' # New directory for processed data

# --- API Key Handling for OpenAI ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable not set.")

# --- LLM Configuration for OpenAI ---
DEFAULT_OPENAI_MODEL_NAME = "gpt-3.5-turbo" 
MAX_TOKENS_TO_SAMPLE = 1024 
TEMPERATURE = 0.2 

def load_articles_for_summarization(date_str):
    """
    Loads articles from the JSON file that includes full_text.
    """
    file_path = os.path.join(RAW_DATA_DIR, f'{date_str}_combined_sources_fulltext_articles.json')
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        print(f"Please ensure 'src/ingestion/scraper.py' has been run to generate this file with full text.")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Successfully loaded {len(articles)} articles from {file_path} (expected to contain full text).")
        return articles
    except Exception as e:
        print(f"ERROR: Could not load or parse the file {file_path}. Error: {e}")
        return []

def construct_popular_science_prompt_for_openai(article_title, article_content):
    """
    Constructs system and user prompts for OpenAI API for popular science summary.
    (This function remains the same)
    """
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
    """
    Generates a summary using the OpenAI Chat Completions API.
    (This function remains largely the same)
    """
    if not client:
        print("ERROR: OpenAI client not initialized (API key might be missing).")
        return "Error: API client not initialized."

    system_prompt, user_prompt = construct_popular_science_prompt_for_openai(article_title, article_content)
    try:
        print(f"\nRequesting summary for: '{article_title[:80]}...' from OpenAI model {model_name} using its full text (or best available).")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temp,
            n=1,
            stop=None
        )
        if response.choices and len(response.choices) > 0:
            summary_text = response.choices[0].message.content
            print("Summary generated successfully by OpenAI.")
            return summary_text.strip()
        else:
            print("ERROR: No choices found in the OpenAI API response or unexpected response structure.")
            # print(f"Full API Response: {response}") # Uncomment for debugging
            return "Error: Could not extract summary from OpenAI API response."
    except openai.APIConnectionError as e:
        print(f"ERROR: OpenAI API connection error: {e}")
        return f"Error: API Connection Error - {e.__cause__}"
    except openai.RateLimitError as e:
        print(f"ERROR: OpenAI API rate limit exceeded: {e}")
        return "Error: API Rate Limit Exceeded"
    except openai.APIStatusError as e:
        print(f"ERROR: OpenAI API status error: {e.status_code} - {e.response}")
        return f"Error: API Status Error {e.status_code}"
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during OpenAI summary generation: {e}")
        import traceback
        print(traceback.format_exc())
        return "Error: Unexpected error during OpenAI summarization."

# --- New function to save processed articles ---
def save_processed_articles(articles, date_str):
    """
    Saves the list of articles (now including summaries) to a new JSON file
    in the data/processed/ directory.
    """
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True) # Ensure the directory exists
    file_path = os.path.join(PROCESSED_DATA_DIR, f'{date_str}_processed_articles.json')
    
    print(f"\nSaving processed articles to {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(articles)} processed articles to {file_path}.")
    except Exception as e:
        print(f"ERROR: Could not save processed articles to JSON file. Error: {e}")


if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # e.g., today_string = '2025-05-31' 
    
    articles_to_process = load_articles_for_summarization(today_string)
    processed_articles_list = [] # To store articles that have been summarized

    if articles_to_process and OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        print(f"\n--- OpenAI Summarization with Full Text (Processing first {min(2, len(articles_to_process))} articles) ---")
        
        # Create a copy to modify, or modify in place if that's intended
        articles_with_summaries = list(articles_to_process) # Create a shallow copy

        for i, article in enumerate(articles_with_summaries[:2]): # Process first 2 for testing
            title = article.get('title', 'N/A')
            content_to_summarize = article.get('full_text', '') 
            
            if not content_to_summarize or len(content_to_summarize.strip()) < 50:
                print(f"    WARNING: 'full_text' for '{title}' is missing or too short. Falling back.")
                content_to_summarize = article.get('summary_from_feed', article.get('summary_from_list', ''))
                if not content_to_summarize and title != 'N/A':
                    content_to_summarize = title
                elif title != 'N/A' and content_to_summarize:
                     content_to_summarize = title + ". " + content_to_summarize

            if not content_to_summarize or not content_to_summarize.strip() or content_to_summarize.strip() == ".":
                print(f"\nSkipping article '{title}' due to insufficient content for summarization.")
                article['popular_summary'] = "Content insufficient for summarization." # Add placeholder
                processed_articles_list.append(article) # Still add to list for saving
                continue
                
            print(f"\nInput Content for '{title}' (first 500 chars of content to summarize):\n{content_to_summarize[:500]}...")
            
            generated_summary = generate_summary_with_openai(title, content_to_summarize, openai_client)
            
            print(f"\n--- Generated Popular Science Summary for '{title}' (Using OpenAI) ---")
            print(generated_summary)
            print("--- End of Summary ---")
            
            article['popular_summary'] = generated_summary
            processed_articles_list.append(article) # Add processed article to new list

            if i < len(articles_with_summaries[:2]) - 1: 
                time.sleep(1) 

        # Add remaining unprocessed articles to the list if you want to save all of them
        # Or only save the ones that were processed (i.e., attempted for summarization)
        # For now, `processed_articles_list` only contains the articles we attempted to summarize.
        # If you want to save ALL original articles, with summaries added to those processed,
        # you'd iterate through `articles_to_process` and update them, then save `articles_to_process`.
        # Let's modify to save all original articles, adding summaries where generated:
        
        # Reset and repopulate processed_articles_list with all articles, adding summaries
        all_articles_for_saving = []
        for original_article in articles_to_process:
            # Find if this article was processed and has a summary
            summary_added = False
            for processed_article_with_summary in processed_articles_list:
                if original_article['link'] == processed_article_with_summary['link']:
                    all_articles_for_saving.append(processed_article_with_summary)
                    summary_added = True
                    break
            if not summary_added:
                # If not processed (e.g. was beyond the [:2] limit), add original with placeholder
                original_article['popular_summary'] = "Not processed for summary in this run."
                all_articles_for_saving.append(original_article)
        
        # *** MODIFICATION: Call the new save function ***
        if all_articles_for_saving:
            save_processed_articles(all_articles_for_saving, today_string)
                
    elif not OPENAI_API_KEY:
        print("\nSkipping OpenAI summarization test because OPENAI_API_KEY is not set.")
    else:
        print("\nNo articles loaded or full_text JSON not found, skipping OpenAI summarization test.")