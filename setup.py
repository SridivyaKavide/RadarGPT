import os
import sys
import subprocess
import shutil

def setup_painradar():
    """Set up the PainRadar application with all new features"""
    print("Setting up PainRadar with all new features...")
    
    # Create necessary directories
    os.makedirs('instance', exist_ok=True)
    os.makedirs('radargpt_cache', exist_ok=True)
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Creating .env file...")
        with open('.env', 'w') as f:
            f.write("""GOOGLE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=

# Twitter API keys (leave empty if not available)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# Integration API keys (leave empty if not available)
JIRA_API_KEY=
JIRA_DOMAIN=
JIRA_EMAIL=
TRELLO_API_KEY=
TRELLO_TOKEN=
SLACK_WEBHOOK_URL=
NOTION_API_KEY=

# LinkedIn settings
LINKEDIN_ENABLED=false
""")
        print("Please edit the .env file with your API keys")
    
    # Create database
    print("Initializing database...")
    try:
        subprocess.check_call([sys.executable, "run_full.py", "--init-db"])
    except:
        print("Database initialization will be done when you run the application")
    
    print("\nSetup complete!")
    print("To run the application:")
    print("1. Make sure you've added your API keys to the .env file")
    print("2. Run: python run_full.py")
    print("3. Access the application at http://localhost:5000")

if __name__ == "__main__":
    setup_painradar()