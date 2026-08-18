import os
import re
import time
from datetime import date
import requests
import feedparser
from jobspy import scrape_jobs

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

DIRECT_ATS_TARGETS = [
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "zoe"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "kinsta"},
    {"platform": "Ashby", "type": "ashby", "slug": "zoe"},
]

RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
]

def calculate_job_score(title, description=""):
    """
    Strict scoring system ensuring only valid Product/UX Design roles pass.
    """
    title_lower = title.lower()
    text = (title + " " + description).lower()
    score = 0

    # 1. HARD FILTER: Title must explicitly mention a target product/UX design role
    valid_design_roles = [
        "product designer", 
        "ux designer", 
        "ui designer", 
        "product design", 
        "ux/ui designer",
        "lead product designer",
        "senior product designer"
    ]
    
    has_valid_role = any(role in title_lower for role in valid_design_roles)
    if not has_valid_role:
        return -99  # Instant rejection

    # 2. HARD FILTER: Instantly reject if title contains pollution keywords
    pollution_terms = [
        "developer", "engineer", "manager", "strategist", "interior", 
        "revit", "writer", "marketing", "sales", "support", "devops", 
        "data scientist", "frontend", "backend", "full stack", "program manager"
    ]
    if any(term in title_lower for term in pollution_terms):
        return -99

    # Positive scoring for seniority & remote context
    if "senior" in text:
        score += 3
    if "lead" in text:
        score += 4
    if "remote" in text:
        score += 2

    # Disqualifiers for unwanted seniority levels or geo locks
    unwanted_terms = [
        "junior", "mid", "intermediate", "principal", "staff", 
        "director", "head of", "vp", "agency", "consultancy", 
        "contract", "freelance", "us only", "united states only"
    ]
    for term in unwanted_terms:
        if term in text:
            score -= 15

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

def search_jobspy_local():
    """
    Open-source replacement using JobSpy (no API key required).
    """
    print("Fetching jobs via local JobSpy (LinkedIn / Indeed)...")
    jobs = []
    try:
        df_jobs = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term="Senior Product Designer",
            location="Remote",
            results_wanted=20,
            hours_old=48,
            country_indeed='UK'
        )
        
        for _, row in df_jobs.iterrows():
            title = row.get("title", "")
            link = row.get("job_url", "")
            company = row.get("company", "Unknown Company")
            description = row.get("description", "")
            
            score = calculate_job_score(title, str(description))
            if score >= 5 and link:
                print(f" [+] JobSpy Passed (Score {score}): {title} at {company}")
                jobs.append({
                    "title": title,
                    "link": link,
                    "company": company,
                    "platform": "LinkedIn / JobSpy"
                })
    except Exception as e:
        print(f"JobSpy execution failed: {e}")
    return jobs

def fetch_direct_ats_jobs():
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
                        if score >= 5 and link:
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
                        if score >= 5 and link:
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
                if score >= 5 and link:
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

    all_new_jobs.extend(search_jobspy_local())
    all_new_jobs.extend(fetch_direct_ats_jobs())
    all_new_jobs.extend(parse_rss_feeds())

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
