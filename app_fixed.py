import os
import re
import time
import json
import random
from datetime import datetime, timedelta
import logging
from collections import Counter
import re

# Global variable to store the latest status message
current_status = {}

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, Response
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

# Import vertical insights
from vertical_insights import VerticalInsights
# Import analytics
from analytics import TrendAnalytics

# Import sqlalchemy functions
from sqlalchemy import func, desc, case

# --- Source list for multi_search ---
ALL_SOURCES = [
    "Reddit",
    "Stack Overflow",
    "ComplaintsBoard",
    "Product Hunt",
    "Quora"
]

# --- Load environment variables ---
load_dotenv()

# --- Gemini setup ---
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# --- Verticals setup ---
vertical_insights = VerticalInsights()
VERTICALS = vertical_insights.VERTICALS

# --- Reddit (PRAW) setup ---
import praw
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Import improved ComplaintsBoard scraper
from improved_complaintsboard import improved_complaintsboard_scraper
from fix_producthunt import scrape_producthunt_fixed
# --- Diskcache persistent cache ---
from diskcache import Cache
cache = Cache("radargpt_cache")

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# --- Database and Login setup ---
app.config['SECRET_KEY'] = 'f3bce3d9a4b21e3d78d0f6a1c7eaf5a914ea7d1b2cfc9e4d8a237f6b5e8d4c13'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('POSTGRES_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for localhost

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    queries = db.relationship('SearchQuery', backref='user', lazy=True)

class SearchQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(50), nullable=False)
    mode = db.Column(db.String(50), nullable=True)
    result = db.Column(db.Text, nullable=True)  # Stores summary
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chats = db.relationship('QueryChat', backref='query', lazy=True)
    vertical = db.Column(db.String(50), nullable=True)  # New column for vertical insights
    
class QueryChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
class VerticalChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vertical = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(200), nullable=False)  # was 'query'
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text, nullable=True)  # Stores the insights context
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def get_date_range(period):
    now = datetime.utcnow()
    if period == 'week':
        return now - timedelta(days=7)
    elif period == 'month':
        return now - timedelta(days=30)
    elif period == 'year':
        return now - timedelta(days=365)
    else:
        return now - timedelta(days=7)  # Default to week

def get_daily_search_counts(start_date, end_date):
    daily_counts = db.session.query(
        func.date(SearchQuery.timestamp).label('date'),
        func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).group_by(
        func.date(SearchQuery.timestamp)
    ).all()
    
    return [{'date': str(d.date), 'count': d.count} for d in daily_counts]

def get_category_distribution(start_date, end_date):
    category_counts = db.session.query(
        SearchQuery.source,
        func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).group_by(
        SearchQuery.source
    ).all()
    
    return [{'category': c.source, 'count': c.count} for c in category_counts]

def get_trending_topics(start_date, end_date, limit=10):
    trending = db.session.query(
        SearchQuery.keyword,
        func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).group_by(
        SearchQuery.keyword
    ).order_by(
        desc('count')
    ).limit(limit).all()
    
    return [{'topic': t.keyword, 'count': t.count} for t in trending]

def get_analytics_insights(start_date, end_date):
    total_searches = db.session.query(func.count(SearchQuery.id)).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).scalar()
    
    unique_keywords = db.session.query(func.count(func.distinct(SearchQuery.keyword))).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).scalar()
    
    return {
        'total_searches': total_searches,
        'unique_keywords': unique_keywords
    }

@app.route('/pain_dashboard')
@login_required
def dashboard():
    return render_template('pain_dashboard.html')

@app.route('/api/vertical_chat_history', methods=['GET'])
@login_required
def get_vertical_chat_history():
    vertical = request.args.get('vertical')
    if not vertical:
        return jsonify({'error': 'Vertical parameter is required'}), 400
        
    chats = VerticalChat.query.filter_by(
        vertical=vertical,
        user_id=current_user.id
    ).order_by(VerticalChat.timestamp.asc()).all()
    
    return jsonify([{
        'id': chat.id,
        'role': chat.role,
        'text': chat.text,
        'timestamp': chat.timestamp.isoformat(),
        'context': chat.context
    } for chat in chats])

@app.route('/api/status')
def api_status():
    return jsonify(current_status)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))

