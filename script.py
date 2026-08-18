import os
import re
import time
from datetime import datetime, date
import requests
from ddgs import DDGS

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

SEARCH_QUERIES = [
    # 1. Greenhouse (EU Hosted Instance) - Balanced across Spain and key EU tech hubs
    'site:job-boards.eu.greenhouse.io ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 2. Lever (EU Hosted Instance)
    'site:jobs.eu.lever.co ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 3. Ashby
    'site:jobs.ashbyhq.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 4. Greenhouse (Global Base)
    'site:boards.greenhouse.io ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 5. Workable
    'site:apply.workable.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 6. Lever (Global Base)
    'site:jobs.lever.co ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 7. Teamtailor
    'site:teamtailor.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 8. Recruitee
    'site:recruitee.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 9. Personio
    'site:personio.com/job ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 10. Breezy HR
    'site:breezy.hr ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 11. Workday
    'site:myworkdayjobs.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 12. SmartRecruiters
    'site:jobs.smartrecruiters.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France" OR "Portugal" OR "Ireland") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 13. BambooHR
    'site:bamboohr.com/careers ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 14. Homerun
    'site:homerun.co ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 15. Factorial
    'site:factorialhr.com ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"',
    # 16. Pinpoint
    'site:pinpoint.hr ("Senior" OR "Lead") ("Product Designer" OR "UX Designer") ("Remote" OR "Spain" OR "España" OR "UK" OR "Germany" OR "Netherlands" OR "France") -agency -consultancy -contract -freelance -junior -mid -"principal" -"staff" -"director" -"ui/ux"'
]

def detect_ats_platform(url):
    if "job-boards.eu.greenhouse.io" in url:
        return "Greenhouse EU"
    elif "jobs.eu.lever.co" in url:
        return "Lever EU"
    elif "ashbyhq.com" in url:
        return "Ashby"
    elif "greenhouse.io" in url:
        return "Greenhouse"
    elif "workable.com" in url:
        return "Workable"
    elif "lever.co" in url:
        return "Lever"
    elif "teamtailor.com" in url:
        return "Teamtailor"
    elif "recruitee.com" in url:
        return "Recruitee"
    elif "personio.com" in url:
        return "Personio"
    elif "breezy.hr" in url:
        return "Breezy"
    elif "myworkdayjobs.com" in url:
        return "Workday"
    elif "smartrecruiters.com" in url:
        return "SmartRecruiters"
    elif "bamboohr.com" in url:
        return "BambooHR"
    elif "homerun.co" in url:
        return "Homerun"
    elif "factorialhr.com" in url:
        return "Factorial"
    elif "pinpoint.hr" in url:
        return "Pinpoint"
    return "Other"

def extract_company_name(title, url):
    if " at " in title:
        parts = title.split(" at ")
        if len(parts) > 1:
            return parts[-1].split(" - ")[0].strip()
     
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        domain = match.group(1)
        parts = url.split('/')
        ats_domains = [
            "greenhouse.io", "eu.greenhouse.io", "ashbyhq.com", "lever.co", "eu.lever.co", "workable.com", 
            "teamtailor.com", "recruitee.com", "personio.com", "breezy.hr", 
            "smartrecruiters.com", "bamboohr.com", "homerun.co", "factorialhr.com", "pinpoint.hr"
        ]
        if any(ats in domain for ats in ats_domains) and len(parts) > 3 and parts[3]:
            return parts[3].replace("-", " ").title()
            
    return "Unknown Company"

def title_passes_criteria(title, snippet):
    title_lower = title.lower()
    
    unwanted_levels = ["junior", "mid", "intermediate", "principal", "staff", "director", "head of", "vp"]
    if any(level in title_lower for level in unwanted_levels):
        return False
        
    has_target_seniority = any(lvl in title_lower for lvl in ["senior", "lead"])
    if not has_target_seniority:
        return False
        
    has_target_role = any(role in title_lower for role in ["product designer", "ux designer"])
    if not has_target_role:
        return False
        
    if "ui/ux" in title_lower or title_lower.startswith("ui/ux"):
        return False
        
    combined_text = (title + " " + snippet).lower()
    hard_unwanted_locations = ["us only", "united states only", "usa only", "us-only"]
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
    for attempt in range(retries):
        try:
            print(f"Searching for query (Attempt {attempt + 1}): {query}")
            job_results = []
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=30))
                print(f"Found {len(results)} raw results for query.")
                for r in results:
                    title = r.get("title", "Job Posting")
                    link = r.get("href", "")
                    snippet = r.get("body", "")
                    
                    # Guard against non-job results creeping in via generic keywords
                    if any(bad in title.lower() for bad in ["wikipedia", "dictionary", "senior center", "apartments", "meaning"]):
                        continue
                        
                    if link:
                        if title_passes_criteria(title, snippet):
                            print(f" [+] PASSED FILTER: {title} | {link}")
                            job_results.append({
                                "title": title,
                                "link": link,
                                "company": extract_company_name(title, link),
                                "platform": detect_ats_platform(link)
                            })
                        else:
                            print(f" [x] FILTERED OUT: {title}")
            return job_results
        except Exception as e:
            print(f"Attempt {attempt + 1} failed due to error/timeout: {e}")
            if attempt < retries - 1:
                sleep_time = (attempt + 1) * 10
                print(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print("All retries failed for this query due to timeouts. Skipping gracefully.")
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
            else:
                print(f" [!] DUPLICATE SKIPPED (Already in Notion): {link}")
         
        time.sleep(5)

if __name__ == "__main__":
    main()

