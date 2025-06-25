import os
import sys
from flask import Flask
from models import db, User, SearchQuery, QueryChat, Team, TeamMember, SharedQuery, Comment, Integration, TrendData

def integrate_new_features(app):
    """
    Integrate new features into the existing Flask app
    """
    # Import the routes
    from app_routes import register_routes
    
    # Register the routes
    register_routes(app)
    
    # Create database tables for new models
    with app.app_context():
        # Create tables for new models only
        db.create_all()
    
    # Add new data sources to multi_search
    from app import multi_search as original_multi_search
    from twitter_source import twitter_source
    from app_store_source import app_store_source
    from industry_forum_source import industry_forum_source
    
    # Override the multi_search function to include new data sources
    def enhanced_multi_search():
        response = original_multi_search()
        
        # If it's a JSON response, enhance it with additional data sources
        if hasattr(response, 'json'):
            data = response.json
            keyword = data.get('keyword', '')
            
            # Add Twitter data if available
            try:
                twitter_data = twitter_source.get_twitter_posts(keyword, max_posts=20)
                if twitter_data:
                    data['sources']['Twitter'] = twitter_data
            except Exception as e:
                print(f"Error fetching Twitter data: {e}")
            
            # Add App Store data if available
            try:
                app_id = "389801252"  # Example app ID
                app_store_data = app_store_source.get_app_store_reviews(app_id, max_reviews=10)
                if app_store_data:
                    data['sources']['App Store'] = app_store_data
            except Exception as e:
                print(f"Error fetching App Store data: {e}")
            
            # Add Industry Forum data if available
            try:
                forum_data = industry_forum_source.get_forum_posts_by_vertical('saas', keyword, max_posts=10)
                if forum_data:
                    data['sources']['Industry Forums'] = forum_data
            except Exception as e:
                print(f"Error fetching Industry Forum data: {e}")
            
            response.json = data
        
        return response
    
    # Replace the original multi_search with the enhanced version
    app.view_functions['multi_search'] = enhanced_multi_search
    
    return app