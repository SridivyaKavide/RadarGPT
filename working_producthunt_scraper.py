#!/usr/bin/env python3
"""
Working Product Hunt scraper that uses requests + BeautifulSoup
"""

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import json

def scrape_producthunt_working(keyword, max_pages=3):
    """Scrape Product Hunt using requests and BeautifulSoup, targeting real product data from embedded JSON."""
    print(f"🔍 Scraping Product Hunt for: {keyword}")
    
    results = []
    seen_urls = set()
    
    # Search URL
    search_url = f"https://www.producthunt.com/search?q={quote_plus(keyword)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"📄 Scraping: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- NEW: Try to extract from embedded __NEXT_DATA__ JSON ---
        next_data = soup.find('script', id='__NEXT_DATA__', type='application/json')
        if next_data:
            try:
                data = json.loads(next_data.string)
                # Traverse the JSON to find product search results
                # This structure may change, but usually it's in data['props']['pageProps']['posts']
                posts = None
                # Try common paths
                if (
                    'props' in data and
                    'pageProps' in data['props'] and
                    'posts' in data['props']['pageProps']
                ):
                    posts = data['props']['pageProps']['posts']
                elif (
                    'props' in data and
                    'pageProps' in data['props'] and
                    'searchResults' in data['props']['pageProps']
                ):
                    posts = data['props']['pageProps']['searchResults']
                if posts:
                    print(f"✅ Found {len(posts)} products in __NEXT_DATA__ JSON")
                    for post in posts:
                        try:
                            name = post.get('name') or post.get('title') or ''
                            description = post.get('tagline') or post.get('description') or ''
                            slug = post.get('slug')
                            url = f"https://www.producthunt.com/products/{slug}" if slug else ''
                            if name and url and url not in seen_urls:
                                seen_urls.add(url)
                                result = {
                                    "title": name,
                                    "url": url,
                                    "description": description,
                                    "keyword": keyword
                                }
                                results.append(result)
                                print(f"  📝 Added: {name[:50]}... {url}")
                        except Exception as e:
                            print(f"❌ Error processing product from JSON: {e}")
                    print(f"🎉 Scraping complete! Found {len(results)} products (JSON method)")
                    return results
                else:
                    print("❌ No products found in __NEXT_DATA__ JSON")
            except Exception as e:
                print(f"❌ Error parsing __NEXT_DATA__ JSON: {e}")
        # --- END NEW ---

        # Fallback to old selectors if new method fails
        # Find product items
        product_selectors = [
            'div[data-test="post-item"]',
            '.post-item',
            '.search-result',
            '[data-test="post"]',
            '.styles_item__Dk_nz',
            '.styles_post__IoxLo'
        ]
        
        product_items = []
        for selector in product_selectors:
            product_items = soup.select(selector)
            if product_items:
                print(f"✅ Found {len(product_items)} products using selector: {selector}")
                break
        
        if not product_items:
            # Try alternative approach
            product_links = soup.find_all('a', href=re.compile(r'/products/'))
            if product_links:
                print(f"✅ Found {len(product_links)} product links")
                product_items = [{'link': link} for link in product_links[:20]]
            else:
                print(f"❌ No product items found")
                return results
        
        for item in product_items:
            try:
                # Extract product URL
                if 'link' in item:
                    link_elem = item['link']
                    href = link_elem.get('href')
                else:
                    link_elem = item.find('a')
                    if not link_elem:
                        continue
                    href = link_elem.get('href')
                
                if not href:
                    continue
                
                # Build full URL
                if href.startswith('/'):
                    full_url = urljoin('https://www.producthunt.com', href)
                else:
                    full_url = href
                
                # Skip if we've seen this URL
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                # Extract title
                title = ""
                title_elem = item.find('h3') or item.find('h2') or item.find('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Extract description
                description = ""
                desc_elem = item.find('p')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                # Only add if we have meaningful content
                if title and full_url:
                    result = {
                        "title": title,
                        "url": full_url,
                        "description": description,
                        "keyword": keyword
                    }
                    results.append(result)
                    print(f"  📝 Added: {title[:50]}...")
            
            except Exception as e:
                print(f"❌ Error processing item: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Error scraping Product Hunt: {e}")
    
    print(f"🎉 Scraping complete! Found {len(results)} products")
    return results

def test_scraper():
    """Test the scraper"""
    print("🧪 Testing Product Hunt Scraper")
    print("=" * 50)
    
    test_keywords = ["customer service", "project management"]
    
    for keyword in test_keywords:
        print(f"\n📝 Testing: {keyword}")
        results = scrape_producthunt_working(keyword, max_pages=1)
        
        print(f"📊 Results: {len(results)}")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result['title']}")
            print(f"     Description: {result['description'][:100]}...")
            print(f"     URL: {result['url']}")
            print()

if __name__ == "__main__":
    test_scraper() 