import os
import sys
import random
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

# Add the current directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app and database
from app import app, db, SearchQuery, User

def seed_trend_data():
    """Seed the database with trend data for analytics"""
    print("Seeding trend data...")
    
    # Create a test user if it doesn't exist
    with app.app_context():
        user = User.query.filter_by(username="test").first()
        if not user:
            from werkzeug.security import generate_password_hash
            user = User(username="test", password=generate_password_hash("test"))
            db.session.add(user)
            db.session.commit()
            print("Created test user")
        
        # Keywords to seed - adding more common search terms
        keywords = [
            "mobile payments", 
            "cloud computing", 
            "machine learning", 
            "blockchain", 
            "cybersecurity",
            "remote work",
            "digital marketing",
            "e-commerce",
            "artificial intelligence",
            "data analytics",
            "mental health",  # Added this keyword
            "fitness",
            "nutrition",
            "productivity",
            "social media"
        ]
        
        # Sources
        sources = ["reddit", "stackoverflow", "producthunt", "complaintsboard"]
        
        # Generate random search queries over the past 180 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        # Delete existing data
        SearchQuery.query.delete()
        db.session.commit()
        
        # Generate random data
        for keyword in keywords:
            # Create between 20-50 entries for each keyword
            num_entries = random.randint(20, 50)
            for _ in range(num_entries):
                # Random date in the past 180 days
                random_days = random.randint(0, 180)
                timestamp = end_date - timedelta(days=random_days)
                
                # Random source
                source = random.choice(sources)
                
                # Create a mock result
                result = f"Analysis of {keyword} from {source} on {timestamp.strftime('%Y-%m-%d')}"
                
                # Create the search query
                query = SearchQuery(
                    keyword=keyword,
                    source=source,
                    result=result,
                    timestamp=timestamp,
                    user_id=user.id
                )
                db.session.add(query)
        
        db.session.commit()
        print(f"Added {len(keywords) * num_entries} trend data entries")

if __name__ == "__main__":
    seed_trend_data()
    print("Database seeded successfully!")