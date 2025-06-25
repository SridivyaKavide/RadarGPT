import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter
import re
from textblob import TextBlob
from sqlalchemy import text

class TrendAnalytics:
    """Class for analyzing trends over time and competitive analysis"""
    
    def __init__(self, db):
        self.db = db
        
    def get_trend_data(self, keyword, days=90):
        """Get trend data for a keyword over time"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Debug print
        print(f"Searching for keyword: '{keyword}', start_date: {start_date}")
        
        # First try exact match
        query = self.db.session.execute(
            text("""
            SELECT keyword, timestamp, source, result 
            FROM search_query 
            WHERE timestamp >= :start_date
            AND keyword = :keyword
            ORDER BY timestamp
            """),
            {
                "start_date": start_date,
                "keyword": keyword
            }
        )
        
        results = query.fetchall()
        
        # If no results, try LIKE search
        if not results:
            print(f"No exact matches for '{keyword}', trying LIKE search")
            query = self.db.session.execute(
                text("""
                SELECT keyword, timestamp, source, result 
                FROM search_query 
                WHERE timestamp >= :start_date
                AND keyword LIKE :keyword_pattern
                ORDER BY timestamp
                """),
                {
                    "start_date": start_date,
                    "keyword_pattern": f"%{keyword}%"
                }
            )
            results = query.fetchall()
            print(f"Found {len(results)} results with LIKE search for '{keyword}'")
            
        # If still no results, try searching for related terms
        if not results:
            print(f"No LIKE matches for '{keyword}', trying related terms")
            # Map common search terms to related keywords in our database
            related_terms = {
                "mental": "mental health",
                "health": "mental health",
                "anxiety": "anxiety",
                "depression": "depression",
                "stress": "stress management",
                "mindful": "mindfulness",
                "therapy": "therapy",
                "counseling": "counseling",
                "wellness": "mental wellness",
                "psychological": "psychological support",
                "emotional": "emotional health"
            }
            
            # Check if any word in the keyword matches our related terms
            for word in keyword.lower().split():
                for term, related in related_terms.items():
                    if term in word:
                        print(f"Found related term: '{related}' for '{word}'")
                        query = self.db.session.execute(
                            text("""
                            SELECT keyword, timestamp, source, result 
                            FROM search_query 
                            WHERE timestamp >= :start_date
                            AND keyword = :keyword
                            ORDER BY timestamp
                            """),
                            {
                                "start_date": start_date,
                                "keyword": related
                            }
                        )
                        results = query.fetchall()
                        if results:
                            print(f"Found {len(results)} results for related term '{related}'")
                            break
                if results:
                    break
        
        results = query.fetchall()
        if not results:
            return None
            
        # Process results into time series
        df = pd.DataFrame(results, columns=["keyword", "timestamp", "source", "result"])
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        
        # Count mentions by date
        date_counts = df.groupby("date").size()
        
        # Calculate sentiment over time
        df["sentiment"] = df["result"].apply(lambda x: TextBlob(x).sentiment.polarity if x else 0)
        sentiment_by_date = df.groupby("date")["sentiment"].mean()
        
        # Extract common topics/themes
        all_text = " ".join(df["result"].fillna(""))
        topics = self._extract_topics(all_text)
        
        return {
            "date_range": [str(d) for d in date_counts.index],
            "mention_counts": date_counts.tolist(),
            "sentiment_trend": sentiment_by_date.tolist(),
            "top_topics": topics[:10]
        }
    
    def _extract_topics(self, text):
        """Extract common topics from text"""
        # Simple implementation - in production would use more sophisticated NLP
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        # Filter out common stopwords
        stopwords = {"and", "the", "for", "that", "this", "with", "from", "have", "are", "not"}
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
            sentiment_scaled = [s * max(trend_data["mention_counts"]) for s in trend_data["sentiment_trend"]]
            plt.plot(dates, sentiment_scaled, 'g-', label="Sentiment (scaled)")
        
        plt.title("Trend Analysis")
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
        """Analyze competitors based on keyword"""
        # This would typically involve more sophisticated analysis
        # For now, we'll extract competitor mentions from search results
        
        query = self.db.session.execute(
            text("""
            SELECT result 
            FROM search_query 
            WHERE keyword LIKE :keyword_pattern
            AND result IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 20
            """),
            {"keyword_pattern": f"%{keyword}%"}
        )
        
        results = query.fetchall()
        if not results:
            return None
            
        # Combine all results
        all_text = " ".join([r[0] for r in results if r[0]])
        
        # Extract company/product names (simplified approach)
        # In production, would use named entity recognition
        company_pattern = r'(?:called|named|by|from|company|product|app|service|platform)\s+([A-Z][a-zA-Z0-9]+)'
        companies = re.findall(company_pattern, all_text)
        
        # Count occurrences
        company_counts = Counter(companies)
        
        # Get top competitors
        top_competitors = company_counts.most_common(10)
        
        # Extract strengths/weaknesses for each competitor (simplified)
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
            
            competitor_analysis[company] = {
                "strengths": strengths[:3],  # Limit to top 3
                "weaknesses": weaknesses[:3]
            }
        
        return {
            "top_competitors": top_competitors,
            "competitor_analysis": competitor_analysis
        }