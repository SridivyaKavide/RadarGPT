import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create necessary directories
os.makedirs('instance', exist_ok=True)
os.makedirs('radargpt_cache', exist_ok=True)

# Make sure all required modules are available
required_modules = [
    'flask', 'flask_cors', 'flask_sqlalchemy', 'flask_login',
    'werkzeug', 'requests', 'bs4', 'praw', 'diskcache',
    'google.generativeai', 'tweepy', 'selenium', 'pandas',
    'numpy', 'matplotlib', 'textblob'
]

missing_modules = []
for module in required_modules:
    try:
        __import__(module.split('.')[0])
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    print("Missing required modules. Please install them with:")
    print(f"pip install {' '.join(missing_modules)}")
    sys.exit(1)

# Import the original app
sys.path.insert(0, os.path.abspath('.'))
from app import app

# Import the models
from models import db

# Initialize the database with the app
db.init_app(app)

# Import the integration function
from app_integration import integrate_new_features

# Integrate new features
app = integrate_new_features(app)

# Run the enhanced app
if __name__ == "__main__":
    print("Starting PainRadar with all new features...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True)