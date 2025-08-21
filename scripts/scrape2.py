#!/usr/bin/env python3
"""
Simple web scraper to extract episode links from a website.
Usage: python scrape2.py <url>
"""

import sys
import requests
from bs4 import BeautifulSoup

def scrape_episode_links(url):
    """Fetch HTML from URL and extract all episode links."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all links that point to episode pages
    episode_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("https://shmotime.com/shmotime_episode/"):
            episode_links.append(href)
    
    # Deduplicate while preserving order
    unique_links = list(dict.fromkeys(episode_links))
    
    return unique_links

def main():
    if len(sys.argv) != 2:
        print("Usage: python scrape2.py <url>")
        print("Example: python scrape2.py https://shmotime.com/shows/jedai-council/")
        sys.exit(1)
    
    url = sys.argv[1]
    if not url.startswith("http"):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
    
    print(f"Scraping episode links from: {url}")
    links = scrape_episode_links(url)
    
    if not links:
        print("No episode links found.")
    else:
        print(f"Found {len(links)} episode links:")
        for i, link in enumerate(links, 1):
            print(f"{i:2d}. {link}")

if __name__ == "__main__":
    main()
