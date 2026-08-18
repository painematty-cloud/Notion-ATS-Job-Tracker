import os
import re
import time
from datetime import date
import requests
import feedparser

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Target company slugs for direct JSON ATS queries (Greenhouse & Ashby)
DIRECT_ATS_TARGETS = [
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "zoe"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "kinsta"},
    {"platform": "Ashby", "type": "ashby", "slug": "zoe"},
]

# Curated RSS feeds for remote design jobs
RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
]

def calculate_job_score(title, description=""):
    """
    Weighted scoring system to determine job quality and relevance.
    Positive weights for target roles/seniority, heavy penalties for unwanted terms.
    """
    text = (title + " " + description).lower()
    score = 0

    # Positive scoring
    if "senior" in text:
        score += 3
    if "lead" in text:
        score += 4
    if "product designer" in text:
        score += 4
    if "ux designer" in text:
        score += 3
    if "remote" in text:
        score += 2

    # Negative scoring / hard disqualifiers
    unwanted_terms = [
        "junior", "mid", "intermediate", "principal", "staff", 
        "director", "head of", "vp", "agency", "consultancy", 
        "contract", "freelance", "ui/ux", "us only", "united states only"
    ]
    
    for term in unwanted_terms:
        if term in text:
            score -= 10

    return score

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

def search_jsearch_api():
    """
    Suggestion 1: Integrate JSearch API (RapidAPI) for LinkedIn & Global Boards
    """
    if not RAPIDAPI_KEY:
        print("RAPIDAPI_KEY not set. Skipping JSearch API search.")
        return []

    print("Fetching jobs via JSearch API (LinkedIn / Indeed)...")
    url = "https://jsearch.p.rapidapi.com/search"
    querystring = {
        "query": "Senior Product Designer OR UX Designer Remote Spain OR UK OR Germany OR Netherlands OR France OR Portugal OR Ireland",
        "page": "1",
        "num_pages": "1",
        "date_posted": "week"
    }
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            for item in data.get("data", []):
                title = item.get("job_title", "")
                link = item.get("job_apply_link", item.get("job_google_link", ""))
                company = item.get("employer_name", "Unknown Company")
                description = item.get("job_description", "")
                
                score = calculate_job_score(title, description)
                if score >= 6 and link:
                    print(f" [+] JSearch Passed (Score {score}): {title} at {company}")
                    jobs.append({
                        "title": title,
                        "link": link,
                        "company": company,
                        "platform": "LinkedIn / JSearch"
                    })
            return jobs
        else:
            print(f"JSearch API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"JSearch API request failed: {e}")
    return []

def fetch_direct_ats_jobs():
    """
    Suggestion 2: Query Direct ATS JSON Endpoints (Greenhouse & Ashby)
    """
    print("Fetching jobs via Direct ATS JSON APIs...")
    jobs = []
    for target in DIRECT_ATS_TARGETS:
        slug = target["slug"]
        platform_type = target["type"]
        
        try:
            if platform_type == "greenhouse":
                endpoint = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
                res = requests.get(endpoint, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for job in data.get("jobs", []):
                        title = job.get("title", "")
                        link = job.get("absolute_url", "")
                        location = job.get("location", {}).get("name", "")
                        
                        score = calculate_job_score(title, location)
                        if score >= 6 and link:
                            print(f" [+] Greenhouse Direct Passed: {title} ({slug})")
                            jobs.append({
                                "title": f"{title} at {slug.capitalize()}",
                                "link": link,
                                "company": slug.capitalize(),
                                "platform": "Greenhouse"
                            })
            elif platform_type == "ashby":
                endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                res = requests.get(endpoint, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for job in data.get("jobs", []):
                        title = job.get("title", "")
                        link = job.get("jobUrl", "")
                        location = job.get("location", "")
                        
                        score = calculate_job_score(title, str(location))
                        if score >= 6 and link:
                            print(f" [+] Ashby Direct Passed: {title} ({slug})")
                            jobs.append({
                                "title": f"{title} at {slug.capitalize()}",
                                "link": link,
                                "company": slug.capitalize(),
                                "platform": "Ashby"
                            })
        except Exception as e:
            print(f"Failed to fetch ATS for {slug}: {e}")
    return jobs

def parse_rss_feeds():
    """
    Suggestion 4: Direct RSS Feed Parsing for Curated Design Boards
    """
    print("Parsing curated design RSS feeds...")
    jobs = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                
                score = calculate_job_score(title, summary)
                if score >= 6 and link:
                    print(f" [+] RSS Feed Passed (Score {score}): {title}")
                    jobs.append({
                        "title": title,
                        "link": link,
                        "company": "External RSS Board",
                        "platform": "Other"
                    })
        except Exception as e:
            print(f"Failed to parse RSS feed {feed_url}: {e}")
    return jobs

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
    if res.status_code in [200, 201]:
        print(f"Successfully added to Notion: {job['title']} ({job['company']})")
    else:
        print(f"FAILED to add to Notion ({res.status_code}): {res.text}")

def main():
    seen_urls = get_existing_notion_urls()
    all_new_jobs = []

    # 1. Fetch via JSearch API (LinkedIn / Job Aggregators)
    all_new_jobs.extend(search_jsearch_api())

    # 2. Fetch directly from known ATS JSON endpoints
    all_new_jobs.extend(fetch_direct_ats_jobs())

    # 3. Parse curated design RSS feeds
    all_new_jobs.extend(parse_rss_feeds())

    # Deduplicate and push to Notion using weighted score vetting
    for job in all_new_jobs:
        link = job.get("link", "")
        if link and link not in seen_urls:
            seen_urls.add(link)
            add_to_notion(job)
            time.sleep(1)
        else:
            print(f" [!] DUPLICATE SKIPPED: {link}")

if __name__ == "__main__":
    main()
