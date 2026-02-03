import os
import requests
import datetime
import time
from google import genai
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Ensure your GitHub Action secret is named GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "") # Optional: Add for higher GH API limits
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# --- SOURCE 1: HACKER NEWS (Algolia API) ---
def get_hn_ai_news():
    print("Fetching Hacker News AI trends...")
    url = "http://hn.algolia.com/api/v1/search_by_date?query=AI+OR+LLM+OR+GPT&tags=story&hitsPerPage=30"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        stories = []
        for hit in data.get('hits', []):
            if hit.get('points', 0) > 20: 
                title = hit.get('title')
                link = hit.get('url') or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                stories.append(f"- [HN] {title} ({link})")
        return "\n".join(stories[:12])
    except Exception as e:
        print(f"Warning: HN fetch failed: {e}")
        return "No Hacker News data available."

# --- SOURCE 2: GITHUB TRENDING (API-based approach) ---
def get_github_trending():
    print("Fetching GitHub Trending (AI/ML)...")
    # Using the Search API to find hot AI/ML repos updated in the last 24 hours
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=topic:ai+topic:ml+created:>{yesterday}&sort=stars&order=desc"
    
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        items = response.json().get('items', [])
        repos = []
        for repo in items[:10]:
            name = repo.get('full_name')
            desc = repo.get('description') or "No description provided."
            stars = repo.get('stargazers_count')
            repos.append(f"- [GitHub] {name} ({stars} stars): {desc}")
        return "\n".join(repos)
    except Exception as e:
        print(f"Warning: GitHub API failed: {e}. Falling back to scraping