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
from app import app, multi_source_search

# Import the fixed scraper
from fixed_complaintsboard import get_complaintsboard_results

# Patch the multi_source_search function to use the fixed scraper
def patched_multi_source_search(keyword):
    results = multi_source_search(keyword)
    # Replace the complaintsboard results with results from the fixed scraper
    results['complaintsboard'] = get_complaintsboard_results(keyword)
    return results

# Monkey patch the function in the app module
import app as app_module
app_module.multi_source_search = patched_multi_source_search

# Import the routes
from app_routes_fixed import bp

# Register the blueprint with the app
app.register_blueprint(bp)

# Run the enhanced app
if __name__ == "__main__":
    print("Starting PainRadar with fixed ComplaintsBoard scraper...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True)