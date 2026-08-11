import os
import re
import time
from datetime import datetime, date
import requests
from ddgs import DDGS

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

SEARCH_QUERIES = [
    'site:jobs.ashbyhq.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "UK" OR "EU" OR "EMEA") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux" -"US" -"USA" -"United States" -"North America" -"APAC" -"LATAM"',
    'site:boards.greenhouse.io ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "UK" OR "EU" OR "EMEA") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux" -"US" -"USA" -"United States" -"North America" -"APAC" -"LATAM"',
    'site:apply.workable.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "UK" OR "EU" OR "EMEA") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux" -"US" -"USA" -"United States" -"North America" -"APAC" -"LATAM"',
    'site:jobs.lever.co ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "UK" OR "EU" OR "EMEA") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux" -"US" -"USA" -"United States" -"North America" -"APAC" -"LATAM"',
    'site:myworkdayjobs.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "UK" OR "EU" OR "EMEA") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux" -"US" -"USA" -"United States" -"North America" -"APAC" -"LATAM"'
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

def title_passes_criteria(title, snippet):
    title_lower = title.lower()
    
    # Exclude unwanted seniority levels explicitly from the title
    unwanted_levels = ["junior", "mid", "intermediate", "principal", "staff", "director", "head of", "vp"]
    if any(level in title_lower for level in unwanted_levels):
        return False
        
    # Ensure target seniority exists (Senior or Lead)
    has_target_seniority = any(lvl in title_lower for lvl in ["senior", "lead"])
    if not has_target_seniority:
        return False
        
    # Ensure target role exists (Product Designer or UX Designer)
    has_target_role = any(role in title_lower for role in ["product designer", "ux designer"])
    if not has_target_role:
        return False
        
    # Exclude UI/UX starting or focused roles
    if "ui/ux" in title_lower or title_lower.startswith("ui/ux"):
        return False
        
    # Relaxed location criteria check (only filter out hard locks if explicitly stated in title)
    combined_text = (title + " " + snippet).lower()
    hard_unwanted_locations = ["us only", "united states only", "usa only"]
    if any(loc in combined_text for loc in hard_unwanted_locations):
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
    """Searches with built-in retry logic and safe backend handling."""
    for attempt in range(retries):
        try:
            print(f"Searching for query (Attempt {attempt + 1}): {query}")
            job_results = []
            with DDGS() as ddgs:
                # Removed explicit html backend which can drop results depending on package version
                results = list(ddgs.text(query, max_results=10))
                print(f"Found {len(results)} raw results for query.")
                for r in results:
                    title = r.get("title", "Job Posting")
                    link = r.get("href", "")
                    snippet = r.get("body", "")
                    if link:
                        if title_passes_criteria(title, snippet):
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
                time.sleep(5)
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
    # Notion API returns 201 Created on successful page creation
    if res.status_code in [200, 201]:
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
         
        time.sleep(3)

if __name__ == "__main__":
    main()
