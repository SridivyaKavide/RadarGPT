import requests
import re
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from diskcache import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class AppStoreSource:
    """App Store reviews data source for PainRadar"""
    
    def __init__(self):
        pass
    
    def get_app_store_reviews(self, app_id, max_reviews=50):
        """Get app reviews from Apple App Store"""
        cache_key = f"appstore_{app_id}_{max_reviews}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        try:
            url = f"https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []
                
            data = response.json()
            results = []
            
            for entry in data.get("feed", {}).get("entry", [])[:max_reviews]:
                results.append({
                    "title": entry.get("title", {}).get("label", ""),
                    "content": entry.get("content", {}).get("label", ""),
                    "rating": entry.get("im:rating", {}).get("label", ""),
                    "author": entry.get("author", {}).get("name", {}).get("label", ""),
                    "date": entry.get("updated", {}).get("label", "")
                })
                
            cache.set(cache_key, results, expire=3600)
            return results
        except Exception as e:
            logger.error(f"Error fetching App Store reviews: {e}")
            return []
    
    def get_play_store_reviews(self, app_id, max_reviews=50):
        """Get app reviews from Google Play Store using Selenium"""
        cache_key = f"playstore_{app_id}_{max_reviews}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            driver = webdriver.Chrome(options=options)
            
            url = f"https://play.google.com/store/apps/details?id={app_id}&showAllReviews=true"
            driver.get(url)
            
            # Wait for reviews to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[jsname='fk8dgd']"))
            )
            
            # Scroll to load more reviews
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                import time
                time.sleep(1)
            
            reviews = driver.find_elements(By.CSS_SELECTOR, "div[jsname='fk8dgd']")
            results = []
            
            for review in reviews[:max_reviews]:
                try:
                    rating_element = review.find_element(By.CSS_SELECTOR, "div[role='img']")
                    rating = rating_element.get_attribute("aria-label")
                    rating = re.search(r"(\d+)", rating).group(1) if rating else "?"
                    
                    author = review.find_element(By.CSS_SELECTOR, "span[class='X43Kjb']").text
                    date = review.find_element(By.CSS_SELECTOR, "span[class='p2TkOb']").text
                    content = review.find_element(By.CSS_SELECTOR, "div[class='h3YV2d']").text
                    
                    results.append({
                        "author": author,
                        "date": date,
                        "rating": rating,
                        "content": content
                    })
                except Exception as e:
                    continue
            
            driver.quit()
            cache.set(cache_key, results, expire=3600)
            return results
        except Exception as e:
            logger.error(f"Error fetching Play Store reviews: {e}")
            if 'driver' in locals():
                driver.quit()
            return []

# Singleton instance
app_store_source = AppStoreSource()