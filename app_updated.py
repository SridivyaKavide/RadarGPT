import os
import re
import time
import json
import random
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import logging
from collections import Counter
import threading
from functools import lru_cache

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
from scrapers import ScraperManager

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

# Initialize scraper manager
scraper_manager = ScraperManager()

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
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chats = db.relationship('QueryChat', backref='query', lazy=True)
    vertical = db.Column(db.String(50), nullable=True)  # New column for vertical insights
    
class QueryChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
class VerticalChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vertical = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(200), nullable=False)  # was 'query'
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text, nullable=True)  # Stores the insights context
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# Cache for storing results
cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 3600  # 1 hour

@lru_cache(maxsize=100)
def get_cached_data(persona, industry, mode):
    """Get cached data with thread safety"""
    with cache_lock:
        cache_key = f"{persona}_{industry}_{mode}"
        if cache_key in cache:
            timestamp, data = cache[cache_key]
            if time.time() - timestamp < CACHE_EXPIRY:
                return data
    return None

def set_cached_data(persona, industry, mode, data):
    """Set cached data with thread safety"""
    with cache_lock:
        cache_key = f"{persona}_{industry}_{mode}"
        cache[cache_key] = (time.time(), data)

@app.route('/pain-cloud-realtime', methods=['GET'])
def pain_cloud_realtime_page():
    return render_template('pain_cloud_realtime.html')

@app.route('/pain-cloud-realtime', methods=['POST'])
def pain_cloud_realtime_api():
    data = request.get_json()
    persona = data.get('persona')
    industry = data.get('industry')
    mode = data.get('mode', 'real')

    if not persona or not industry:
        return jsonify({'error': 'Missing persona or industry'}), 400

    # Check cache first
    cached_data = get_cached_data(persona, industry, mode)
    if cached_data:
        return jsonify(cached_data)

    sources = PERSONA_INDUSTRY_SOURCES.get((persona, industry)) or PERSONA_SOURCES.get(persona, [])

    def is_complaint_post(title, body):
        complaint_keywords = [
            "hate", "struggle", "issue", "problem", "bug", "error", "glitch", "broken", "crash", "lag",
            "not working", "doesn't work", "stopped working", "won't load", "can't log in", "crashes", "fails", "failure",
            "unable to", "doesn't respond", "hangs", "freeze", "timeout", "corrupted", "inaccessible",
            "annoying", "frustrating", "confusing", "complicated", "infuriating", "maddening", "disappointed", "slow",
            "bloated", "tedious", "pointless", "missing feature", "churn", "costs too much", "pricing problem", "overpriced",
            "hard to scale", "lack of support", "team hates", "reviews are bad", "burnout", "micromanage"
        ]
        combined = f"{title.lower()} {body.lower()}"
        return any(kw in combined for kw in complaint_keywords)

    # Fetch posts concurrently with timeout
    all_posts = []
    reddit_sources = [s[2:] for s in sources if s.startswith('r/')]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for subreddit in reddit_sources:
            futures.append(executor.submit(fetch_subreddit_posts, subreddit))
        
        for future in as_completed(futures, timeout=15):  # 15 second timeout
            try:
                posts = future.result()
                all_posts.extend(posts)
            except Exception as e:
                print(f"[Reddit error]: {e}")

    if not all_posts:
        return jsonify({'error': 'No relevant complaint posts found.'})

    def score(post):
        return post['score'] - 0.5 * ((time.time() - post['created_utc']) / 86400)

    top_posts = sorted(all_posts, key=score, reverse=True)[:50]

    # Process posts in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Process pain points
        pain_points_future = executor.submit(process_pain_points, top_posts, persona, industry)
        # Process trends
        trends_future = executor.submit(process_trends, top_posts)
        
        pain_points = pain_points_future.result()
        trending_keywords = trends_future.result()

    # Prepare response data
    response_data = {
        'pain_points': pain_points,
        'trending_keywords': trending_keywords,
        'groups': {
            'rising': [p for p in pain_points if p.get('trend_direction') == 'rising'],
            'fading': [p for p in pain_points if p.get('trend_direction') == 'fading'],
            'flat': [p for p in pain_points if p.get('trend_direction') == 'flat']
        },
        'raw_posts': top_posts
    }

    # Cache the response
    set_cached_data(persona, industry, mode, response_data)
    
    return jsonify(response_data)

def fetch_subreddit_posts(subreddit):
    """Fetch posts from a subreddit with error handling"""
    try:
        posts = list(reddit.subreddit(subreddit).new(limit=100))
        return [{
            'title': post.title or '',
            'selftext': post.selftext or '',
            'score': post.score,
            'url': f"https://reddit.com{post.permalink}",
            'source': f"r/{subreddit}",
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(post.created_utc)),
            'created_utc': post.created_utc
        } for post in posts if is_complaint_post(post.title, post.selftext)]
    except Exception as e:
        print(f"[Reddit error] r/{subreddit}: {e}")
        return []

def process_pain_points(posts, persona, industry):
    """Process pain points in parallel"""
    pain_points = []
    current_date = datetime.utcnow().strftime('%B %d, %Y')
    
    for post in posts:
        text = f"{post['title']} {post['selftext']}"
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = set([...])  # Your stopwords list
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        freq = Counter(filtered)
        top_keywords = freq.most_common(3)
        keywords = [{'word': k, 'score': min(10, max(3, v))} for k, v in top_keywords]
        
        pain_point = {
            'summary': post['title'][:100],
            'reason': 'Fallback: complaint matched keyword list.',
            'market_gap': '',
            'trend': '',
            'severity': 7,
            'title': post['title'],
            'excerpt': post['selftext'][:180],
            'upvotes': post['score'],
            'source': post['source'],
            'timestamp': post['timestamp'],
            'url': post['url'],
            'persona': persona,
            'tag': 'VC-worthy',
            'keywords': keywords
        }
        
        # Process trend data
        num_bins = 15
        now = time.time()
        bin_edges = [now - (num_bins - i) * 7 * 86400 for i in range(num_bins + 1)]
        bin_counts = [0] * num_bins
        
        for i in range(num_bins):
            if bin_edges[i] <= post['created_utc'] < bin_edges[i + 1]:
                bin_counts[i] += 1
                break
        
        pain_point['sparkline_data'] = bin_counts or [0] * num_bins
        delta = bin_counts[-1] - bin_counts[0] if bin_counts else 0
        pain_point['trend_direction'] = 'rising' if delta > 2 else 'fading' if delta < -2 else 'flat'
        
        pain_points.append(pain_point)
    
    return pain_points

def process_trends(posts):
    """Process trends in parallel"""
    all_keywords = []
    for post in posts:
        text = f"{post['title']} {post['selftext']}"
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = set([...])  # Your stopwords list
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        all_keywords.extend(filtered)
    
    return [kw for kw, _ in Counter(all_keywords).most_common(10)]

# ... rest of the existing routes and functions ... 