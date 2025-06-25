#!/usr/bin/env python3
"""
Production-ready Flask app with OpenRouter DeepSeek integration
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from diskcache import Cache

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Production configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'production-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///production.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-coder-33b-instruct"

# Rate limiting
RATE_LIMIT_PER_MINUTE = 10
RATE_LIMIT_PER_HOUR = 100

# Initialize components
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Cache for responses and rate limiting
cache = Cache("production_cache")

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    api_calls_today = db.Column(db.Integer, default=0)
    last_api_reset = db.Column(db.Date, default=datetime.now().date)

class SearchQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    result = db.Column(db.Text, nullable=True)
    processing_time = db.Column(db.Float, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rate limiting decorator
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        
        user_id = current_user.id
        now = datetime.now()
        
        # Check daily limit
        if current_user.last_api_reset != now.date():
            current_user.api_calls_today = 0
            current_user.last_api_reset = now.date()
            db.session.commit()
        
        if current_user.api_calls_today >= RATE_LIMIT_PER_HOUR:
            return jsonify({"error": "Daily API limit reached"}), 429
        
        # Check minute limit
        minute_key = f"rate_limit:{user_id}:{now.strftime('%Y%m%d%H%M')}"
        current_minute_calls = cache.get(minute_key, 0)
        if current_minute_calls >= RATE_LIMIT_PER_MINUTE:
            return jsonify({"error": "Rate limit exceeded"}), 429
        cache.set(minute_key, current_minute_calls + 1, expire=60)
        
        # Update daily count
        current_user.api_calls_today += 1
        db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function

# OpenRouter API client
class OpenRouterClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://radargpt.com",
            "X-Title": "RadarGPT"
        }
    
    def generate_response(self, prompt, model=DEEPSEEK_MODEL, max_tokens=1000):
        """Generate response using OpenRouter API"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert market analyst and product strategist. Provide clear, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"OpenRouter API Error: {e}")
            return None

# Initialize OpenRouter client
if OPENROUTER_API_KEY:
    openrouter_client = OpenRouterClient(OPENROUTER_API_KEY, OPENROUTER_BASE_URL)
    USE_OPENROUTER = True
else:
    USE_OPENROUTER = False
    print("⚠️ OpenRouter API key not found, using fallback mode")

# Fallback response generator
def generate_fallback_response(keyword, mode="future_pain"):
    """Generate response using pre-defined templates"""
    templates = {
        "future_pain": {
            "problems": [
                f"Complex integration challenges with {keyword} systems",
                f"User adoption barriers for {keyword} solutions",
                f"Data security concerns in {keyword} environments"
            ],
            "opportunities": [
                f"AI-powered {keyword} automation solutions",
                f"Unified {keyword} platform integrations",
                f"Enhanced {keyword} user experience tools"
            ],
            "trends": [
                f"Rapid {keyword} cloud migration adoption",
                f"AI/ML integration in {keyword} workflows",
                f"Remote work {keyword} tool proliferation"
            ]
        }
    }
    
    template = templates.get(mode, templates["future_pain"])
    
    return f"""
## 📊 Market Analysis: {keyword.title()}

### 🔥 Key Problems
{chr(10).join([f"- {p}" for p in template['problems']])}

### 💡 Opportunities
{chr(10).join([f"- {o}" for p in template['opportunities']])}

### 📈 Trends
{chr(10).join([f"- {t}" for t in template['trends']])}

### 🎯 Recommendations
1. **Immediate**: Focus on integration solutions
2. **Short-term**: Develop automation capabilities
3. **Long-term**: Build AI-powered features

---
*Generated with fallback analysis*
"""

