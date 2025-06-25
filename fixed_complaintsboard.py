from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time
import re
from diskcache import Cache

# Use the cache from the main app
cache = Cache("radargpt_cache")

def scrape_complaintsboard_fixed(keyword, max_pages=20):
    """
    Improved version of scrape_complaintsboard_full_text that uses webdriver_manager
    to automatically download and manage the ChromeDriver.
    """
    cache_key = f"complaintsboard_{keyword}_{max_pages}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use webdriver_manager to handle driver installation
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
        driver.get(search_url)
        print(f"Searching ComplaintsBoard for: {keyword}")
        
        try:
            # Wait for search results to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text"))
            )
        except TimeoutException:
            print("No results found or page timed out")
            cache.set(cache_key, [], expire=3600)
            return []

        results = []
        page = 1
        seen = set()
        
        while page <= max_pages:
            print(f"Scraping page {page} of ComplaintsBoard results")
            
            # Scroll down to load more content
            for _ in range(5):
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(1)
            
            # Parse the page
            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("span.search__item-text")
            print(f"Found {len(items)} items on page {page}")
            
            for item in items:
                parent_a = item.find_parent("a", href=True)
                if parent_a:
                    href = parent_a['href']
                    m = re.match(r"(/[^#]+)#(c\\d+)", href)
                    if m:
                        page_url = "https://www.complaintsboard.com" + m.group(1)
                        complaint_id = m.group(2)
                        key = (page_url, complaint_id)
                        if key not in seen:
                            results.append({
                                "title": item.text.strip(),
                                "url": f"{page_url}#{complaint_id}",
                                "text": ""
                            })
                            seen.add(key)
            
            # Try to go to next page
            try:
                next_button = driver.find_element(By.XPATH, "//a[contains(., 'Next')]")
                if next_button.is_enabled():
                    next_button.click()
                    page += 1
                    time.sleep(2)
                else:
                    print("No more pages available")
                    break
            except Exception as e:
                print(f"Error navigating to next page: {e}")
                break
        
        print(f"Total results found: {len(results)}")
        cache.set(cache_key, results, expire=3600)
        return results
    
    finally:
        driver.quit()

# Function to replace the original in app.py
def get_complaintsboard_results(keyword):
    """
    Wrapper function to call the fixed scraper
    """
    return scrape_complaintsboard_fixed(keyword)