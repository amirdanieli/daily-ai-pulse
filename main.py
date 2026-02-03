import os
import requests
import datetime
import time
from google import genai
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# --- SOURCE 1: HACKER NEWS ---
def get_hn_ai_news():
    print("Fetching Hacker News AI trends...")
    url = "http://hn.algolia.com/api/v1/search_by_date?query=AI+OR+LLM+OR+GPT&tags=story&hitsPerPage=30"
    try:
        response = requests.get(url, timeout=10).json()
        stories = []
        for hit in response['hits']:
            if hit.get('points', 0) > 20: 
                stories.append(f"- [HN] {hit['title']} (Link: {hit.get('url', 'N/A')})")
        return "\n".join(stories[:10]) 
    except Exception as e:
        print(f"Warning: HN fetch failed: {e}")
        return "No Hacker News data available."

# --- SOURCE 2: GITHUB TRENDING ---
def get_github_trending():
    print("Fetching GitHub Trending...")
    url = "https://github.com/trending?since=daily"
    try:
        page = requests.get(url, timeout=10)
        soup = BeautifulSoup(page.text, 'html.parser')
        repos = []
        for row in soup.select('article.Box-row')[:10]:
            repo_name = row.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
            desc = row.select_one('p')
            desc_text = desc.text.strip() if desc else "No description"
            repos.append(f"- [GitHub] {repo_name}: {desc_text}")
        return "\n".join(repos)
    except Exception as e:
        print(f"Warning: GitHub fetch failed: {e}")
        return "No GitHub data available."

# --- THE CURATOR (Gemini 1.5 Flash) ---
def summarize_with_gemini(raw_data):
    print("Initializing Google GenAI Client...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are the producer of a technical AI podcast. 
    Here is the raw stream of news from Hacker News and GitHub for {DATE_STR}:
    
    {raw_data}
    
    TASK:
    1. Select the top 5-7 most significant stories/tools.
    2. Write a "Podcast Briefing" script.
    3. Format it clearly with sections: "Top Headlines", "Deep Dive", and "Quick Hits".
    """
    
    # We strictly use the stable 1.5 model which has better EU availability
    # We add a retry loop for 429 errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt+1} to generate briefing...")
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"Error on attempt {attempt+1}: {error_msg}")
            
            # If it's a quota/rate limit error, wait and retry
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print("Hit rate limit. Waiting 20 seconds...")
                time.sleep(20)
            else:
                # If it's not a rate limit (like 404 or Auth), break immediately
                return f"CRITICAL ERROR: {error_msg}"
    
    return "Failed to generate briefing after multiple attempts."

# --- MAIN EXECUTION ---
def main():
    hn_data = get_hn_ai_news()
    gh_data = get_github_trending()
    
    combined_raw = f"--- HACKER NEWS ---\n{hn_data}\n\n--- GITHUB TRENDING ---\n{gh_data}"
    
    briefing = summarize_with_gemini(combined_raw)
    
    filename = "briefing.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Daily AI Pulse: {DATE_STR}\n\n{briefing}")
    
    print("Briefing generated successfully.")

if __name__ == "__main__":
    main()