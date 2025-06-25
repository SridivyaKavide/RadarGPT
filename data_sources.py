import os
import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tweepy
import praw
import json
import logging
from diskcache import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class DataSourceManager:
    """Manager class for all data sources"""
    
    def __init__(self):
        # Load environment variables
        self.reddit = self._init_reddit()
        self.twitter = self._init_twitter()
        self.linkedin_enabled = os.getenv("LINKEDIN_ENABLED", "false").lower() == "true"
        
    def _init_reddit(self):
        """Initialize Reddit API client"""
        try:
            # Check if API keys are available
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT")
            
            if not all([client_id, client_secret, user_agent]):
                logger.warning("Reddit API credentials not found or incomplete")
                return None
                
            return praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Failed to initialize Reddit: {e}")
            return None
            
    def _init_twitter(self):
        """Initialize Twitter API client"""
        try:
            # Check if API keys are available
            api_key = os.getenv("TWITTER_API_KEY")
            api_secret = os.getenv("TWITTER_API_SECRET")
            access_token = os.getenv("TWITTER_ACCESS_TOKEN")
            access_secret = os.getenv("TWITTER_ACCESS_SECRET")
            
            if not all([api_key, api_secret, access_token, access_secret]):
                logger.warning("Twitter API credentials not found or incomplete")
                return None
                
            auth = tweepy.OAuth1UserHandler(
                api_key,
                api_secret,
                access_token,
                access_secret
            )
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter: {e}")
            return None
    
    def get_reddit_posts(self, keyword, max_posts=5, subreddit="all"):
        """Get Reddit posts with replies"""
        cache_key = f"reddit_{keyword}_{max_posts}_{subreddit}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        if not self.reddit:
            logger.warning("Reddit API not initialized, returning empty results")
            return []
            
        try:
            results = []
            submissions = self.reddit.subreddit(subreddit).search(keyword, limit=max_posts)
            
            for submission in submissions:
                submission.comments.replace_more(limit=0)
                comments = [c.body or "" for c in submission.comments.list()[:10]]
                results.append({
                    "title": submission.title or "",
                    "selftext": submission.selftext or "",
                    "url": submission.url or "",
                    "comments": comments,
                    "score": submission.score,
                    "created_utc": submission.created_utc
                })
                
            cache.set(cache_key, results, expire=3600)
            return results
        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")
            return []
    
    def get_twitter_posts(self, keyword, max_posts=50):
        """Get Twitter/X posts related to keyword"""
        cache_key = f"twitter_{keyword}_{max_posts}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        if not self.twitter:
            logger.warning("Twitter API not initialized, returning empty results")
            return []
            
        try:
            results = []
            tweets = self.twitter.search_tweets(q=keyword, count=max_posts, tweet_mode="extended")
            
            for tweet in tweets:
                results.append({
                    "text": tweet.full_text,
                    "user": tweet.user.screen_name,
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count,
                    "created_at": tweet.created_at.isoformat(),
                    "url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
                })
                
            cache.set(cache_key, results, expire=3600)
            return results
        except Exception as e:
            logger.error(f"Error fetching Twitter posts: {e}")
            return []
    
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
    
    def get_linkedin_posts(self, keyword, max_posts=20):
        """Get LinkedIn posts (requires LinkedIn API access)"""
        if not self.linkedin_enabled:
            return []
            
        cache_key = f"linkedin_{keyword}_{max_posts}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        # This is a placeholder - LinkedIn API access requires approval
        # In a real implementation, you would use the LinkedIn API client
        return []

# Singleton instance
data_source_manager = DataSourceManager()