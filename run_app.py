import os
import sys
from flask import Flask
from dotenv import load_dotenv
from app import app, db
from models import User, SearchQuery, QueryChat, Team, TeamMember, SharedQuery, Comment, Integration, TrendData

# Load environment variables
load_dotenv()

# Create necessary directories
os.makedirs('instance', exist_ok=True)
os.makedirs('radargpt_cache', exist_ok=True)

# Import the original app
sys.path.insert(0, os.path.abspath('.'))
from app import app as original_app

def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created.")

# Run the original app
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)