import os
import requests
from ddgs import DDGS

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Your exact search queries with full operators intact
SEARCH_QUERIES = [
    'site:jobs.ashbyhq.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:boards.greenhouse.io ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:apply.workable.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:jobs.lever.co ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:myworkdayjobs.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid'
]

def search_duckduckgo(query):
    print(f"Searching DuckDuckGo for: {query}")
    job_results = []
    try:
        with DDGS() as ddgs:
            # Using backend='html' forces DuckDuckGo to process complex operators accurately
            results = list(ddgs.text(query, max_results=5, backend='html'))
            print(f"Found {len(results)} results for query.")
            for r in results:
                job_results.append({
                    "title": r.get("title", "Job Posting"),
                    "link": r.get("href", "")
                })
    except Exception as e:
        print(f"Error fetching DuckDuckGo search results: {e}")
    return job_results

def add_to_notion(title, url_link):
    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Job Title": {"title": [{"text": {"content": title}}]},
            "URL": {"url": url_link}
        }
    }
    res = requests.post(notion_url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"Successfully added to Notion: {title}")
    else:
        print(f"FAILED to add to Notion ({res.status_code}): {res.text}")

def main():
    for query in SEARCH_QUERIES:
        items = search_duckduckgo(query)
        for item in items:
            title = item.get("title", "Job Posting")
            link = item.get("link", "")
            if link:
                add_to_notion(title, link)

if __name__ == "__main__":
    main()
