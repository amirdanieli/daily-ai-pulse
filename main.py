import os
import requests
import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup
import time

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
            # Filter for quality (min 20 points)
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

# --- THE CURATOR (Gemini) ---
def summarize_with_gemini(raw_data):
    print("Sending data to Gemini...")
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Try the specific stable version first, fallback to Pro if it fails
    models_to_try = ['gemini-1.5-flash-001', 'gemini-1.5-flash', 'gemini-pro']
    
    model = None
    for model_name in models_to_try:
        try:
            print(f"Attempting to use model: {model_name}")
            model = genai.GenerativeModel(model_name)
            # Test connection with a tiny prompt before sending the big one
            model.generate_content("test") 
            print(f"Success! Connected to {model_name}")
            break
        except Exception as e:
            print(f"Failed to connect to {model_name}: {e}")
            model = None

    if not model:
        # If all fail, list available models to debug
        print("CRITICAL ERROR: Could not connect to any model. Listing available models:")
        for m in genai.list_models():
            print(m.name)
        return "Error: Could not generate briefing. Check logs."

    prompt = f"""
    You are the producer of a technical AI podcast. 
    Here is the raw stream of news from Hacker News and GitHub for {DATE_STR}:
    
    {raw_data}
    
    TASK:
    1. Select the top 5-7 most significant stories/tools. Focus on new open-source tools, model releases, or major research updates.
    2. Write a "Podcast Briefing" script.
    3. Format it clearly with sections: "Top Headlines", "Deep Dive (The #1 Story)", and "Quick Hits".
    4. Keep it concise.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error during generation: {e}"

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