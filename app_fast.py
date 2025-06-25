#!/usr/bin/env python3
"""
Fast version of the Flask app with optimized Ollama settings for speed
"""

import os
import re
import time
import json
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
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

# --- Fast Ollama setup for speed ---
from langchain_ollama import OllamaLLM
llm = OllamaLLM(
    model="mistral:7b-instruct-q4_0",
    temperature=0.7,
    num_ctx=2048,  # Smaller context for speed
    num_thread=8,  # More threads for parallel processing
    repeat_penalty=1.1,
    top_k=20,  # Lower for faster generation
    top_p=0.9
)

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
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models (same as original) ---
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
    result = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chats = db.relationship('QueryChat', backref='query', lazy=True)
    vertical = db.Column(db.String(50), nullable=True)

class QueryChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())

class VerticalChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vertical = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    text = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# --- Fast Data Source Functions ---
def get_reddit_posts_with_replies(keyword, start=0, batch_size=3, max_posts=3, subreddit="all"):
    """Reduced batch size for faster processing"""
    cache_key = f"reddit_{keyword}_{start}_{batch_size}_{max_posts}_{subreddit}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    results = []
    submissions = reddit.subreddit(subreddit).search(keyword, limit=None if start or batch_size else max_posts)
    for _ in range(start):
        try:
            next(submissions)
        except StopIteration:
            break
    for _ in range(batch_size if batch_size else max_posts):
        try:
            submission = next(submissions)
            submission.comments.replace_more(limit=0)
            comments = [c.body or "" for c in submission.comments.list()[:5]]  # Reduced comments
            results.append({
                "title": submission.title or "",
                "selftext": submission.selftext or "",
                "url": submission.url or "",
                "comments": comments
            })
        except StopIteration:
            break
    cache.set(cache_key, results, expire=3600)
    return results

def fast_summarize_post_and_replies(post):
    """Fast summarization with shorter prompts"""
    prompt = f"""<s>[INST] Analyze this Reddit post and extract key problems:

Title: {post['title']}
Body: {post['selftext']}
Comments: {chr(10).join(post['comments'][:3])}

List 3 main problems in bullet points. [/INST]"""
    try:
        response = llm.invoke(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

def fast_generate_startup_ideas(summary):
    """Fast startup idea generation"""
    prompt = f"""<s>[INST] Based on this problem summary, suggest 2 startup ideas:

{summary}

For each idea provide:
- Problem
- Solution
- Target users
- Score (1-10)

Keep it concise. [/INST]"""
    try:
        response = llm.invoke(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

# --- Fast Multi-Source Search ---
def fast_multi_source_search(keyword):
    """Optimized search with reduced data"""
    results = {}
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            "reddit": executor.submit(get_reddit_posts_with_replies, keyword, max_posts=3),
            "stackoverflow": executor.submit(search_stackoverflow, keyword, max_pages=2),
            "complaintsboard": executor.submit(scrape_complaintsboard_full_text, keyword, max_pages=10),
            "producthunt": executor.submit(scrape_producthunt_fixed, keyword)
        }
        for name, future in futures.items():
            try:
                timeout = 10 if name == "complaintsboard" else 5
                results[name] = future.result(timeout=timeout)
                print(f"✅ {name}: {len(results[name])} results")
            except TimeoutError:
                print(f"⏰ Timeout: {name}")
                results[name] = []
            except Exception as e:
                print(f"❌ Error {name}: {str(e)}")
                results[name] = []
    return results

# --- Fast Summarization ---
def fast_summarize_with_citations(content_list, prompt_prefix):
    """Fast summarization with reduced content"""
    # Limit content for faster processing
    limited_content = content_list[:10]  # Only first 10 items
    
    sources_str = ""
    for idx, item in enumerate(limited_content, 1):
        sources_str += f"[{idx}] {item['title']}\n"
    
    content_str = "\n\n".join([f"{item['title']}\n{item.get('text','')[:200]}" for item in limited_content])
    
    prompt = f"""<s>[INST] {prompt_prefix}

Analyze this content and provide insights in 3-4 bullet points:

Sources:
{sources_str}

Content:
{content_str}

Provide a concise, structured response. [/INST]"""
    
    try:
        response = llm.invoke(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

# --- Fast Mode Prompts ---
FAST_MODE_PROMPTS = {
    "future_pain": """
You're a product strategist. Analyze the content and provide:
1. Top 3 emerging problems
2. 2 startup opportunities
3. Key trends

Keep it concise and structured.
""",
    "unspoken": """
You're a UX expert. Identify:
1. Hidden user problems
2. Emotional pain points
3. Product opportunities

Be specific and actionable.
""",
    "zero_to_one": """
You're a startup founder. Find:
1. Unmet needs
2. Disruptive opportunities
3. Validation scores

Focus on innovation.
"""
}

# --- Routes ---
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/radargpt', methods=['POST'])
@login_required
def radargpt_api():
    data = request.json
    keyword = data.get('keyword')
    mode = data.get('mode', 'future_pain')
    
    if not keyword:
        return jsonify({"error": "Keyword required"}), 400
    
    cache_key = f"fast_radargpt_{keyword}_{mode}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({
            "summary": cached_result["summary"],
            "sources": cached_result["sources"],
            "cached": True
        })
    
    try:
        # Fast search with reduced timeout
        search_results = fast_multi_source_search(keyword)
        all_content = []
        for v in search_results.values():
            if isinstance(v, list):
                all_content.extend(v[:5])  # Limit content
            elif isinstance(v, dict):
                all_content.append(v)
        
        prompt_prefix = FAST_MODE_PROMPTS.get(mode, FAST_MODE_PROMPTS['future_pain'])
        summary = fast_summarize_with_citations(all_content, prompt_prefix)
        
        # Cache result
        cache.set(cache_key, {
            "summary": summary,
            "sources": search_results
        }, expire=1800)  # 30 minutes
        
        return jsonify({
            "summary": summary,
            "sources": search_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 