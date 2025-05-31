import feedparser
import requests
import time
from datetime import datetime
import json
import os
from bs4 import BeautifulSoup

RSS_FEEDS = {
    'Google AI Blog': 'https://blog.google/technology/ai/rss/',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/'
}
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
REQUEST_TIMEOUT = 20


def get_full_article_text(article_url, headers):
    """
    Fetches and extracts the main textual content from a given article URL.
    This is a generic extractor and might need site-specific rules for better accuracy.
    """
    print(f"    Fetching full text for: {article_url}")
    try:
        response = requests.get(article_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Generic Content Extraction Heuristics ---
        # Try common tags/attributes for main content. This order can be important.
        # 1. <article> tag
        main_content = soup.find('article')
        
        # 2. Common div IDs or classes
        if not main_content:
            common_selectors = [
                'div#content', 'div#main-content', 'div#main', 
                'div.post-content', 'div.article-content', 'div.entry-content',
                'div.story-content', 'div.article-body', 'div.main-article-content',
                'main#main', 'main.main-content' 
            ]
            for selector in common_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
        
        # 3. Fallback: try to find the largest text block if no semantic tags are found
        if not main_content:
            # This is a more complex heuristic and can be added later if needed.
            # For now, if the above fails, we might just get limited text or fail gracefully.
            print(f"    WARNING: Could not find a clear main content container for {article_url}. Text might be incomplete.")
            # As a very basic fallback, take all <p> tags. This can be noisy.
            paragraphs = soup.find_all('p')
            text_content = "\n".join([p.get_text(strip=True) for p in paragraphs])
            return text_content if text_content else "Could not extract main content (fallback)."


        if main_content:
            # Remove script, style, nav, header, footer, aside, form, etc. before extracting text
            for unwanted_tag in main_content.select('script, style, nav, header, footer, aside, form, .share-links, .related-posts, .comments, #comments'):
                unwanted_tag.decompose()
            
            # Get text from the main content area, joining paragraphs
            paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
            text_content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Basic cleaning: reduce multiple newlines
            text_content = '\n'.join(filter(None, text_content.splitlines()))
            
            print(f"    Successfully extracted text (length: {len(text_content)}) for: {article_url}")
            return text_content if text_content else "Main content container found, but no text extracted."
        else:
            print(f"    ERROR: Main content container not found for {article_url}")
            return "Main content container not found."

    except requests.exceptions.RequestException as e:
        print(f"    ERROR: Network error fetching full text for {article_url}: {e}")
        return f"Error fetching content: Network error - {e}"
    except Exception as e:
        print(f"    ERROR: Unexpected error extracting full text for {article_url}: {e}")
        import traceback
        print(traceback.format_exc())
        return f"Error extracting content: Unexpected error - {e}"


def fetch_rss_feeds():
    """Fetches all RSS feeds defined in RSS_FEEDS and their full article text."""
    print("Starting to fetch RSS feeds and full articles...")
    all_articles = []
    headers = {'User-Agent': USER_AGENT}
    for source_name, url in RSS_FEEDS.items():
        print(f"Processing source: {source_name} ({url})")
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            response.raise_for_status() 
            feed = feedparser.parse(response.content)
            for i, entry in enumerate(feed.entries):
                # Limit to fetching full text for a few articles per feed for now during testing
                if i >= 3 and source_name == 'MIT Technology Review': # Example: fetch only 3 from MIT
                     print(f"    Skipping full text fetch for further articles from {source_name} in this run.")
                     break
                if i >= 2 and source_name == 'Google AI Blog': # Example: fetch only 2 from Google
                     print(f"    Skipping full text fetch for further articles from {source_name} in this run.")
                     break

                published_time = None
                if 'published_parsed' in entry and entry.published_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                
                article_link = entry.get('link', 'N/A')
                full_text = "Full text not fetched." # Default
                if article_link != 'N/A':
                    full_text = get_full_article_text(article_link, headers)
                    time.sleep(1) # Be respectful, add a small delay between fetching full articles

                article_data = {
                    'source': source_name,
                    'title': entry.get('title', 'N/A'),
                    'link': article_link,
                    'published_date': published_time.strftime('%Y-%m-%d %H:%M:%S') if published_time else 'N/A',
                    'summary_from_feed': entry.get('summary', 'N/A'), # Keep original summary
                    'full_text': full_text # Add the new full text
                }
                all_articles.append(article_data)
            print(f"Successfully processed {len(feed.entries)} entries (full text attempted for a subset) from {source_name}.")
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not fetch RSS feed from {source_name}. Network error: {e}")
        except Exception as e:
            print(f"ERROR: An unknown error occurred while processing {source_name}: {e}")
    return all_articles

def fetch_stanford_hai_news_requests(max_pages=1): # Reduced max_pages for quicker testing of full text
    """
    Fetches news articles from the Stanford HAI News website and their full article text.
    """
    print("Starting to scrape Stanford HAI News (including full text)...")
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
            posts = soup.select('div[class*="ContentCard_root__"]')
            
            if not posts and page_num > 1:
                print(f"No more posts found on page {page_num}, stopping.")
                break
            
            page_articles_count = 0
            # Limit to fetching full text for a few articles per page for testing
            for i, post_container in enumerate(posts):
                if i >= 2: # Fetch full text for first 2 articles on the page
                    print(f"    Skipping full text fetch for further articles on this page in this run.")
                    break 

                title_link_element = post_container.select_one('a.ContentCard_titleLink__PPsdO')
                title, link, date_str, summary_from_list = 'N/A', '#', 'N/A', ''
                
                if title_link_element:
                    title = title_link_element.get_text(strip=True)
                    link = title_link_element.get('href', '#')
                    if not link.startswith('http'):
                        link = f"https://hai.stanford.edu{link}" if link.startswith('/') else f"https://hai.stanford.edu/news/{link}"
                
                    summary_element = post_container.select_one('div[class*="ContentCard_blurb__"] p')
                    summary_from_list = summary_element.get_text(strip=True) if summary_element else ''
                    
                    # Date extraction (heuristic, needs improvement)
                    meta_data_div = post_container.select_one('div.ContentMeta_data__blERF')
                    if meta_data_div:
                        date_spans = meta_data_div.select('span')
                        for span_tag in date_spans:
                            if not span_tag.find('a') and len(span_tag.get_text(strip=True)) < 15 and any(char.isdigit() for char in span_tag.get_text(strip=True)):
                                date_str = span_tag.get_text(strip=True)
                                break
                
                full_text = "Full text not fetched."
                if link != '#':
                    full_text = get_full_article_text(link, headers)
                    time.sleep(1) # Be respectful

                if title != 'N/A' and link != '#':
                    all_articles.append({
                        'source': source_name,
                        'title': title,
                        'link': link,
                        'published_date': date_str,
                        'summary_from_list': summary_from_list, # Summary from the list page
                        'full_text': full_text
                    })
                    page_articles_count += 1
            print(f"Processed {page_articles_count} articles (full text attempted for a subset) on page {page_num}.")
            if page_num < max_pages and page_articles_count > 0:
                time.sleep(2)
        # ... (error handling from previous version) ...
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not fetch page {url}. Network error: {e}")
            break 
        except Exception as e:
            print(f"ERROR: An error occurred while parsing page {url}: {e}")
            import traceback
            print(traceback.format_exc())
            
    print(f"Successfully processed a total of {len(all_articles)} articles (full text attempted for a subset) from {source_name}.")
    return all_articles

def save_articles_to_json(articles, filename_prefix="combined_sources_fulltext"): # Changed prefix
    output_dir = 'data/raw'
    os.makedirs(output_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    file_path = os.path.join(output_dir, f'{today_str}_{filename_prefix}_articles.json') # Use new prefix
    print(f"\nSaving all articles to {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(articles)} articles to {file_path}.")
    except Exception as e:
        print(f"ERROR: Could not save articles to JSON file. Error: {e}")

if __name__ == '__main__':
    rss_articles = fetch_rss_feeds()
    stanford_articles = fetch_stanford_hai_news_requests(max_pages=1) # Reduced max_pages for testing
            
    all_fetched_articles = rss_articles + stanford_articles
    
    if all_fetched_articles:
        save_articles_to_json(all_fetched_articles, filename_prefix="combined_sources_fulltext")
    else:
        print("No articles were fetched from any source, skipping save.")