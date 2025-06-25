#!/usr/bin/env python3
"""
Working ComplaintsBoard scraper that uses requests + BeautifulSoup instead of Selenium
This avoids ChromeDriver compatibility issues on Windows
"""

import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random

def scrape_complaintsboard_working(keyword, max_pages=3):
    """
    Scrape ComplaintsBoard using requests and BeautifulSoup
    Extracts real complaint data from the HTML structure shown
    """
    print(f"🔍 Scraping ComplaintsBoard for: {keyword}")
    
    results = []
    seen_urls = set()
    
    # Search URL
    search_url = f"https://www.complaintsboard.com/?search={quote_plus(keyword)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}&page={page}"
            
            print(f"📄 Scraping page {page}: {url}")
            
            # Add delay to be respectful
            if page > 1:
                time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find complaint items using the structure you showed
            complaint_items = soup.find_all('div', class_='search__item')
            
            if not complaint_items:
                print(f"❌ No complaint items found on page {page}")
                break
            
            print(f"✅ Found {len(complaint_items)} complaint items on page {page}")
            
            for item in complaint_items:
                try:
                    # Extract the link
                    link_elem = item.find('a', class_='search__item-link')
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    if not href:
                        continue
                    
                    # Build full URL
                    full_url = urljoin('https://www.complaintsboard.com', href)
                    
                    # Skip if we've seen this URL
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    # Extract title
                    title_elem = item.find('span', class_='search__item-title')
                    title = ""
                    if title_elem:
                        # Remove the highlight spans and get clean text
                        for highlight in title_elem.find_all('span', class_='highlight'):
                            highlight.unwrap()
                        title = title_elem.get_text(strip=True)
                    
                    # Extract complaint text
                    text_elem = item.find('span', class_='search__item-text')
                    complaint_text = ""
                    if text_elem:
                        # Remove the highlight spans and get clean text
                        for highlight in text_elem.find_all('span', class_='highlight'):
                            highlight.unwrap()
                        complaint_text = text_elem.get_text(strip=True)
                    
                    # Extract badge (Complaint, Review, etc.)
                    badge_elem = item.find('span', class_='search__item-badge')
                    badge = ""
                    if badge_elem:
                        badge = badge_elem.get_text(strip=True)
                    
                    # Only add if we have meaningful content
                    if title and complaint_text:
                        result = {
                            "title": title,
                            "url": full_url,
                            "text": complaint_text,
                            "badge": badge,
                            "keyword": keyword
                        }
                        results.append(result)
                        print(f"  📝 Added: {title[:50]}...")
                
                except Exception as e:
                    print(f"  ❌ Error processing item: {e}")
                    continue
            
            # Check if there are more pages
            next_page = soup.find('a', string=re.compile(r'Next|next', re.I))
            if not next_page and page < max_pages:
                print(f"📄 No next page found, stopping at page {page}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error on page {page}: {e}")
            break
        except Exception as e:
            print(f"❌ Error scraping page {page}: {e}")
            break
    
    print(f"🎉 Scraping complete! Found {len(results)} complaints")
    return results

def test_scraper():
    """Test the scraper with a sample keyword"""
    print("🧪 Testing ComplaintsBoard Scraper")
    print("=" * 50)
    
    test_keywords = ["salesforce", "customer service", "software bugs"]
    
    for keyword in test_keywords:
        print(f"\n📝 Testing: {keyword}")
        results = scrape_complaintsboard_working(keyword, max_pages=2)
        
        print(f"📊 Results: {len(results)}")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result['title']}")
            print(f"     Text: {result['text'][:100]}...")
            print(f"     URL: {result['url']}")
            print(f"     Badge: {result['badge']}")
            print()

if __name__ == "__main__":
    test_scraper() 