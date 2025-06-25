import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create necessary directories
os.makedirs('instance', exist_ok=True)
os.makedirs('radargpt_cache', exist_ok=True)

# Import the original app
sys.path.insert(0, os.path.abspath('.'))
from app import app

# Import the routes
from app_routes import bp

# Register the blueprint with the app
app.register_blueprint(bp)

# Run the enhanced app
if __name__ == "__main__":
    print("Starting PainRadar with all new features...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True)