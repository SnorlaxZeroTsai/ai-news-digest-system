# --- src/ingestion/scraper.py ---

import feedparser
import requests
import time
from datetime import datetime

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

if __name__ == '__main__':
    # This block of code will only run when scraper.py is executed directly.
    # It's useful for independent testing of this module.
    articles = fetch_rss_feeds()
    
    if articles:
        print(f"\nTotal articles fetched: {len(articles)}")
        print("--- Displaying first 5 articles as an example ---")
        for article in articles[:5]:
            print("---")
            print(f"  Source: {article['source']}")
            print(f"  Title: {article['title']}")
            print(f"  Link: {article['link']}")
            print(f"  Published Date: {article['published_date']}")
            # The summary can be very long, so let's show the first 100 characters.
            # print(f"  Summary: {article['summary'][:100]}...") 
    else:
        print("No articles were fetched.")