import os
import time
from datetime import date
import requests
import feedparser

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 100 Unique External RSS Feeds grouped appropriately by job board platform
RSS_FEEDS_BY_PLATFORM = {
    "We Work Remotely": [
        "https://weworkremotely.com/categories/remote-design-jobs.rss",
        "https://weworkremotely.com/categories/remote-product-jobs.rss",
        "https://weworkremotely.com/remote-jobs.rss",
        "https://weworkremotely.com/categories/all-other-remote-jobs.rss",
        "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-sales-and-marketing-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"
    ],
    "Remotive": [
        "https://remotive.com/remote-jobs/design/feed",
        "https://remotive.com/remote-jobs/product/feed",
        "https://remotive.com/remote-jobs/feed",
        "https://remotive.com/remote-jobs/software-dev/feed",
        "https://remotive.com/remote-jobs/customer-support/feed",
        "https://remotive.com/remote-jobs/marketing/feed",
        "https://remotive.com/remote-jobs/sales/feed",
        "https://remotive.com/remote-jobs/data/feed",
        "https://remotive.com/remote-jobs/hr/feed",
        "https://remotive.com/remote-jobs/qa/feed",
        "https://remotive.com/remote-jobs/writing/feed",
        "https://remotive.com/remote-jobs/finance-legal/feed",
        "https://remotive.com/remote-jobs/project-management/feed"
    ],
    "Jobicy": [
        "https://jobicy.com/feed/?job_categories=design",
        "https://jobicy.com/feed/?job_categories=product",
        "https://jobicy.com/feed/?job_categories=managers",
        "https://jobicy.com/feed/",
        "https://jobicy.com/feed/?job_categories=developers",
        "https://jobicy.com/feed/?job_categories=marketing",
        "https://jobicy.com/feed/?job_categories=support",
        "https://jobicy.com/feed/?job_categories=copywriting",
        "https://jobicy.com/feed/?job_categories=sme",
        "https://jobicy.com/feed/?job_categories=hr",
        "https://jobicy.com/feed/?job_categories=finance",
        "https://jobicy.com/feed/?job_categories=admin",
        "https://jobicy.com/feed/?job_categories=seo",
        "https://jobicy.com/feed/?job_categories=sales"
    ],
    "Real Work From Anywhere": [
        "https://www.realworkfromanywhere.com/remote-design-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-product-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/rss.xml",
        "https://www.realworkfromanywhere.com/remote-management-and-finance-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-software-developer-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-fullstack-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-frontend-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-backend-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-devops-and-sysadmin-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-customer-support-jobs/rss.xml",
        "https://www.realworkfromanywhere.com/remote-sales-and-marketing-jobs/rss.xml"
    ],
    "Working Nomads": [
        "https://www.workingnomads.com/jobs/rss/design",
        "https://www.workingnomads.com/jobs/rss/management",
        "https://www.workingnomads.com/jobs/rss/all",
        "https://www.workingnomads.com/jobs/rss/development",
        "https://www.workingnomads.com/jobs/rss/sysadmin",
        "https://www.workingnomads.com/jobs/rss/consulting",
        "https://www.workingnomads.com/jobs/rss/sales",
        "https://www.workingnomads.com/jobs/rss/marketing",
        "https://www.workingnomads.com/jobs/rss/finance",
        "https://www.workingnomads.com/jobs/rss/customer-support",
        "https://www.workingnomads.com/jobs/rss/writing",
        "https://www.workingnomads.com/jobs/rss/qa",
        "https://www.workingnomads.com/jobs/rss/hr",
        "https://www.workingnomads.com/jobs/rss/legal"
    ],
    "RemoteOK & JobsCollider": [
        "https://remoteok.com/remote-design-jobs.rss",
        "https://remoteok.com/rss",
        "https://jobscollider.com/remote-jobs.rss",
        "https://remoteok.com/remote-dev-jobs.rss",
        "https://remoteok.com/remote-exec-jobs.rss",
        "https://remoteok.com/remote-marketing-jobs.rss",
        "https://remoteok.com/remote-support-jobs.rss",
        "https://remoteok.com/remote-writing-jobs.rss",
        "https://remoteok.com/remote-sales-jobs.rss",
        "https://remoteok.com/remote-finance-jobs.rss",
        "https://remoteok.com/remote-product-jobs.rss"
    ],
    "Remote First Jobs & Global Feeds": [
        "https://www.skipthedrive.com/feed/",
        "https://remotefirstjobs.com/rss/jobs/engineering.rss",
        "https://remotefirstjobs.com/rss/jobs/development.rss",
        "https://remotefirstjobs.com/rss/jobs/frontend.rss",
        "https://remotefirstjobs.com/rss/jobs/backend.rss",
        "https://remotefirstjobs.com/rss/jobs/fullstack.rss",
        "https://remotefirstjobs.com/rss/jobs/mobile.rss",
        "https://remotefirstjobs.com/rss/jobs/ios.rss",
        "https://remotefirstjobs.com/rss/jobs/android.rss",
        "https://remotefirstjobs.com/rss/jobs/data-science.rss",
        "https://remotefirstjobs.com/rss/jobs/machine-learning.rss",
        "https://remotefirstjobs.com/rss/jobs/cybersecurity.rss",
        "https://remotefirstjobs.com/rss/jobs/qa.rss",
        "https://remotefirstjobs.com/rss/jobs/sysadmin.rss",
        "https://remotefirstjobs.com/rss/jobs/cloud.rss",
        "https://remotefirstjobs.com/rss/jobs/sales.rss",
        "https://remotefirstjobs.com/rss/jobs/marketing.rss",
        "https://remotefirstjobs.com/rss/jobs/content.rss",
        "https://remotefirstjobs.com/rss/jobs/copywriting.rss",
        "https://remotefirstjobs.com/rss/jobs/support.rss",
        "https://remotefirstjobs.com/rss/jobs/success.rss",
        "https://remotefirstjobs.com/rss/jobs/operations.rss",
        "https://remotefirstjobs.com/rss/jobs/finance.rss",
        "https://remotefirstjobs.com/rss/jobs/legal.rss",
        "https://remotefirstjobs.com/rss/jobs/hr.rss",
        "https://remotefirstjobs.com/rss/jobs/recruiting.rss",
        "https://remotefirstjobs.com/rss/jobs/community.rss",
        "https://remotefirstjobs.com/rss/jobs/communications.rss",
        "https://remotefirstjobs.com/rss/jobs/pr.rss",
        "https://remotefirstjobs.com/rss/jobs/education.rss",
        "https://remotefirstjobs.com/rss/jobs/health.rss",
        "https://remotefirstjobs.com/rss/jobs/crypto.rss",
        "https://remotefirstjobs.com/rss/jobs/blockchain.rss",
        "https://remotefirstjobs.com/rss/jobs/web3.rss",
        "https://remotefirstjobs.com/rss/jobs/gaming.rss",
        "https://remotefirstjobs.com/rss/jobs/ecommerce.rss",
        "https://remotefirstjobs.com/rss/jobs/saas.rss",
        "https://remotefirstjobs.com/rss/jobs/b2b.rss"
    ]
}

