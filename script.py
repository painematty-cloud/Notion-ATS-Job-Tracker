import os
import re
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

def search_duckduckgo(query):
    print(f"Searching DuckDuckGo for: {query}")
    job_results = []
    try:
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
                    else:
                        print(f"Filtered out old listing (> 7 days): {title}")
    except Exception as e:
        print(f"Error fetching DuckDuckGo search results: {e}")
    return job_results

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
            "Stage": {"status": {"name": "Not Started"}},
            "Priority Tier": {"select": {"name": "Tier 1"}},
            # Fields that cannot be scraped are populated with "update this field" where supported:
            "Target Base Salary": {"rich_text": [{"text": {"content": "update this field"}}]},
            "LinkedIn Pitch": {"rich_text": [{"text": {"content": "update this field"}}]},
            # Multi-select requires a valid option list
            "Core Craft Keywords": {"multi_select": [{"name": "update this field"}]}
        }
    }
    
    res = requests.post(notion_url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"Successfully added to Notion: {job['title']} ({job['company']})")
    else:
        print(f"FAILED to add to Notion ({res.status_code}): {res.text}")

def main():
    seen_urls = set()
    for query in SEARCH_QUERIES:
        items = search_duckduckgo(query)
        for item in items:
            link = item.get("link", "")
            if link and link not in seen_urls:
                seen_urls.add(link)
                add_to_notion(item)

if __name__ == "__main__":
    main()
