import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# List of RSS feeds to aggregate
RSS_FEEDS = [
    # General/World
    'http://feeds.bbci.co.uk/news/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
    'https://feeds.reuters.com/reuters/topNews',
    # Technology
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://www.wired.com/feed/rss',
    # Business
    'https://www.bloomberg.com/feed/podcast/etf-report.xml',
    'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    # Science/Health
    'https://www.sciencedaily.com/rss/all.xml',
    'https://www.medicalnewstoday.com/rss',
    # Entertainment
    'https://www.rollingstone.com/music/music-news/feed/',
    'https://www.hollywoodreporter.com/t/rss',
]

# Optionally, add more feeds for specific categories
CATEGORY_FEEDS = {
    'technology': [
        'https://techcrunch.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        'https://www.wired.com/feed/rss',
    ],
    'business': [
        'https://www.bloomberg.com/feed/podcast/etf-report.xml',
        'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    ],
    'health': [
        'https://www.medicalnewstoday.com/rss',
        'https://www.sciencedaily.com/rss/health_medicine.xml',
    ],
    'entertainment': [
        'https://www.rollingstone.com/music/music-news/feed/',
        'https://www.hollywoodreporter.com/t/rss',
    ],
    'science': [
        'https://www.sciencedaily.com/rss/all.xml',
    ],
}

def fetch_rss_headlines(category=None, max_items=20):
    """
    Fetch news headlines from RSS feeds. Optionally filter by category.
    Returns a list of dicts: {title, url, source, publishedAt}
    """
    feeds = RSS_FEEDS.copy()
    if category and category in CATEGORY_FEEDS:
        feeds = CATEGORY_FEEDS[category]
    headlines = []
    for feed_url in feeds:
        try:
            d = feedparser.parse(feed_url)
            for entry in d.entries[:max_items]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                published = entry.get('published', '') or entry.get('updated', '')
                source = d.feed.get('title', 'Unknown')
                # Try to parse date
                try:
                    publishedAt = datetime(*entry.published_parsed[:6]).isoformat() if 'published_parsed' in entry else ''
                except Exception:
                    publishedAt = published
                headlines.append({
                    'title': title,
                    'url': url,
                    'source': source,
                    'publishedAt': publishedAt,
                    'category': category or 'general',
                    'region': 'global',
                })
        except Exception as e:
            continue
    return headlines[:max_items]

# Optional: fallback to scraping a few major sites if RSS fails
def scrape_headlines_from_site(url, selector, max_items=10):
    """Scrape headlines from a news site using a CSS selector."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        headlines = []
        for elem in soup.select(selector)[:max_items]:
            title = elem.get_text(strip=True)
            link = elem.get('href')
            if link and not link.startswith('http'):
                link = url.rstrip('/') + '/' + link.lstrip('/')
            headlines.append({
                'title': title,
                'url': link or url,
                'source': url,
                'publishedAt': '',
                'category': 'general',
                'region': 'global',
            })
        return headlines
    except Exception:
        return []

def get_news_trends_hybrid(category=None, max_items=20):
    """
    Try RSS first, then fallback to scraping, then fallback to NewsAPI (to be called from app.py)
    """
    headlines = fetch_rss_headlines(category, max_items)
    if headlines:
        return headlines
    # Fallback: scrape a few major sites (example: BBC)
    scraped = scrape_headlines_from_site('https://www.bbc.com/news', 'a.gs-c-promo-heading', max_items)
    if scraped:
        return scraped
    # Final fallback: return empty, app.py can then use NewsAPI if desired
    return [] 