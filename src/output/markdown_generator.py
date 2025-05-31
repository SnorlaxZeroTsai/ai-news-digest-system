import json
import os
from datetime import datetime
from collections import defaultdict

PROCESSED_DATA_DIR = 'data/processed'
MARKDOWN_OUTPUT_DIR = 'newsletter_site/content/newsletter'

# Mapping English category labels (from classifier) to Chinese titles for the newsletter
# This can be expanded or moved to a config file.
CATEGORY_MAPPING_EN_TO_ZH = {
    "Research & Breakthroughs": "研究與突破",
    "Industry Applications & Case Studies": "產業應用與案例",
    "Ethics, Governance & Policy": "倫理、治理與政策",
    "AI Tools, Platforms & Resources": "AI工具、平台與資源",
    "Market Trends & Investments": "市場動態與投資",
    "Academic Conferences & Community Events": "學術會議與社區活動",
    "Unclassified": "未分類文章",
    "Error": "分類錯誤"
}

def load_processed_articles(date_str):
    """Loads the final processed articles JSON file for a specific date."""
    file_path = os.path.join(PROCESSED_DATA_DIR, f'{date_str}_final_ai_news.json')
    if not os.path.exists(file_path):
        print(f"ERROR: Processed file not found at {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"MarkdownGenerator: Successfully loaded {len(articles)} processed articles from {file_path}")
        return articles
    except Exception as e:
        print(f"MarkdownGenerator ERROR: Could not load or parse file {file_path}. Error: {e}")
        return None

def format_published_date(date_str):
    """Formats the published date string if it's valid, otherwise returns 'N/A'."""
    if not date_str or date_str == 'N/A':
        return 'N/A'
    try:
        # Assuming date_str is like "YYYY-MM-DD HH:MM:SS" or just "YYYY-MM-DD" or "MMM DD"
        # This parsing can be made more robust if various date formats are expected.
        dt_object = None
        if isinstance(date_str, str):
            if len(date_str) > 10 : # Likely includes time
                 dt_object = datetime.strptime(date_str.split()[0], '%Y-%m-%d') # Take only date part
            elif len(date_str) == 10 and '-' in date_str: # YYYY-MM-DD
                 dt_object = datetime.strptime(date_str, '%Y-%m-%d')
            # Add more formats if needed e.g. for "Apr 24"
            # For now, if not YYYY-MM-DD, return as is or 'N/A'
        if dt_object:
            return dt_object.strftime('%Y年%m月%d日')
        return date_str # Return original if not parsed as YYYY-MM-DD
    except ValueError:
        return date_str # Return original if parsing fails

def generate_newsletter_markdown(processed_articles, newsletter_date_obj):
    """
    Generates the full Markdown content for the newsletter from processed articles.
    """
    if not processed_articles:
        return "# AI 科普速遞 - 無內容\n\n今日未擷取或處理任何文章。"

    newsletter_date_str_zh = newsletter_date_obj.strftime('%Y年%m月%d日')
    markdown_content = [f"# AI 科普速遞 - {newsletter_date_str_zh}\n"]

    # Group articles by their primary classification
    articles_by_category = defaultdict(list)
    for article in processed_articles:
        primary_category = "Unclassified" # Default category
        if article.get('classification') and article['classification']['labels']:
            primary_category_en = article['classification']['labels'][0]
            primary_category = CATEGORY_MAPPING_EN_TO_ZH.get(primary_category_en, primary_category_en)
        
        # Filter out articles that were not successfully summarized or had issues
        if "Error:" in article.get('popular_summary', '') or \
           article.get('popular_summary', '') == "Content insufficient for summarization." or \
           article.get('popular_summary', '') == "Summarization skipped: API key not configured." or \
           article.get('popular_summary', '') == "Summarization skipped: processing limit reached.":
            print(f"Skipping article for markdown generation due to summarization issue: {article.get('title')}")
            continue

        articles_by_category[primary_category].append(article)

    # Define the desired order of categories
    category_order = [
        "研究與突破", "產業應用與案例", "倫理、治理與政策",
        "AI工具、平台與資源", "市場動態與投資", 
        "學術會議與社區活動", "未分類文章"
    ]

    for category_title_zh in category_order:
        if category_title_zh in articles_by_category and articles_by_category[category_title_zh]:
            markdown_content.append(f"\n## {category_title_zh}\n")
            for article in articles_by_category[category_title_zh]:
                title = article.get('title', '無標題')
                link = article.get('link', '#')
                source = article.get('source', '未知來源')
                # Use original published_date from ingestion, not the processing date
                published_date = format_published_date(article.get('published_date', 'N/A'))
                summary = article.get('popular_summary', '摘要生成失敗或無內容。')

                markdown_content.append(f"### [{title}]({link})")
                markdown_content.append(f"**來源：** {source} | **原文發布日期：** {published_date}\n")
                markdown_content.append(f"{summary}\n")
                markdown_content.append(f"[閱讀原文]({link})")
                markdown_content.append("\n---\n")
    
    return "\n".join(markdown_content)

def save_markdown_newsletter(markdown_str, date_obj):
    """Saves the generated Markdown string to a file."""
    os.makedirs(MARKDOWN_OUTPUT_DIR, exist_ok=True)
    date_file_str = date_obj.strftime('%Y-%m-%d')
    file_path = os.path.join(MARKDOWN_OUTPUT_DIR, f'{date_file_str}.md') 

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_str)
        print(f"MarkdownGenerator: Successfully saved Markdown newsletter to {file_path}")
        return file_path
    except Exception as e:
        print(f"MarkdownGenerator ERROR: Could not save Markdown file. Error: {e}")
        return None

if __name__ == '__main__':
    today_date_obj = datetime.now()
    today_string_for_load = today_date_obj.strftime('%Y-%m-%d')
    
    articles = load_processed_articles(today_string_for_load)
    if articles:
        markdown_output = generate_newsletter_markdown(articles, today_date_obj)
        if markdown_output:
            save_markdown_newsletter(markdown_output, today_date_obj)
    else:
        print("MarkdownGenerator: No processed articles to generate Markdown newsletter.")