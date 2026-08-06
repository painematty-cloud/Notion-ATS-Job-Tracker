import os
import re
import time
from datetime import datetime, timedelta, date
import requests
from ddgs import DDGS

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

SEARCH_QUERIES = [
    'site:jobs.ashbyhq.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:boards.greenhouse.io ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:apply.workable.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:jobs.lever.co ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:myworkdayjobs.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid'
]

def detect_ats_platform(url):
    if "ashbyhq.com" in url:
        return "Ashby"
    elif "greenhouse.io" in url:
        return "Greenhouse"
    elif "workable.com" in url:
        return "Workable"
    elif "lever.co" in url:
        return "Lever"
    elif "myworkdayjobs.com" in url:
        return "Workday"
    return "Other"

def extract_company_name(title, url):
    if " at " in title:
        parts = title.split(" at ")
        if len(parts) > 1:
            return parts[-1].split(" - ")[0].strip()
    
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        domain = match.group(1)
        if "greenhouse.io" in domain or "ashbyhq.com" in domain or "lever.co" in domain:
            parts = url.split('/')
            if len(parts) > 3 and parts[3]:
                return parts[3].capitalize()
    return "Unknown Company"

def is_within_last_week(text):
    text_lower = text.lower()
    if "months ago" in text_lower or "year ago" in text_lower:
        return False
    match = re.search(r'(\d+)\s+days?\s+ago', text_lower)
    if match and int(match.group(1)) > 7:
        return False
    return True

def get_existing_notion_urls():
    notion_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    existing_urls = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {}
        if start_cursor:
            payload["start_cursor"] = start_cursor
            
        res = requests.post(notion_url, json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            for page in data.get("results", []):
                props = page.get("properties", {})
                url_prop = props.get("URL", {})
                if url_prop.get("type") == "url":
                    url_val = url_prop.get("url")
                    if url_val:
                        existing_urls.add(url_val)
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        else:
            print(f"Failed to fetch existing Notion pages: {res.text}")
            break
            
    print(f"Loaded {len(existing_urls)} existing jobs from Notion to avoid duplicates.")
    return existing_urls

def search_duckduckgo_with_retry(query, retries=3):
    """Searches with built-in retry logic and timeouts to prevent drops."""
    for attempt in range(retries):
        try:
            print(f"Searching for query (Attempt {attempt + 1}): {query}")
            job_results = []
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=10, backend='html'))
                print(f"Found {len(results)} raw results for query.")
                for r in results:
                    title = r.get("title", "Job Posting")
                    link = r.get("href", "")
                    snippet = r.get("body", "")
                    if link:
                        if is_within_last_week(snippet + " " + title):
                            job_results.append({
                                "title": title,
                                "link": link,
                                "company": extract_company_name(title, link),
                                "platform": detect_ats_platform(link)
                            })
            return job_results
        except Exception as e:
            print(f"Attempt {attempt + 1} failed due to error: {e}")
            if attempt < retries - 1:
                time.sleep(5) # Wait 5 seconds before retrying
            else:
                print("All retries failed for this query.")
                return []

def add_to_notion(job):
    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    today_date = date.today().isoformat()
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Job Title": {"title": [{"text": {"content": job["title"]}}]},
            "Company": {"rich_text": [{"text": {"content": job["company"]}}]},
            "ATS Platform": {"select": {"name": job["platform"]}},
            "Date Added": {"date": {"start": today_date}},
            "URL": {"url": job["link"]},
            "Priority Tier": {"select": {"name": "Tier 1"}},
            "Target Base Salary": {"rich_text": [{"text": {"content": "update this field"}}]}
        }
    }
    
    res = requests.post(notion_url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"Successfully added to Notion: {job['title']} ({job['company']})")
    else:
        print(f"FAILED to add to Notion ({res.status_code}): {res.text}")

def main():
    seen_urls = get_existing_notion_urls()
    
    for query in SEARCH_QUERIES:
        items = search_duckduckgo_with_retry(query)
        for item in items:
            link = item.get("link", "")
            if link and link not in seen_urls:
                seen_urls.add(link)
                add_to_notion(item)
        
        # Pause for 3 seconds between queries to prevent triggering rate limits/timeouts
        time.sleep(3)

if __name__ == "__main__":
    main()
