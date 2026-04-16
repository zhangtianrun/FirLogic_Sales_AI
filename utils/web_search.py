import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def find_website_url(company_name):
    """Search for the official website URL of the company."""
    print(f"    [*] Searching DuckDuckGo for: {company_name}")
    try:
        time.sleep(1) # rate limiting protection
        results = DDGS().text(f"{company_name} official website sawmill wood processing", max_results=5)
        for r in results:
            url = r.get("href")
            if url and not any(x in url for x in ["facebook.com", "linkedin.com", "yellowpages", "zoominfo.com", "bloomberg.com", "wikipedia.org", "dnb.com", "manta.com"]):
                return url
        return None
    except Exception as e:
        print(f"    [!] Error searching DDG for {company_name}: {e}")
        return None

def scrape_website_text(url):
    """Fetch URL and return clean text, with a strict timeout."""
    if not url: return "No URL found."
    print(f"    [*] Scraping content from: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:15000] # Cap text length to avoid token limits
    except Exception as e:
        print(f"    [!] Error scraping {url}: {e}")
        return f"Scraping failed: {e}"
