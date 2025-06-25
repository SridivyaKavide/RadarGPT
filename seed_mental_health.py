import os
import sys
import random
from datetime import datetime, timedelta

# Add the current directory to the path so we can import our app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app and database
from app import app, db, SearchQuery, User

def seed_mental_health_data():
    """Seed the database with mental health trend data"""
    print("Seeding mental health trend data...")
    
    # Create a test user if it doesn't exist
    with app.app_context():
        user = User.query.filter_by(username="test").first()
        if not user:
            from werkzeug.security import generate_password_hash
            user = User(username="test", password=generate_password_hash("test"))
            db.session.add(user)
            db.session.commit()
            print("Created test user")
        
        # Mental health specific keywords
        keywords = [
            "mental health",
            "anxiety",
            "depression",
            "stress management",
            "mindfulness",
            "therapy",
            "counseling",
            "mental wellness",
            "psychological support",
            "emotional health"
        ]
        
        # Sources
        sources = ["reddit", "stackoverflow", "producthunt", "complaintsboard"]
        
        # Generate data over the past 180 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        # Generate data with increasing frequency for mental health topics
        for keyword in keywords:
            # Create more entries for mental health topics (50-100 per keyword)
            num_entries = random.randint(50, 100)
            print(f"Adding {num_entries} entries for '{keyword}'")
            
            for i in range(num_entries):
                # More recent dates have higher probability
                # This creates an upward trend in the data
                weight = i / num_entries  # 0 to almost 1
                days_ago = int((1 - weight**2) * 180)  # Quadratic distribution favoring recent dates
                timestamp = end_date - timedelta(days=days_ago)
                
                # Random source
                source = random.choice(sources)
                
                # Create a more detailed result
                topics = ["user experience", "accessibility", "mobile app", "support groups", 
                          "online resources", "professional help", "self-care", "community"]
                sentiment = random.choice(["positive", "negative", "neutral", "mixed"])
                topic = random.choice(topics)
                
                result = f"Analysis of {keyword} from {source} on {timestamp.strftime('%Y-%m-%d')}. " \
                         f"Topic: {topic}. Sentiment: {sentiment}. " \
                         f"This entry discusses {keyword} in relation to {topic} with {sentiment} feedback."
                
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
        print(f"Added mental health trend data successfully")

if __name__ == "__main__":
    seed_mental_health_data()
    print("Mental health data seeded successfully!")