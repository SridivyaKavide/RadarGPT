import os

def fix_multi_search():
    """Fix the multi_search function to use all ProductHunt results"""
    
    # Read the app.py file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a backup
    with open('app.py.multi_search_backup', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Remove the duplicate ProductHunt scraper function
    import re
    pattern = r'# --- Improved ProductHunt scraper ---\r?\ndef scrape_producthunt_products\(keyword, max_pages=3, max_products=30\):.*?f"The easiest way to handle {keyword}",\s+'
    
    fixed_content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Find the multi_search function
    pattern = r'def multi_search\(\):\s+try:.*?all_posts = \[\]\s+for src in ALL_SOURCES:\s+all_posts\.extend\(sources\[src\]\)'
    
    match = re.search(pattern, fixed_content, re.DOTALL)
    if match:
        # Get the matched text
        matched_text = match.group(0)
        
        # Add debug print statements
        modified_text = matched_text.replace(
            'all_posts = []\n        for src in ALL_SOURCES:',
            'all_posts = []\n        print("Sources data:", {src: len(data) for src, data in sources.items()})\n        for src in ALL_SOURCES:'
        )
        
        # Replace in the content
        fixed_content = fixed_content.replace(matched_text, modified_text)
        
        # Write the fixed content
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("Fixed multi_search function and removed duplicate ProductHunt scraper")
        return True
    else:
        print("Could not find the multi_search function in app.py")
        return False

if __name__ == "__main__":
    fix_multi_search()
    print("Now run the app with: python app.py")