import os
import re
import time
from datetime import date
import requests
import feedparser

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Expanded list of 20 ATS systems and top tech companies
DIRECT_ATS_TARGETS = [
    # 1. Greenhouse
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "zoe"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "kinsta"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "canonical"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "gitlab"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "buffer"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "zapier"},
    # 2. Ashby
    {"platform": "Ashby", "type": "ashby", "slug": "zoe"},
    {"platform": "Ashby", "type": "ashby", "slug": "linear"},
    {"platform": "Ashby", "type": "ashby", "slug": "notion"},
    {"platform": "Ashby", "type": "ashby", "slug": "figma"},
    # 3. Lever (via Public Board API structure where applicable)
    {"platform": "Lever", "type": "lever", "slug": "netflix"},
    {"platform": "Lever", "type": "lever", "slug": "getyourguide"},
    # 4. Workable
    {"platform": "Workable", "type": "workable", "slug": "revolut"},
    # 5. Teamtailor
    {"platform": "Teamtailor", "type": "teamtailor", "slug": "coolblue"},
    # 6. Recruitee
    {"platform": "Recruitee", "type": "recruitee", "slug": "quadcode"},
    # 7. Personio
    {"platform": "Personio", "type": "personio", "slug": "personio"},
    # 8. SmartRecruiters
    {"platform": "SmartRecruiters", "type": "smartrecruiters", "slug": "visa"},
    # 9. Pinpoint
    {"platform": "Pinpoint", "type": "pinpoint", "slug": "transfergo"},
    # 10. Breezy HR
    {"platform": "Breezy", "type": "breezy", "slug": "sift"},
    # 11-20 Additional enterprise/scaleup targets across global ATS boards
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "coinbase"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "stripe"},
    {"platform": "Ashby", "type": "ashby", "slug": "ripling"},
    {"platform": "Ashby", "type": "ashby", "slug": "deel"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "airbnb"},
    {"platform": "Ashby", "type": "ashby", "slug": "vanta"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "spotify"},
    {"platform": "Ashby", "type": "ashby", "slug": "retool"},
    {"platform": "Greenhouse", "type": "greenhouse", "slug": "reddit"},
    {"platform": "Ashby", "type": "ashby", "slug": "webflow"}
]

RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
]

def calculate_job_score(title, description=""):
    """
    Absolute strict filter: Rejects anything that isn't cleanly a Product or UX design role.
    """
    title_lower = title.lower()
    text = (title + " " + description).lower()
    score = 0

    # 1. ABSOLUTE HARD FILTER: Title MUST contain one of these exact design phrases
    allowed_roles = [
        "product designer", 
        "ux designer", 
        "ui designer", 
        "product design", 
        "ux/ui designer"
    ]
    if not any(role in title_lower for role in allowed_roles):
        return -99  # Instant rejection

    # 2. ABSOLUTE HARD FILTER: Instant kill if title contains any non-design terms
    pollution_terms = [
        "developer", "engineer", "manager", "strategist", "interior", 
        "revit", "writer", "marketing", "sales", "support", "devops", 
        "data", "frontend", "backend", "full stack", "program", "delivery", 
        "risk", "architect", "analyst", "qa", "test", "security", "brand", "graphic"
    ]
    if any(term in title_lower for term in pollution_terms):
        return -99

    # Scoring weights
    if "senior" in text:
        score += 3
    if "lead" in text:
        score += 4
    if "remote" in text:
        score += 2

    # Negative modifiers
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

def fetch_direct_ats_jobs():
    print("Fetching jobs via Direct ATS JSON APIs...")
    jobs = []
    for target in DIRECT_ATS_TARGETS:
        slug = target["slug"]
        platform_type = target["type"]
        platform_name = target["platform"]
        
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
                            print(f" [+] Greenhouse Passed: {title} ({slug})")
                            jobs.append({
                                "title": f"{title} at {slug.capitalize()}",
                                "link": link,
                                "company": slug.capitalize(),
                                "platform": platform_name
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
                            print(f" [+] Ashby Passed: {title} ({slug})")
                            jobs.append({
                                "title": f"{title} at {slug.capitalize()}",
                                "link": link,
                                "company": slug.capitalize(),
                                "platform": platform_name
                            })
            elif platform_type == "lever":
                endpoint = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                res = requests.get(endpoint, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for job in data:
                        title = job.get("text", "")
                        link = job.get("hostedUrl", "")
                        categories = job.get("categories", {})
                        location = categories.get("location", "")
                        
                        score = calculate_job_score(title, str(location))
                        if score >= 5 and link:
                            print(f" [+] Lever Passed: {title} ({slug})")
                            jobs.append({
                                "title": f"{title} at {slug.capitalize()}",
                                "link": link,
                                "company": slug.capitalize(),
                                "platform": platform_name
                            })
        except Exception as e:
            print(f"Failed to fetch ATS for {slug} ({platform_type}): {e}")
        time.sleep(0.5)
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
