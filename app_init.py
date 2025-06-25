"""
This file contains initialization code to be added to app.py
"""

# Add these imports at the top of app.py
from models import db, User, SearchQuery, QueryChat, Team, TeamMember, SharedQuery, Comment, Integration, TrendData
from data_sources import data_source_manager
from twitter_source import twitter_source
from app_store_source import app_store_source
from industry_forum_source import industry_forum_source
from analytics import TrendAnalytics
from collaboration import CollaborationManager
from integrations import integration_manager
from vertical_insights import vertical_insights
from routes import register_routes

# Add this after app initialization in app.py
def init_app(app):
    # Initialize database with models
    db.init_app(app)
    
    # Register routes
    register_routes(app)
    
    # Create all tables
    with app.app_context():
        db.create_all()
    
    return app

# Add this to the end of app.py
if __name__ == "__main__":
    app = init_app(app)
    app.run(debug=True)