def calculate_job_score(title, description=""):
    """
    Strict scoring system with strong preference for UK & EMEA regions, 
    and heavy penalties for US-only constraints.
    """
    title_lower = title.lower()
    text = (title + " " + description).lower()
    score = 0

    # 1. ABSOLUTE HARD FILTER: Title MUST contain a target design role
    allowed_roles = [
        "product designer", 
        "ux designer", 
        "ui designer", 
        "product design", 
        "ux/ui designer"
    ]
    if not any(role in title_lower for role in allowed_roles):
        return -99

    # 2. ABSOLUTE HARD FILTER: Instant kill for non-design roles
    pollution_terms = [
        "developer", "engineer", "manager", "strategist", "interior", 
        "revit", "writer", "marketing", "sales", "support", "devops", 
        "data", "frontend", "backend", "full stack", "program", "delivery", 
        "risk", "architect", "analyst", "qa", "test", "security", "brand", "graphic"
    ]
    if any(term in title_lower for term in pollution_terms):
        return -99

    # 3. GEOGRAPHIC FILTER & WEIGHTING
    us_only_terms = ["us only", "united states only", "usa only", "us-only", "americas only"]
    if any(term in text for term in us_only_terms):
        return -99  # Discard if restricted strictly to the US

    emea_uk_terms = [
        "uk", "united kingdom", "london", "europe", "emea", "spain", 
        "espana", "germany", "berlin", "netherlands", "amsterdam", 
        "france", "paris", "portugal", "lisbon", "ireland", "dublin", 
        "eu timezones", "european timezone"
    ]
    
    has_emea_uk = any(term in text for term in emea_uk_terms)
    if has_emea_uk:
        score += 6  # Heavy bonus for UK/EMEA alignment
    else:
        score -= 3  # Minor penalty if location is completely ambiguous or non-specified

    # Seniority & Remote scoring weights
    if "senior" in text:
        score += 3
    if "lead" in text:
        score += 4
    if "remote" in text:
        score += 2

    # Negative modifiers for seniority levels or contract restrictions
    unwanted_terms = [
        "junior", "mid", "intermediate", "principal", "staff", 
        "director", "head of", "vp", "agency", "consultancy", 
        "contract", "freelance"
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

def parse_rss_feeds():
    total_feeds = sum(len(feeds) for feeds in RSS_FEEDS_BY_PLATFORM.values())
    print(f"Parsing {total_feeds} grouped RSS feeds with UK/EMEA prioritization...")
    jobs = []
    
    for platform_name, feed_list in RSS_FEEDS_BY_PLATFORM.items():
        print(f"--- Querying Group: {platform_name} ({len(feed_list)} feeds) ---")
        for feed_url in feed_list:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = entry.get("summary", "")
                    
                    score = calculate_job_score(title, summary)
                    if score >= 5 and link:
                        print(f" [+] [{platform_name}] Matched (Score {score}): {title}")
                        jobs.append({
                            "title": title,
                            "link": link,
                            "company": f"RSS ({platform_name})",
                            "platform": "Other"
                        })
            except Exception as e:
                pass
            time.sleep(0.05)
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
    all_new_jobs = parse_rss_feeds()

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
