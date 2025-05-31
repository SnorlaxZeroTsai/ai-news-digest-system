import json
import os
from datetime import datetime
from openai import OpenAI # Ensure OpenAI SDK is imported
import time

# Define the path to the data (now expecting files with full text)
DATA_DIR = 'data/raw' 

# --- API Key Handling for OpenAI ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    # Consider raising an exception or exiting

# --- LLM Configuration for OpenAI ---
DEFAULT_OPENAI_MODEL_NAME = "gpt-3.5-turbo" 
MAX_TOKENS_TO_SAMPLE = 1024 
TEMPERATURE = 0.2 

def load_articles_for_summarization(date_str):
    """
    Loads articles from the JSON file that now includes full_text.
    """
    # *** MODIFICATION: Update filename to look for fulltext articles ***
    file_path = os.path.join(DATA_DIR, f'{date_str}_combined_sources_fulltext_articles.json')
    
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
    (This function remains the same as before, as it already takes article_content)
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
    (This function remains largely the same, it just receives different article_content now)
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
            print(f"Full API Response: {response}")
            return "Error: Could not extract summary from OpenAI API response."
    except openai.APIConnectionError as e: # Make sure to import 'openai' if not already done at top level
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


if __name__ == '__main__':
    today_string = datetime.now().strftime('%Y-%m-%d')
    # e.g., today_string = '2025-05-31' # Ensure this file exists with full text
    
    articles_data = load_articles_for_summarization(today_string)
    
    if articles_data and OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        print(f"\n--- OpenAI Summarization with Full Text (Processing first {min(2, len(articles_data))} articles) ---")
        for i, article in enumerate(articles_data[:2]): 
            title = article.get('title', 'N/A')
            
            # *** MODIFICATION: Use 'full_text' as primary content for summarization ***
            content_to_summarize = article.get('full_text', '') 
            
            # Fallback logic if full_text is missing or very short
            if not content_to_summarize or len(content_to_summarize.strip()) < 50: # Arbitrary length check
                print(f"    WARNING: 'full_text' for '{title}' is missing or too short. Falling back to summary_from_feed/list or title.")
                content_to_summarize = article.get('summary_from_feed', article.get('summary_from_list', ''))
                if not content_to_summarize and title != 'N/A':
                    content_to_summarize = title
                elif title != 'N/A' and content_to_summarize:
                     content_to_summarize = title + ". " + content_to_summarize


            if not content_to_summarize or not content_to_summarize.strip() or content_to_summarize.strip() == ".":
                print(f"\nSkipping article '{title}' due to insufficient content for summarization after fallbacks.")
                continue
                
            print(f"\nInput Content for '{title}' (first 500 chars):\n{content_to_summarize[:500]}...")
            
            generated_summary = generate_summary_with_openai(title, content_to_summarize, openai_client)
            
            print(f"\n--- Generated Popular Science Summary for '{title}' (Using OpenAI with full text) ---")
            print(generated_summary)
            print("--- End of Summary ---")
            
            if i < len(articles_data[:2]) - 1: 
                time.sleep(1) 
                
    elif not OPENAI_API_KEY:
        print("\nSkipping OpenAI summarization test because OPENAI_API_KEY is not set.")
    else:
        print("\nNo articles loaded or full_text JSON not found, skipping OpenAI summarization test.")