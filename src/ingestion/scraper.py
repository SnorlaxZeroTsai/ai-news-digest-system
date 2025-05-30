import feedparser
import requests # Ensure requests is imported
import time
from datetime import datetime
import json
import os

# --- BeautifulSoup for parsing ---
from bs4 import BeautifulSoup # Ensure BeautifulSoup is imported

# Define the RSS feeds to fetch.
RSS_FEEDS = {
    'Google AI Blog': 'https://blog.google/technology/ai/rss/',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/'
}

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
REQUEST_TIMEOUT = 20 # seconds

def fetch_rss_feeds():
    """Fetches all RSS feeds defined in RSS_FEEDS."""
    print("Starting to fetch RSS feeds...")
    # ... (此函數內容與之前相同，為節省篇幅省略) ...
    all_articles = []
    headers = {'User-Agent': USER_AGENT}
    for source_name, url in RSS_FEEDS.items():
        print(f"Processing source: {source_name} ({url})")
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            response.raise_for_status() 
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                published_time = None
                if 'published_parsed' in entry and entry.published_parsed:
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

def fetch_stanford_hai_news_requests(max_pages=2):
    """
    Fetches news articles from the Stanford HAI News website using requests and BeautifulSoup.
    Uses updated selectors based on provided HTML snippet.
    """
    print("Starting to scrape Stanford HAI News using requests+bs4 with updated selectors...")
    source_name = 'Stanford HAI News'
    base_url = 'https://hai.stanford.edu/news'
    all_articles = []
    headers = {'User-Agent': USER_AGENT}

    for page_num in range(1, max_pages + 1):
        url = f"{base_url}?page={page_num}"
        print(f"Scraping page: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Updated selector for the main card container
            # Using a class that seems more specific to the card root
            posts = soup.select('div[class*="ContentCard_root__"]') 

            if not posts and page_num > 1:
                print(f"No more posts found on page {page_num} using selector 'div[class*=\"ContentCard_root__\"]', stopping.")
                break 

            page_articles_count = 0
            for post_container in posts:
                # Updated selector for title and link, targeting the specific link class
                title_link_element = post_container.select_one('a.ContentCard_titleLink__PPsdO')
                
                title = 'N/A'
                link = '#'
                
                if title_link_element:
                    title = title_link_element.get_text(strip=True)
                    link = title_link_element.get('href', '#')
                    
                    if not link.startswith('http'):
                        if link.startswith('/'):
                            link = f"https://hai.stanford.edu{link}"
                        else:
                            # This case might need refinement if relative paths are complex
                            link = f"https://hai.stanford.edu/news/{link}" 
                
                # Updated selector for summary/blurb
                summary_element = post_container.select_one('div[class*="ContentCard_blurb__"] p')
                summary = summary_element.get_text(strip=True) if summary_element else ''

                # Date extraction: Attempt to find date within ContentMeta_data__blERF
                # This is a heuristic and might need refinement
                date_str = 'N/A'
                meta_data_div = post_container.select_one('div.ContentMeta_data__blERF')
                if meta_data_div:
                    # Look for a span that likely contains a short date string (e.g., "Apr 24")
                    # and doesn't contain a link to a topic
                    date_spans = meta_data_div.select('span')
                    for span in date_spans:
                        # A simple check: if it doesn't contain an 'a' tag and has short text
                        if not span.find('a') and len(span.get_text(strip=True)) < 15 and any(char.isdigit() for char in span.get_text(strip=True)):
                            date_str = span.get_text(strip=True)
                            break # Take the first likely candidate

                # Only add if we successfully found a title and link
                if title != 'N/A' and link != '#':
                    article_data = {
                        'source': source_name,
                        'title': title,
                        'link': link,
                        'published_date': date_str, 
                        'summary': summary
                    }
                    all_articles.append(article_data)
                    page_articles_count += 1
            
            print(f"Found {page_articles_count} articles on page {page_num}.")
            if page_num < max_pages and page_articles_count > 0:
                time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not fetch page {url}. Network error: {e}")
            break
        except Exception as e:
            print(f"ERROR: An error occurred while parsing page {url}: {e}")
            import traceback
            print(traceback.format_exc())
    
    print(f"Successfully scraped a total of {len(all_articles)} articles from {source_name}.")
    return all_articles


def save_articles_to_json(articles, filename_prefix="combined"):
    # ... (此函數內容與之前相同，為節省篇幅省略) ...
    output_dir = 'data/raw'
    os.makedirs(output_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    file_path = os.path.join(output_dir, f'{today_str}_{filename_prefix}_articles.json')
    print(f"\nSaving all articles to {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(articles)} articles to {file_path}.")
    except Exception as e:
        print(f"ERROR: Could not save articles to JSON file. Error: {e}")

if __name__ == '__main__':
    rss_articles = fetch_rss_feeds()
    stanford_articles = fetch_stanford_hai_news_requests(max_pages=2)
    all_fetched_articles = rss_articles + stanford_articles
    
    if all_fetched_articles:
        save_articles_to_json(all_fetched_articles, filename_prefix="combined_sources")
    else:
        print("No articles were fetched from any source, skipping save.")