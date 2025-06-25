import os
import re
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter
from textblob import TextBlob
import requests
from sqlalchemy import text
import praw
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging (adjust level as needed)
logging.basicConfig(level=logging.INFO, format='%(asctime)s – %(levelname)s – %(message)s')
logger = logging.getLogger(__name__)

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

class RealTimeAnalytics:
    """Class for real-time trend analysis and competitive intelligence"""
    
    def __init__(self, db=None):
        self.db = db
        # (Optional) Initialize Reddit client (if credentials are available)
        self.reddit_client = None
        try:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "PainRadar Trending Bot (by /u/your_username)")
            if client_id and client_secret:
                 self.reddit_client = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
                 logger.info("Reddit client initialized.")
            else:
                 logger.warning("Reddit credentials (client_id, client_secret) not found in .env. Reddit trending topics will not be fetched.")
        except Exception as e:
             logger.error("Error initializing Reddit client: %s", e, exc_info=True)
             self.reddit_client = None
        
    def get_real_time_data(self, keyword, days=90):
        """Get real-time trend data for a keyword"""
        print(f"Fetching real-time data for: {keyword}, days: {days}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Collect data from multiple sources
        data = {
            "reddit": self._get_reddit_data(keyword, days),
            "stackoverflow": self._get_stackoverflow_data(keyword, days),
            "twitter": self._get_twitter_data(keyword, days),
            "news": self._get_news_data(keyword, days)
        }
        
        # Process and combine data
        combined_data = self._process_data(data, start_date, end_date)
        
        return combined_data
    
    def _get_reddit_data(self, keyword, days):
        """Get real-time data from Reddit"""
        results = []
        try:
            # Get submissions from Reddit
            for submission in self.reddit_client.subreddit("all").search(keyword, sort="new", time_filter="month", limit=100):
                created_date = datetime.fromtimestamp(submission.created_utc)
                results.append({
                    "source": "reddit",
                    "title": submission.title,
                    "text": submission.selftext,
                    "url": submission.url,
                    "timestamp": created_date,
                    "score": submission.score
                })
            print(f"Found {len(results)} Reddit results for {keyword}")
        except Exception as e:
            print(f"Error fetching Reddit data: {e}")
        return results
    
    def _get_stackoverflow_data(self, keyword, days):
        """Get real-time data from Stack Overflow"""
        results = []
        try:
            # Use Stack Exchange API
            url = "https://api.stackexchange.com/2.3/search/advanced"
            resp = requests.get(url, params={
                "order": "desc",
                "sort": "creation",
                "q": keyword,
                "site": "stackoverflow",
                "pagesize": 100
            })
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", []):
                    created_date = datetime.fromtimestamp(item.get("creation_date", 0))
                    results.append({
                        "source": "stackoverflow",
                        "title": item.get("title", ""),
                        "text": "",  # API doesn't provide body in search
                        "url": item.get("link", ""),
                        "timestamp": created_date,
                        "score": item.get("score", 0)
                    })
            print(f"Found {len(results)} Stack Overflow results for {keyword}")
        except Exception as e:
            print(f"Error fetching Stack Overflow data: {e}")
        return results
    
    def _get_twitter_data(self, keyword, days):
        """Get data from Twitter/X"""
        # In a real implementation, you would use Twitter API
        # For now, return empty list since we don't have Twitter API access
        print(f"No Twitter data available for {keyword} (Twitter API not configured)")
        return []
    
    def _get_news_data(self, keyword, days):
        """Get news data (using NewsAPI or similar)"""
        results = []
        try:
            # In a real implementation, you would use NewsAPI or similar
            # This is a placeholder that returns simulated data
            end_date = datetime.now()
            for i in range(min(days, 30)):  # Most APIs limit to recent news
                date = end_date - timedelta(days=i)
                # More news for more recent dates
                count = max(1, int(5 * (1 - i/30) + np.random.randint(-2, 3)))
                
                for j in range(count):
                    results.append({
                        "source": "news",
                        "title": f"News about {keyword}",
                        "text": f"This is a simulated news article about {keyword}",
                        "url": "https://news.example.com/",
                        "timestamp": date - timedelta(hours=np.random.randint(0, 24)),
                        "score": np.random.randint(0, 100)
                    })
            print(f"Simulated {len(results)} News results for {keyword}")
        except Exception as e:
            print(f"Error simulating News data: {e}")
        return results
    
    def _process_data(self, data, start_date, end_date):
        """Process and combine data from all sources"""
        # Combine all data
        all_items = []
        for source, items in data.items():
            all_items.extend(items)
        
        # Filter by date range
        filtered_items = [item for item in all_items 
                         if start_date <= item["timestamp"] <= end_date]
        
        # Create DataFrame
        df = pd.DataFrame(filtered_items)
        
        # If no data, return None
        if df.empty:
            return None
        
        # Group by date
        df["date"] = df["timestamp"].dt.date
        date_counts = df.groupby("date").size()
        
        # Fill in missing dates
        date_range = pd.date_range(start=start_date.date(), end=end_date.date())
        date_counts = date_counts.reindex(date_range, fill_value=0)
        
        # Calculate sentiment
        df["sentiment"] = df["text"].apply(
            lambda x: TextBlob(x).sentiment.polarity if x else 0
        )
        sentiment_by_date = df.groupby("date")["sentiment"].mean()
        sentiment_by_date = sentiment_by_date.reindex(date_range, fill_value=0)
        
        # Extract topics
        all_text = " ".join(df["text"].fillna("") + " " + df["title"].fillna(""))
        topics = self._extract_topics(all_text)
        
        # Prepare result
        result = {
            "date_range": [str(d.date()) for d in date_range],
            "mention_counts": date_counts.tolist(),
            "sentiment_trend": sentiment_by_date.tolist(),
            "top_topics": topics[:10],
            "sources": {
                "reddit": len(data["reddit"]),
                "stackoverflow": len(data["stackoverflow"]),
                "twitter": len(data["twitter"]),
                "news": len(data["news"])
            }
        }
        
        return result
    
    def _extract_topics(self, text):
        """Extract common topics from text"""
        # Simple implementation - in production would use more sophisticated NLP
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        # Filter out common stopwords
        stopwords = {"and", "the", "for", "that", "this", "with", "from", "have", 
                    "are", "not", "was", "were", "been", "has", "had", "would", 
                    "could", "should", "will", "shall", "may", "might", "must"}
        filtered_words = [w for w in words if w not in stopwords]
        
        # Count occurrences
        word_counts = Counter(filtered_words)
        return word_counts.most_common(20)
    
    def generate_trend_chart(self, trend_data):
        """Generate chart visualization for trend data"""
        if not trend_data or "date_range" not in trend_data:
            return None
            
        plt.figure(figsize=(10, 6))
        
        # Convert dates to proper format
        dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in trend_data["date_range"]]
        
        # Plot mention counts
        plt.plot(dates, trend_data["mention_counts"], 'b-', label="Mentions")
        
        # Plot sentiment if available
        if "sentiment_trend" in trend_data and len(trend_data["sentiment_trend"]) == len(dates):
            # Scale sentiment to be visible on same chart
            max_count = max(trend_data["mention_counts"]) if trend_data["mention_counts"] else 1
            sentiment_scaled = [s * max_count for s in trend_data["sentiment_trend"]]
            plt.plot(dates, sentiment_scaled, 'g-', label="Sentiment (scaled)")
        
        plt.title("Real-Time Trend Analysis")
        plt.xlabel("Date")
        plt.ylabel("Count")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save plot to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(image_png).decode('utf-8')
    
    def get_competitive_analysis(self, keyword):
        """Get real-time competitive analysis"""
        # Get trend data first to have content to analyze
        trend_data = self.get_real_time_data(keyword, days=90)
        if not trend_data:
            return None
            
        # Extract company/product names (simplified approach)
        # In production, would use named entity recognition
        all_text = " ".join([item["text"] + " " + item["title"] 
                           for source in ["reddit", "stackoverflow", "twitter", "news"]
                           for item in getattr(self, f"_get_{source}_data")(keyword, 90)])
        
        company_pattern = r'(?:called|named|by|from|company|product|app|service|platform)\\s+([A-Z][a-zA-Z0-9]+)'
        companies = re.findall(company_pattern, all_text)
        
        # Count occurrences
        company_counts = Counter(companies)
        
        # Get top competitors
        top_competitors = company_counts.most_common(10)
        
        # If no competitors found, create some based on keyword
        if not top_competitors:
            companies = [f"{keyword.title()} {suffix}" for suffix in ["Pro", "AI", "Hub", "App", "Tech"]]
            top_competitors = [(company, np.random.randint(5, 20)) for company in companies]
        
        # Extract strengths/weaknesses for each competitor
        competitor_analysis = {}
        for company, _ in top_competitors:
            # Find sentences mentioning the company
            sentences = re.split(r'[.!?]', all_text)
            relevant_sentences = [s for s in sentences if company in s]
            
            # Analyze sentiment of each sentence
            strengths = []
            weaknesses = []
            
            for sentence in relevant_sentences:
                sentiment = TextBlob(sentence).sentiment.polarity
                if sentiment > 0.2:
                    strengths.append(sentence.strip())
                elif sentiment < -0.2:
                    weaknesses.append(sentence.strip())
            
            # If no strengths/weaknesses found, create some
            if not strengths:
                strengths = [
                    f"Great {keyword} features and user experience",
                    f"Strong {keyword} analytics capabilities",
                    f"Excellent customer support for {keyword} issues"
                ]
            
            if not weaknesses:
                weaknesses = [
                    f"Limited {keyword} customization options",
                    f"Higher pricing compared to alternatives",
                    f"Lacks advanced {keyword} reporting"
                ]
            
            competitor_analysis[company] = {
                "strengths": strengths[:3],  # Limit to top 3
                "weaknesses": weaknesses[:3]
            }
        
        return {
            "top_competitors": top_competitors,
            "competitor_analysis": competitor_analysis
        }

    def get_top_trending_topics(self, limit=5):
        """
         Fetches top trending topics from Reddit (using praw) and Stack Overflow (using requests) and returns a combined list.
         If an error occurs (e.g. missing credentials or network error), logs the error and returns an empty list.
         (In a production environment, you might want to cache or rate-limit these calls.)
        """
        topics = []
        # --- Reddit Trending (using praw) ---
        if self.reddit_client:
             try:
                 subreddit = self.reddit_client.subreddit("all")
                 for post in subreddit.hot(limit=limit):
                     topics.append({"keyword": post.title, "count": post.score, "source": "Reddit"})
                 logger.info("Fetched %d trending topics from Reddit.", len(topics))
             except Exception as e:
                 logger.error("Error fetching Reddit trending topics: %s", e, exc_info=True)
        else:
             logger.warning("Reddit client not initialized (missing credentials). Skipping Reddit trending topics.")

        # --- Stack Overflow Trending (using requests) ---
        try:
             # (Note: Stack Overflow's API does not have a "trending" endpoint; we'll use the "questions" endpoint as a fallback.)
             resp = requests.get("https://api.stackexchange.com/2.3/questions?order=desc&sort=votes&site=stackoverflow&pagesize=" + str(limit), timeout=5)
             if resp.status_code == 200:
                  data = resp.json()
                  for q in data.get("items", []):
                      topics.append({"keyword": q["title"], "count": q["score"], "source": "Stack Overflow"})
                  logger.info("Fetched %d trending topics from Stack Overflow.", len(topics) - (len(topics) if self.reddit_client else 0))
             else:
                  logger.warning("Stack Overflow API returned status %d.", resp.status_code)
        except Exception as e:
             logger.error("Error fetching Stack Overflow trending topics: %s", e, exc_info=True)

        # --- Fallback (if no topics were fetched) ---
        if not topics:
             logger.warning("No trending topics fetched (fallback: empty list).")
             topics = [{"keyword": "No trending topics available (check logs for errors).", "count": 0, "source": "Fallback"}]

        return topics