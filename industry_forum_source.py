import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from diskcache import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class IndustryForumSource:
    """Industry forum data source for PainRadar"""
    
    def __init__(self):
        # Define common industry forums
        self.forums = {
            "fintech": [
                "https://community.fintechtalk.co.uk",
                "https://forum.fintechee.com"
            ],
            "healthcare": [
                "https://community.himss.org",
                "https://healthitforums.com"
            ],
            "ecommerce": [
                "https://community.shopify.com",
                "https://community.bigcommerce.com"
            ],
            "saas": [
                "https://community.atlassian.com",
                "https://community.hubspot.com"
            ],
            "edtech": [
                "https://community.canvaslms.com",
                "https://community.brightspace.com"
            ]
        }
    
    def get_industry_forum_posts(self, forum_url, keyword, max_posts=20):
        """Generic scraper for industry forums"""
        cache_key = f"forum_{forum_url}_{keyword}_{max_posts}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            driver = webdriver.Chrome(options=options)
            
            search_url = f"{forum_url}/search?q={keyword.replace(' ', '+')}"
            driver.get(search_url)
            
            # Wait for search results
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.search-result-link"))
                )
            except TimeoutException:
                driver.quit()
                return []
            
            # Get search results
            soup = BeautifulSoup(driver.page_source, "html.parser")
            results = []
            
            for result_elem in soup.select("div.search-result")[:max_posts]:
                title_elem = result_elem.select_one("a.search-result-link")
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                url = title_elem.get("href")
                if not url.startswith("http"):
                    url = forum_url + url
                    
                excerpt = result_elem.select_one("div.search-result-excerpt")
                excerpt_text = excerpt.text.strip() if excerpt else ""
                
                results.append({
                    "title": title,
                    "url": url,
                    "excerpt": excerpt_text
                })
            
            driver.quit()
            cache.set(cache_key, results, expire=3600)
            return results
        except Exception as e:
            logger.error(f"Error fetching forum posts: {e}")
            if 'driver' in locals():
                driver.quit()
            return []
    
    def get_forum_posts_by_vertical(self, vertical, keyword, max_posts=20):
        """Get forum posts from forums related to a specific vertical"""
        if vertical not in self.forums:
            return []
            
        results = []
        for forum_url in self.forums[vertical]:
            try:
                forum_results = self.get_industry_forum_posts(forum_url, keyword, max_posts=max_posts//len(self.forums[vertical]))
                results.extend(forum_results)
            except Exception as e:
                logger.error(f"Error fetching from {forum_url}: {e}")
                
        return results[:max_posts]

# Singleton instance
industry_forum_source = IndustryForumSource()