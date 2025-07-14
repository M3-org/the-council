# pip install beautifulsoup4 requests
import sys
import requests
from bs4 import BeautifulSoup

if len(sys.argv) < 2 or not sys.argv[1].startswith('http'):
    print('Usage: python scrape.py <url>')
    sys.exit(1)

url = sys.argv[1]
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers)
resp.raise_for_status()
html = resp.text

soup = BeautifulSoup(html, "html.parser")
links = []
for a in soup.find_all("a", href=True):
    href = a['href']
    if href.startswith("https://shmotime.com/shmotime_episode/"):
        links.append(href)

# Deduplicate while preserving order
unique_links = list(dict.fromkeys(links))

for link in unique_links:
    print(link)