# Enhanced prompt generator
def generate_analysis_prompt(keyword, mode="future_pain"):
    """Generate optimized prompt for OpenRouter"""
    prompts = {
        "future_pain": f"""Analyze the market for "{keyword}" and provide:

1. **Top 3 Emerging Problems** (with severity scores 1-10)
2. **Top 3 Market Opportunities** (with market size estimates)
3. **Key Trends** (with growth projections)
4. **Startup Recommendations** (with validation scores)

Focus on actionable insights for entrepreneurs and product managers.
Format with clear headings and bullet points.""",
        
        "unspoken": f"""Identify hidden, unspoken problems in the "{keyword}" space:

1. **Unmet User Needs** (problems users don't explicitly state)
2. **Workflow Inefficiencies** (silent pain points)
3. **UX Gaps** (friction points in user experience)
4. **Opportunity Areas** (where solutions are missing)

Provide specific, actionable insights.""",
        
        "zero_to_one": f"""Generate disruptive, zero-to-one opportunities for "{keyword}":

1. **Novel Market Gaps** (completely new categories)
2. **Disruptive Technologies** (paradigm shifts)
3. **Unaddressed Segments** (ignored user groups)
4. **Revolutionary Approaches** (new ways of solving problems)

Focus on breakthrough innovations, not incremental improvements."""
    }
    
    return prompts.get(mode, prompts["future_pain"])

# Routes
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/radargpt', methods=['GET', 'POST'])
@login_required
@rate_limit
def radargpt():
    if request.method == 'POST':
        data = request.json
        keyword = data.get('keyword', '')
        mode = data.get('mode', 'future_pain')
        
        if not keyword:
            return jsonify({"error": "Keyword required"}), 400
        
        # Check cache first
        cache_key = f"analysis:{keyword}:{mode}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return jsonify({
                "summary": cached_result["summary"],
                "processing_time": cached_result["processing_time"],
                "cached": True,
                "model_used": cached_result["model_used"]
            })
        
        start_time = time.time()
        
        # Try OpenRouter first
        if USE_OPENROUTER:
            prompt = generate_analysis_prompt(keyword, mode)
            result = openrouter_client.generate_response(prompt)
            model_used = "deepseek-coder-33b"
        else:
            result = None
            model_used = "fallback"
        
        # Fallback if OpenRouter fails
        if not result:
            result = generate_fallback_response(keyword, mode)
            model_used = "fallback"
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Cache the result
        cache.set(cache_key, {
            "summary": result,
            "processing_time": processing_time,
            "model_used": model_used
        }, expire=3600)  # Cache for 1 hour
        
        # Save to database
        query = SearchQuery(
            keyword=keyword,
            result=result,
            processing_time=processing_time,
            model_used=model_used,
            user_id=current_user.id
        )
        db.session.add(query)
        db.session.commit()
        
        return jsonify({
            "summary": result,
            "processing_time": f"{processing_time:.2f}s",
            "model_used": model_used,
            "cached": False
        })
    
    return render_template('radarGPT.html')

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

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        "status": "healthy",
        "openrouter_available": USE_OPENROUTER,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/usage')
@login_required
def usage_stats():
    """Get user usage statistics"""
    return jsonify({
        "api_calls_today": current_user.api_calls_today,
        "daily_limit": RATE_LIMIT_PER_HOUR,
        "minute_limit": RATE_LIMIT_PER_MINUTE,
        "last_reset": current_user.last_api_reset.isoformat()
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("🏭 Production RadarGPT starting...")
    print(f"🔑 OpenRouter: {'✅ Available' if USE_OPENROUTER else '❌ Not configured'}")
    print(f"⚡ Rate limit: {RATE_LIMIT_PER_MINUTE}/min, {RATE_LIMIT_PER_HOUR}/day")
    print("🌐 Server: http://localhost:5000")
    
    # Use production WSGI server
    try:
        from waitress import serve
        print("🚀 Using Waitress production server")
        serve(app, host='0.0.0.0', port=5000, threads=4)
    except ImportError:
        print("⚠️ Waitress not available, using Flask development server")
        app.run(debug=False, host='0.0.0.0', port=5000) 