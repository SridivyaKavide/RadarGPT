import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create necessary directories
os.makedirs('instance', exist_ok=True)
os.makedirs('radargpt_cache', exist_ok=True)

# Import the fixed scrapers
from fix_producthunt import scrape_producthunt_fixed

# Import the original app
sys.path.insert(0, os.path.abspath('.'))
from app import app, multi_source_search, scrape_complaintsboard_full_text

# Patch the multi_source_search function to use the fixed scrapers
def patched_multi_source_search(keyword):
    results = {}
    import time
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        from app import get_reddit_posts_with_replies, search_stackoverflow
        
        futures = {
            "reddit": executor.submit(get_reddit_posts_with_replies, keyword),
            "stackoverflow": executor.submit(search_stackoverflow, keyword),
            "complaintsboard": executor.submit(scrape_complaintsboard_full_text, keyword),
            "producthunt": executor.submit(scrape_producthunt_fixed, keyword)
        }
        
        for name, future in futures.items():
            try:
                # Increase timeout for scrapers
                if name in ["complaintsboard", "producthunt"]:
                    timeout = 60  # Give more time for scraping
                else:
                    timeout = max(5, 30 - (time.time() - start_time))
                    
                results[name] = future.result(timeout=timeout)
                print(f"Successfully retrieved {len(results[name])} results from {name}")
            except TimeoutError:
                print(f"Timeout error for {name}")
                results[name] = []
            except Exception as e:
                print(f"Error for {name}: {str(e)}")
                results[name] = []
    
    return results

# Monkey patch the function in the app module
import app as app_module
app_module.multi_source_search = patched_multi_source_search

# Run the enhanced app
if __name__ == "__main__":
    print("Starting PainRadar with all fixed scrapers...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True)