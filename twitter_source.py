import os
import tweepy
import logging
from diskcache import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class TwitterSource:
    """Twitter/X data source for PainRadar"""
    
    def __init__(self):
        self.api = self._init_twitter()
        
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
    
    def get_twitter_posts(self, keyword, max_posts=50):
        """Get Twitter/X posts related to keyword"""
        cache_key = f"twitter_{keyword}_{max_posts}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        if not self.api:
            logger.warning("Twitter API not initialized, returning empty results")
            return []
            
        try:
            results = []
            tweets = self.api.search_tweets(q=keyword, count=max_posts, tweet_mode="extended")
            
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

# Singleton instance
twitter_source = TwitterSource()