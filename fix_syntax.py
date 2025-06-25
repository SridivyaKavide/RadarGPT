import os
import re

def fix_app_py():
    # Read the original file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the problematic section
    pattern = r'try:\s+# Try multiple CSS selectors to find complaint items.*?except TimeoutException:\s+.*?cache\.set\(cache_key, \[\], expire=3600\)\s+return \[\]\s+\s+results = \[\]'
    
    # Check if the pattern exists
    if re.search(pattern, content, re.DOTALL):
        # Create a backup
        with open('app.py.bak', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Created backup at app.py.bak")
        
        # Fix the syntax error by adding a proper exception handler
        fixed_content = re.sub(
            pattern,
            '''try:
            # Try multiple CSS selectors to find complaint items
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text"))
                )
                print(f"Found search__item-text elements for keyword: {keyword}")
            except TimeoutException:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-item"))
                    )
                    print(f"Found complaint-item elements for keyword: {keyword}")
                except TimeoutException:
                    print(f"No complaint elements found for keyword: {keyword}")
                    cache.set(cache_key, [], expire=3600)
                    return []
        except Exception as e:
            print(f"Error during ComplaintsBoard search: {e}")
            cache.set(cache_key, [], expire=3600)
            return []
            
        results = []''',
            content,
            flags=re.DOTALL
        )
        
        # Write the fixed content
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print("Fixed syntax error in app.py")
        return True
    else:
        print("Could not find the problematic section in app.py")
        return False

if __name__ == "__main__":
    if fix_app_py():
        print("You can now run 'python app.py'")
    else:
        print("Manual fix required. Please check app.py for syntax errors.")