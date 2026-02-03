import os
import requests
import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# --- SOURCE 1: HACKER NEWS (via Algolia API) ---
def get_hn_ai_news():
    print("Fetching Hacker News AI trends...")
    # Search for 'AI', 'LLM', 'GPT' in the last 24 hours
    url = "http://hn.algolia.com/api/v1/search_by_date?query=AI+OR+LLM+OR+GPT&tags=story&hitsPerPage=20"
    try:
        response = requests.get(url).json()
        stories = []
        for hit in response['hits']:
            if hit.get('points', 0) > 50: # Filter for quality (min 50 upvotes)
                stories.append(f"- [HN] {hit['title']} (Link: {hit.get('url', 'N/A')})")
        return "\n".join(stories[:10]) # Top 10
    except Exception as e:
        return f"Error fetching HN: {e}"

# --- SOURCE 2: GITHUB TRENDING (Scraping) ---
def get_github_trending():
    print("Fetching GitHub Trending...")
    url = "https://github.com/trending?since=daily"
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        repos = []
        # GitHub's HTML structure changes occasionally, but this usually works
        for row in soup.select('article.Box-row')[:10]:
            repo_name = row.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
            desc = row.select_one('p')
            desc_text = desc.text.strip() if desc else "No description"
            repos.append(f"- [GitHub] {repo_name}: {desc_text}")
        return "\n".join(repos)
    except Exception as e:
        return f"Error fetching GitHub: {e}"

# --- THE CURATOR (Gemini) ---
def summarize_with_gemini(raw_data):
    print("Sending data to Gemini...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # Free and fast
    
    prompt = f"""
    You are the producer of a technical AI podcast. 
    Here is the raw stream of news from Hacker News and GitHub for {DATE_STR}:
    
    {raw_data}
    
    TASK:
    1. Select the top 5-7 most significant stories/tools. Focus on new open-source tools, model releases, or major research updates. Ignore generic business hype.
    2. Write a "Podcast Briefing" script. It should be written in a way that is easy to read.
    3. Format it clearly with sections: "Top Headlines", "Deep Dive (The #1 Story)", and "Quick Hits".
    4. Keep it concise.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- MAIN EXECUTION ---
def main():
    hn_data = get_hn_ai_news()
    gh_data = get_github_trending()
    
    combined_raw = f"--- HACKER NEWS ---\n{hn_data}\n\n--- GITHUB TRENDING ---\n{gh_data}"
    
    briefing = summarize_with_gemini(combined_raw)
    
    # Save to file
    filename = f"briefing.md" # We overwrite the same file so the URL is constant for Phase 2
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Daily AI Pulse: {DATE_STR}\n\n{briefing}")
    
    print("Briefing generated successfully.")

if __name__ == "__main__":
    main()