@app.route('/generate-solution', methods=['POST'])
def generate_solution():
    data = request.get_json()
    if not data or 'pain_point' not in data:
        return jsonify({'error': 'Pain point is required'}), 400
        
    pain_point = data['pain_point']
    
    # Create prompt for solution generation
    prompt = f"""
    Based on this pain point, generate a detailed startup solution:
    
    Pain Point: {pain_point}
    
    Provide the following:
    1. Solution Overview
    2. Key Features
    3. Target Market
    4. Revenue Model
    5. Implementation Steps
    6. Success Metrics
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        return jsonify({
            'solution': response.text.strip()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pain-cloud', methods=['GET'])
def pain_cloud_page():
    return render_template('pain_cloud.html')

@app.route('/pain-cloud', methods=['POST'])
def pain_cloud_api():
    data = request.get_json()
    if not data or 'keyword' not in data:
        return jsonify({'error': 'Keyword is required'}), 400
        
    keyword = data['keyword']
    
    # Get Reddit posts
    subreddits = ['startups', 'entrepreneur', 'smallbusiness']
    all_posts = []
    
    for subreddit in subreddits:
        try:
            posts = reddit.subreddit(subreddit).search(keyword, limit=10)
            for post in posts:
                all_posts.append({
                    'title': post.title,
                    'text': post.selftext,
                    'score': post.score,
                    'url': post.url,
                    'created': datetime.utcfromtimestamp(post.created_utc).isoformat() if post.created_utc else ""
                })
        except Exception as e:
            print(f"Error fetching from {subreddit}: {e}")
            continue
    
    # Analyze posts for pain points
    pain_points = []
    for post in all_posts:
        prompt = f"""
        Analyze this post for pain points and problems:
        
        Title: {post['title']}
        Text: {post['text']}
        
        Extract specific pain points and problems that could be solved by a startup.
        Format as a list of problems, each with:
        - Problem description
        - Severity (1-10)
        - Affected users
        - Potential impact
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            analysis = response.text.strip()
            pain_points.append({
                'post': post,
                'analysis': analysis
            })
        except Exception as e:
            print(f"Error analyzing post: {e}")
            continue
    
    return jsonify({
        'posts': all_posts,
        'pain_points': pain_points
    })

@app.route('/pain-cloud-realtime', methods=['GET'])
def pain_cloud_realtime_page():
    return render_template('pain_cloud_realtime.html')

@app.route('/pain-cloud-combined', methods=['GET'])
def pain_cloud_combined_page():
    return render_template('pain_cloud_combined.html')

@app.route('/pain-cloud-realtime', methods=['POST'])
def pain_cloud_realtime_api():
    data = request.get_json()
    if not data or 'keyword' not in data:
        return jsonify({'error': 'Keyword is required'}), 400
        
    keyword = data['keyword']
    
    def is_complaint_post(title, body):
        # Simple heuristic to identify complaint posts
        complaint_indicators = [
            'problem', 'issue', 'error', 'bug', 'fail', 'broken',
            'annoying', 'frustrated', 'hate', 'terrible', 'awful',
            'difficult', 'hard', 'complicated', 'confusing'
        ]
        
        text = (title + ' ' + body).lower()
        return any(indicator in text for indicator in complaint_indicators)
    
    def fetch_subreddit(subreddit):
        try:
            posts = reddit.subreddit(subreddit).search(keyword, limit=20, sort='new')
            results = []
            for post in posts:
                if is_complaint_post(post.title, post.selftext):
                    results.append({
                        'title': post.title,
                        'text': post.selftext,
                        'score': post.score,
                        'url': post.url,
                        'created': datetime.utcfromtimestamp(post.created_utc).isoformat() if post.created_utc else "",
                        'subreddit': subreddit
                    })
            return results
        except Exception as e:
            print(f"Error fetching from {subreddit}: {e}")
            return []
    
    # Fetch from multiple subreddits
    subreddits = ['startups', 'entrepreneur', 'smallbusiness', 'business']
    all_posts = []
    
    for subreddit in subreddits:
        posts = fetch_subreddit(subreddit)
        all_posts.extend(posts)
    
    # Sort by creation date
    all_posts.sort(key=lambda x: x['created'], reverse=True)
    
    # Analyze posts for pain points
    pain_points = []
    for post in all_posts:
        prompt = f"""
        Analyze this post for pain points and problems:
        
        Title: {post['title']}
        Text: {post['text']}
        
        Extract specific pain points and problems that could be solved by a startup.
        Format as a list of problems, each with:
        - Problem description
        - Severity (1-10)
        - Affected users
        - Potential impact
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            analysis = response.text.strip()
            pain_points.append({
                'post': post,
                'analysis': analysis
            })
        except Exception as e:
            print(f"Error analyzing post: {e}")
            continue
    
    return jsonify({
        'posts': all_posts,
        'pain_points': pain_points
    })

if __name__ == '__main__':
    app.run(debug=True)