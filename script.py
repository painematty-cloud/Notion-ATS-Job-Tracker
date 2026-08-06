import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

SEARCH_QUERIES = [
    'site:jobs.ashbyhq.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:boards.greenhouse.io ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:apply.workable.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:jobs.lever.co ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid',
    'site:myworkdayjobs.com ("Senior" OR "Lead" OR "Principal" OR "Staff") ("Product Designer" OR "UX Designer" OR "UX/UI Designer") ("Remote" OR "UK" OR "EU") -agency -consultancy -contract -freelance -junior -mid'
]

def search_google(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Error fetching Google Search results: {response.text}")
    return []

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
        print(f"Added to Notion: {title}")
    else:
        print(f"Failed to add to Notion ({res.status_code}): {res.text}")

def main():
    for query in SEARCH_QUERIES:
        items = search_google(query)
        for item in items:
            title = item.get("title", "Job Posting")
            link = item.get("link", "")
            if link:
                add_to_notion(title, link)

if __name__ == "__main__":
    main()
