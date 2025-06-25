#!/usr/bin/env python3
"""
Ultra-fast Flask app with instant responses
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from langchain_ollama import OllamaLLM

# Load environment variables
load_dotenv()

# Ultra-fast Ollama setup
llm = OllamaLLM(
    model="mistral:7b-instruct-q4_0",
    temperature=0.7,
    num_ctx=1024,  # Very small context for speed
    num_thread=12,  # Maximum threads
    repeat_penalty=1.0,
    top_k=10,  # Very low for instant generation
    top_p=0.8
)

app = Flask(__name__)
CORS(app)

# Database setup
app.config['SECRET_KEY'] = 'f3bce3d9a4b21e3d78d0f6a1c7eaf5a914ea7d1b2cfc9e4d8a237f6b5e8d4c13'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('POSTGRES_DATABASE_URI', 'sqlite:///instant.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class SearchQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    result = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Instant response templates
INSTANT_RESPONSES = {
    "future_pain": {
        "problems": [
            "Integration complexity with existing systems",
            "User adoption and training challenges", 
            "Data security and compliance concerns",
            "Scalability and performance issues",
            "Cost management and ROI tracking"
        ],
        "opportunities": [
            "AI-powered automation solutions",
            "Unified platform integrations",
            "Enhanced user experience tools",
            "Advanced analytics and insights",
            "Mobile-first applications"
        ],
        "trends": [
            "Cloud migration acceleration",
            "AI/ML integration growth",
            "Remote work tool adoption",
            "Security-first development",
            "API-first architecture"
        ]
    },
    "unspoken": {
        "problems": [
            "Hidden workflow inefficiencies",
            "Unmet user experience needs",
            "Silent feature gaps",
            "Undocumented pain points",
            "Implicit integration needs"
        ],
        "opportunities": [
            "Intuitive UX improvements",
            "Workflow automation tools",
            "Seamless integration solutions",
            "User onboarding enhancements",
            "Proactive problem detection"
        ]
    },
    "zero_to_one": {
        "problems": [
            "Completely new market needs",
            "Unaddressed user segments",
            "Emerging technology gaps",
            "Untapped data opportunities",
            "Novel workflow requirements"
        ],
        "opportunities": [
            "Revolutionary platform solutions",
            "AI-native applications",
            "Cross-platform integrations",
            "Predictive analytics tools",
            "Automated decision systems"
        ]
    }
}

def generate_instant_analysis(keyword, mode="future_pain"):
    """Generate instant analysis using templates + minimal AI"""
    
    # Get template response
    template = INSTANT_RESPONSES.get(mode, INSTANT_RESPONSES["future_pain"])
    
    # Create instant prompt
    prompt = f"""<s>[INST] Analyze "{keyword}" and provide 3 key insights:

1. Main problems
2. Opportunities  
3. Trends

Keep it brief and actionable. [/INST]"""
    
    try:
        # Get AI response (very fast)
        ai_response = llm.invoke(prompt)
        
        # Combine template + AI
        response = f"""
## Analysis for "{keyword}"

### 🔥 Key Problems
{chr(10).join([f"- {p}" for p in template['problems'][:3]])}

### 💡 Opportunities  
{chr(10).join([f"- {o}" for p in template['opportunities'][:3]])}

### 📈 Trends
{chr(10).join([f"- {t}" for t in template['trends'][:3]])}

### 🤖 AI Insights
{ai_response[:200]}...
"""
        return response.strip()
        
    except Exception as e:
        # Fallback to template only
        return f"""
## Analysis for "{keyword}"

### 🔥 Key Problems
{chr(10).join([f"- {p}" for p in template['problems'][:3]])}

### 💡 Opportunities  
{chr(10).join([f"- {o}" for p in template['opportunities'][:3]])}

### 📈 Trends
{chr(10).join([f"- {t}" for t in template['trends'][:3]])}
"""

# Routes
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/radargpt', methods=['GET', 'POST'])
@login_required
def radargpt():
    if request.method == 'POST':
        data = request.json
        keyword = data.get('keyword', '')
        mode = data.get('mode', 'future_pain')
        
        if not keyword:
            return jsonify({"error": "Keyword required"}), 400
        
        # Generate instant response
        start_time = time.time()
        result = generate_instant_analysis(keyword, mode)
        end_time = time.time()
        
        # Save to database
        query = SearchQuery(
            keyword=keyword,
            result=result,
            user_id=current_user.id
        )
        db.session.add(query)
        db.session.commit()
        
        return jsonify({
            "summary": result,
            "processing_time": f"{end_time - start_time:.2f}s",
            "query_id": query.id,
            "instant": True
        })
    
    return render_template('radarGPT.html')

@app.route('/radargpt', methods=['GET'])
@login_required
def radargpt_page():
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

@app.route('/api/instant_analysis', methods=['POST'])
def instant_analysis():
    """Ultra-fast API endpoint"""
    data = request.json
    keyword = data.get('keyword', '')
    mode = data.get('mode', 'future_pain')
    
    if not keyword:
        return jsonify({"error": "Keyword required"}), 400
    
    start_time = time.time()
    result = generate_instant_analysis(keyword, mode)
    end_time = time.time()
    
    return jsonify({
        "summary": result,
        "processing_time": f"{end_time - start_time:.2f}s",
        "instant": True
    })

@app.route('/status_check')
def status_check():
    """Instant status check"""
    keyword = request.args.get('keyword', '')
    if keyword:
        return jsonify({
            "status": "ready",
            "keyword": keyword,
            "instant": True
        })
    return jsonify({"status": "ready", "instant": True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Instant RadarGPT starting on http://localhost:5000")
    print("⚡ Ultra-fast responses with minimal processing")
    app.run(debug=True, host='0.0.0.0', port=5000) 