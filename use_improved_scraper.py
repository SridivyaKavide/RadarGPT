import os
import sys

def update_app_py():
    """Update app.py to use the improved ComplaintsBoard scraper"""
    
    # Read the app.py file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a backup
    with open('app.py.scraper_backup', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Import the improved scraper
    import_code = """
# Import improved ComplaintsBoard scraper
from improved_complaintsboard import improved_complaintsboard_scraper
"""
    
    # Find where to insert the import
    import_position = content.find("# --- Diskcache persistent cache ---")
    if import_position > 0:
        content = content[:import_position] + import_code + content[import_position:]
    
    # Find and replace the complaints_job function in multi_search
    import re
    pattern = r'def complaints_job\(\):\s+try:.*?sources\["ComplaintsBoard"\] = \[\{"title": c\["title"\], "url": c\["url"\], "text": ""\} for c in results\]'
    
    replacement = """def complaints_job():
            try:
                # Use the improved scraper with more pages
                results = improved_complaintsboard_scraper(keyword, max_pages=10)
                print(f"ComplaintsBoard found {len(results)} results")
                sources["ComplaintsBoard"] = [{"title": c["title"], "url": c["url"], "text": ""} for c in results]"""
    
    fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Updated app.py to use the improved ComplaintsBoard scraper")
    return True

if __name__ == "__main__":
    update_app_py()
    print("Now run the app with: python app.py")