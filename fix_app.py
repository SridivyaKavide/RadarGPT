import re

def fix_syntax_error():
    # Read the app.py file
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Fix the syntax error in the try-except block
    pattern = r'try:\s+# Try multiple CSS selectors to find complaint items.*?except TimeoutException:\s+print\(f"No complaint elements found for keyword: {keyword}"\)\s+cache\.set\(cache_key, \[\], expire=3600\)\s+return \[\]\s+\s+results = \[\]'
    replacement = r'try:\n            # Try multiple CSS selectors to find complaint items\n            try:\n                WebDriverWait(driver, 30).until(\n                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text"))\n                )\n                print(f"Found search__item-text elements for keyword: {keyword}")\n            except TimeoutException:\n                try:\n                    WebDriverWait(driver, 10).until(\n                        EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-item"))\n                    )\n                    print(f"Found complaint-item elements for keyword: {keyword}")\n                except TimeoutException:\n                    print(f"No complaint elements found for keyword: {keyword}")\n                    cache.set(cache_key, [], expire=3600)\n                    return []\n        except Exception as e:\n            print(f"Error during ComplaintsBoard search: {e}")\n            cache.set(cache_key, [], expire=3600)\n            return []\n            \n        results = []'
    
    fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content back to app.py
    with open('app.py', 'w') as f:
        f.write(fixed_content)
    
    print("Syntax error fixed in app.py")

if __name__ == "__main__":
    fix_syntax_error()
    print("Now you can run 'python app.py'")