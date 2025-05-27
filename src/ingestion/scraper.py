import feedparser
import requests
import time
from datetime import datetime
import json
import os

# Define the RSS feeds to fetch.
# Using a dictionary allows for easy extension in the future.
RSS_FEEDS = {
    'Google AI Blog': 'https://blog.google/technology/ai/rss/',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/'
}

def fetch_rss_feeds():
    """
    Fetches all RSS feeds defined in RSS_FEEDS and extracts article information.
    """
    print("Starting to fetch RSS feeds...")
    all_articles = []

    for source_name, url in RSS_FEEDS.items():
        print(f"Processing source: {source_name} ({url})")
        try:
            # Use requests to get the feed content with a timeout.
            response = requests.get(url, timeout=15)
            # Raise an exception for bad status codes (4xx or 5xx).
            response.raise_for_status() 

            # Parse the response content using feedparser.
            feed = feedparser.parse(response.content)

            # Iterate through each entry in the feed.
            for entry in feed.entries:
                # Attempt to parse the publication date.
                published_time = None
                if 'published_parsed' in entry and entry.published_parsed:
                    # feedparser attempts to parse dates into a time.struct_time.
                    published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

                article_data = {
                    'source': source_name,
                    'title': entry.get('title', 'N/A'),
                    'link': entry.get('link', 'N/A'),
                    'published_date': published_time.strftime('%Y-%m-%d %H:%M:%S') if published_time else 'N/A',
                    'summary': entry.get('summary', 'N/A')
                }
                all_articles.append(article_data)
            
            print(f"Successfully fetched {len(feed.entries)} articles from {source_name}.")

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not fetch RSS feed from {source_name}. Network error: {e}")
        except Exception as e:
            print(f"ERROR: An unknown error occurred while processing {source_name}: {e}")

    return all_articles

def save_articles_to_json(articles):
    """
    Saves a list of articles to a JSON file in the data/raw/ directory.
    The filename includes the current date.
    """
    # Define the output directory based on our project structure.
    output_dir = 'data/raw'
    # Ensure the output directory exists.
    os.makedirs(output_dir, exist_ok=True)

    # Generate a filename with today's date.
    today_str = datetime.now().strftime('%Y-%m-%d')
    file_path = os.path.join(output_dir, f'{today_str}_rss_articles.json')

    print(f"Saving articles to {file_path}...")

    # Write the articles list to the JSON file.
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            # json.dump writes the Python object to a file.
            # ensure_ascii=False is important for correctly handling non-English characters.
            # indent=4 makes the JSON file human-readable.
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(articles)} articles.")
    except Exception as e:
        print(f"ERROR: Could not save articles to JSON file. Error: {e}")


if __name__ == '__main__':
    # This block of code will only run when scraper.py is executed directly.
    # It's useful for independent testing of this module.
    fetched_articles = fetch_rss_feeds()
    
    if fetched_articles:
        save_articles_to_json(fetched_articles)
    else:
        print("No articles were fetched, skipping save.")