import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from diskcache import Cache

# Use the cache from the main app
cache = Cache("radargpt_cache")

def scrape_producthunt_fixed(keyword, max_pages=3, max_products=30):
    """
    Improved version of scrape_producthunt_products that uses webdriver_manager
    to automatically download and manage the ChromeDriver.
    """
    cache_key = f"producthunt_{keyword}_{max_pages}_{max_products}"
    # Always clear the cache to ensure fresh results
    cache.delete(cache_key)
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
        search_url = f"https://www.producthunt.com/search?q={keyword.replace(' ', '+')}"
        driver.get(search_url)
        print(f"Searching ProductHunt for: {keyword}")
        
        products = []
        current_page = 1
        
        while current_page <= max_pages and len(products) < max_products:
            try:
                # Wait for products to load - try multiple selectors
                selectors = [
                    "div.text-16.font-semibold.text-dark-gray[data-sentry-component='LegacyText']",  # New specific selector
                    "div.styles_title__jWi91",  # Old selector
                    "div.text-16.font-semibold.text-dark-gray",  # General selector
                    "h3.color-darker-grey"  # Another possible selector
                ]
                
                found = False
                for selector in selectors:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        print(f"Found products using selector: {selector}")
                        found = True
                        break
                    except Exception:
                        continue
                
                if not found:
                    print("No product elements found on page")
                    break
                    
            except Exception as e:
                print(f"Error waiting for page to load: {e}")
                break
                
            # Scroll down to load more content and wait longer
            for _ in range(5):
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(2)
            
            # Parse the page
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Try different selectors for product cards
            product_cards = []
            for selector in selectors:
                product_cards = soup.select(selector)
                if product_cards:
                    break
            
            print(f"Found {len(product_cards)} products on page {current_page}")
            
            for card in product_cards:
                # Extract product information based on the structure
                title = card.get_text(strip=True)
                
                # Find description - look in nearby elements
                desc_div = None
                parent = card.parent
                if parent:
                    # Try to find description using the specific selector
                    desc_candidates = parent.select("div.text-14.font-normal.text-light-gray[data-sentry-component='LegacyText']")
                    if not desc_candidates:
                        # Fallback to more general selectors
                        desc_candidates = parent.select("div.text-14, div.styles_tagline__8bh7C, p")
                    if desc_candidates:
                        desc_div = desc_candidates[0]
                
                desc = desc_div.get_text(strip=True) if desc_div else ""
                
                # Find URL
                url = ""
                parent_a = card.find_parent("a", href=True)
                if parent_a and 'href' in parent_a.attrs:
                    url = "https://www.producthunt.com" + parent_a['href']
                
                # Create product object
                prod = {
                    "title": title,
                    "description": desc,
                    "url": url,
                    "text": desc
                }
                
                # Add to results if not already present
                if prod not in products and title:
                    products.append(prod)
                
                if len(products) >= max_products:
                    break
            
            # Try to go to next page
            try:
                next_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Next')]")
                if next_buttons and next_buttons[0].is_enabled():
                    next_buttons[0].click()
                    current_page += 1
                    time.sleep(2)
                else:
                    print("No more pages available")
                    break
            except Exception as e:
                print(f"Error navigating to next page: {e}")
                break
        
        print(f"Total products found: {len(products)}")
        cache.set(cache_key, products, expire=3600)
        return products
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # Test the function
    keyword = "project management"
    results = scrape_producthunt_fixed(keyword)
    print(f"Found {len(results)} products for '{keyword}'")
    for i, product in enumerate(results[:5], 1):
        print(f"{i}. {product['title']} - {product['url']}")