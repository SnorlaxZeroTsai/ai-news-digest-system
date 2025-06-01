import json
import os
from datetime import datetime, date
from collections import defaultdict
import re # Keep for create_slug_from_title if it remains here for standalone testing

PROCESSED_DATA_DIR = 'data/processed'
MARKDOWN_OUTPUT_DIR = 'newsletter_site/content/newsletter'
MANUAL_IMAGE_BASE_PATH_FOR_MARKDOWN = "/images/manual_summaries" # Used by main.py
MANUAL_IMAGE_ACTUAL_BASE_DIR = os.path.join('newsletter_site', 'static', 'images', 'manual_summaries') # For checking existence

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

def create_slug_from_title(title): # This function might be moved to utils later
    """Creates a simplified slug from an article title for filenames."""
    if not title: import uuid; return str(uuid.uuid4())[:8]
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'\s+', '_', slug).strip('_')
    return slug[:50]


def load_processed_articles(date_str):
    file_path = os.path.join(PROCESSED_DATA_DIR, f'{date_str}_final_ai_news.json')
    if not os.path.exists(file_path): print(f"ERROR: Processed file not found at {file_path}"); return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f: articles = json.load(f)
        print(f"MarkdownGenerator: Successfully loaded {len(articles)} articles from {file_path}")
        return articles
    except Exception as e: print(f"MarkdownGenerator ERROR: Could not load or parse file {file_path}. Error: {e}"); return None

def format_published_date(date_str):
    if not date_str or date_str == 'N/A': return 'N/A'
    try:
        dt_object = None
        if isinstance(date_str, str):
            if len(date_str) > 10 : dt_object = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
            elif len(date_str) == 10 and '-' in date_str: dt_object = datetime.strptime(date_str, '%Y-%m-%d')
        if dt_object: return dt_object.strftime('%Y年%m月%d日')
        return date_str 
    except ValueError: return date_str

def generate_newsletter_markdown(processed_articles, newsletter_date_obj):
 
    if not processed_articles:
        fm_title = f"AI 科普速遞 - {newsletter_date_obj.strftime('%Y年%m月%d日')}"
        fm_date = newsletter_date_obj.strftime('%Y-%m-%d')
        front_matter = f"---\ntitle: \"{fm_title}\"\ndate: {fm_date}\n---\n"
        return f"{front_matter}\n# {fm_title}\n\n今日未擷取或處理任何文章。"

    fm_title_date_str_zh = newsletter_date_obj.strftime('%Y年%m月%d日')
    fm_date_str_iso = newsletter_date_obj.strftime('%Y-%m-%d')
    
    front_matter = (
        f"---\n"
        f"title: \"AI 科普速遞 - {fm_title_date_str_zh}\"\n"
        f"date: {fm_date_str_iso}\n"
        f"---\n"
    )
    markdown_content_parts = [f"# AI 科普速遞 - {fm_title_date_str_zh}\n"]
    articles_by_category = defaultdict(list)
    
    for article in processed_articles:
        primary_category_en = (article.get('classification') and article['classification']['labels'] and article['classification']['labels'][0]) or "Unclassified"
        primary_category = CATEGORY_MAPPING_EN_TO_ZH.get(primary_category_en, primary_category_en)
        if "Error:" in article.get('popular_summary', '') or \
           article.get('popular_summary', '') == "Content insufficient for summarization." or \
           article.get('popular_summary', '') == "Summarization skipped: API key not configured." or \
           article.get('popular_summary', '') == "Summarization skipped: processing limit reached.":
            print(f"Skipping article for markdown due to summarization issue: {article.get('title')}")
            continue
        articles_by_category[primary_category].append(article)

    category_order = ["研究與突破", "產業應用與案例", "倫理、治理與政策", "AI工具、平台與資源", "市場動態與投資", "學術會議與社區活動", "未分類文章"]


    for category_title_zh in category_order:
        if category_title_zh in articles_by_category and articles_by_category[category_title_zh]:
            markdown_content_parts.append(f"\n## {category_title_zh}\n")
            for article in articles_by_category[category_title_zh]:
                title = article.get('title', '無標題')
                link = article.get('link', '#')
                source = article.get('source', '未知來源')
                published_date = format_published_date(article.get('published_date', 'N/A'))
                summary = article.get('popular_summary', '摘要生成失敗或無內容。')

        
                image_markdown_path_from_json = article.get('image_expected_markdown_path')
                image_to_check_filename = article.get('image_expected_filename') # e.g., YYYY-MM-DD_slug.png
                
                image_markdown_to_insert = None # Initialize

                if image_markdown_path_from_json and image_to_check_filename:
                    # Construct the actual file system path to check for existence
                    # Assumes image_date_folder_name is the YYYY-MM-DD part of image_to_check_filename
                    image_date_folder_name = image_to_check_filename.split('_')[0] # Extracts YYYY-MM-DD
                    actual_image_file_path = os.path.join(MANUAL_IMAGE_ACTUAL_BASE_DIR, 
                                                          image_date_folder_name, 
                                                          image_to_check_filename)
                    
                    if os.path.exists(actual_image_file_path):
                        image_markdown_to_insert = image_markdown_path_from_json
                        print(f"    Found manual image for '{title}': {image_markdown_to_insert}")
                    else:
                        print(f"    INFO: Manual image not found for '{title}' at {actual_image_file_path} (expected Markdown path: {image_markdown_path_from_json})")
                else:
                    print(f"    INFO: No expected image path/filename in JSON for '{title}'.")

                markdown_content_parts.append(f"### [{title}]({link})")
                
                if image_markdown_to_insert:
                    markdown_content_parts.append(f"\n![{title}]({image_markdown_to_insert})\n")

                markdown_content_parts.append(f"**來源：** {source} | **原文發布日期：** {published_date}\n")
                markdown_content_parts.append(f"{summary}\n")
                markdown_content_parts.append(f"[閱讀原文]({link})")
                markdown_content_parts.append("\n---\n")
    
    return front_matter + "\n".join(markdown_content_parts)


def save_markdown_newsletter(markdown_str, date_obj):
    os.makedirs(MARKDOWN_OUTPUT_DIR, exist_ok=True)
    date_file_str = date_obj.strftime('%Y-%m-%d')
    file_path = os.path.join(MARKDOWN_OUTPUT_DIR, f'{date_file_str}.md') 
    try:
        with open(file_path, 'w', encoding='utf-8') as f: f.write(markdown_str)
        print(f"MarkdownGenerator: Successfully saved Markdown newsletter to {file_path}")
        return file_path
    except Exception as e: print(f"MarkdownGenerator ERROR: Could not save Markdown file. Error: {e}"); return None

if __name__ == '__main__':
    today_date_obj = datetime.now()
    today_string_for_load = today_date_obj.strftime('%Y-%m-%d')
    articles = load_processed_articles(today_string_for_load) # This now expects _final_ai_news.json
    if articles:
        markdown_output = generate_newsletter_markdown(articles, today_date_obj)
        if markdown_output: save_markdown_newsletter(markdown_output, today_date_obj)
    else:
        print("MarkdownGenerator: No processed articles, generating an empty newsletter page.")
        empty_markdown_output = generate_newsletter_markdown([], today_date_obj)
        save_markdown_newsletter(empty_markdown_output, today_date_obj)