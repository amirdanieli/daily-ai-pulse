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
        print(f"Warning: GitHub API failed: {e}. Falling back to scraping...")
        return "No GitHub data available."

# --- THE CURATOR (GenAI SDK with Resilience) ---
def summarize_with_gemini(raw_data):
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found in environment."

    print("Initializing Google GenAI Client...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are the producer of a technical AI podcast. 
    Here is the raw stream of news and tools from Hacker News and GitHub for {DATE_STR}:
    
    {raw_data}
    
    TASK:
    1. Select the top 5-7 most significant stories or repositories.
    2. Write a professional "Podcast Briefing" script.
    3. Use three sections: 
       - 🔥 TOP HEADLINES (The biggest news)
       - 🛠️ TOOL SPOTLIGHT (Focus on a GitHub repo)
       - ⚡ QUICK HITS (Rapid-fire summaries)
    """

    # Retry Logic for 429 (Quota) and 503 (Overloaded)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Using stable gemini-2.0-flash
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "503" in err_msg:
                wait = (attempt + 1) * 20 
                print(f"API busy ({err_msg[:3]}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                return f"Gemini API Error: {err_msg}"
    
    return "Briefing generation failed after multiple retries due to server load."

# --- MAIN EXECUTION ---
def main():
    start_time = time.time()
    
    hn_data = get_hn_ai_news()
    gh_data = get_github_trending()
    
    combined_raw = f"--- HACKER NEWS ---\n{hn_data}\n\n--- GITHUB TRENDING ---\n{gh_data}"
    
    briefing = summarize_with_gemini(combined_raw)
    
    # Save to Markdown for GitHub Action Artifacts/Summary
    filename = "briefing.md"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Daily AI Pulse: {DATE_STR}\n\n{briefing}")
        
        # This allows the briefing to show up directly in the GitHub Action Summary
        if "GITHUB_STEP_SUMMARY" in os.environ:
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary_file:
                summary_file.write(f"\n{briefing}")
                
        print(f"Success! Briefing generated in {round(time.time() - start_time, 2)} seconds.")
    except Exception as e:
        print(f"Failed to write file: {e}")

if __name__ == "__main__":
    main()