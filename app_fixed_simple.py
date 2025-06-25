import os
import re
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
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

# --- Load environment variables ---
load_dotenv()

# --- Gemini setup ---
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# --- Reddit (PRAW) setup ---
import praw
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# --- Diskcache persistent cache ---
from diskcache import Cache
cache = Cache("radargpt_cache")

app = Flask(__name__)
CORS(app)

# --- Database and Login setup ---
app.config['SECRET_KEY'] = 'f3bce3d9a4b21e3d78d0f6a1c7eaf5a914ea7d1b2cfc9e4d8a237f6b5e8d4c13'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('POSTGRES_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
    
class QueryChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# --- Main route ---
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('home')
            return redirect(next_page)
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('User already exists')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Starting PainRadar with simplified app...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True)