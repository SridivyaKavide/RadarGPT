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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from diskcache import Cache

# Use the cache from the main app
cache = Cache("radargpt_cache")

def improved_complaintsboard_scraper(keyword, max_pages=3):
    """
    Improved version of scrape_complaintsboard_full_text that better handles pagination
    to extract more results with improved timeout handling.
    """
    cache_key = f"complaintsboard_{keyword}_{max_pages}"
    
    # Check if we have cached results first
    cached_results = cache.get(cache_key)
    if cached_results:
        print(f"Using cached results for '{keyword}'")
        return cached_results
    
    # If no cached results, proceed with scraping
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Add a realistic user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Use webdriver_manager to handle driver installation
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        # Return empty results if driver fails
        return []
    
    try:
        # Set page load timeout to prevent hanging
        # Increase timeout and add retry logic
        max_retries = 2
        timeout_seconds = 40  # Increased from 15
        for attempt in range(max_retries):
            try:
                driver.set_page_load_timeout(timeout_seconds)
                # First try the search page
                search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
                driver.get(search_url)
                print(f"Searching ComplaintsBoard for: {keyword} (attempt {attempt+1})")
                break  # Success
            except TimeoutException:
                print(f"Page load timed out (attempt {attempt+1}), retrying...")
                if attempt == max_retries - 1:
                    print("Page load timed out, returning empty results")
                    return []
        
        results = []
        seen = set()
        
        # Try to find results on the search page with a shorter timeout
        try:
            WebDriverWait(driver, 5).until(  # Reduced timeout from 10 to 5 seconds
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text, .complaint-item"))
            )
            print("Found search results")
            
            # Process the first page
            results.extend(extract_complaints_from_page(driver, seen))
            
            # Navigate through pagination with a limit on pages
            page = 1
            while page < max_pages and page < 3:  # Additional safety limit
                try:
                    # Try to find the next page button with multiple approaches
                    next_buttons = driver.find_elements(By.XPATH, "//a[contains(., 'Next')]")
                    if not next_buttons:
                        next_buttons = driver.find_elements(By.XPATH, "//a[@rel='next']")
                    if not next_buttons:
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination a:last-child")
                    if not next_buttons:
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, "a.next")
                    
                    if next_buttons and next_buttons[0].is_displayed() and next_buttons[0].is_enabled():
                        next_buttons[0].click()
                        page += 1
                        print(f"Navigating to page {page}")
                        
                        # Wait for the page to load with timeout
                        time.sleep(1)  # Reduced from 2 seconds
                        
                        # Extract complaints from this page
                        new_results = extract_complaints_from_page(driver, seen)
                        results.extend(new_results)
                        print(f"Found {len(new_results)} new results on page {page}")
                        
                        if not new_results:
                            print("No new results found, stopping pagination")
                            break
                    else:
                        print("No next button found or it's disabled")
                        break
                except Exception as e:
                    print(f"Error navigating to next page: {e}")
                    break
        except TimeoutException:
            print("No search results found or timeout occurred")
        
        print(f"Total ComplaintsBoard results: {len(results)}")
        
        # Cache results even if we have a small number
        if results:
            cache.set(cache_key, results, expire=3600 * 24)  # Cache for 24 hours
        return results
    
    except Exception as e:
        print(f"Unexpected error in scraper: {e}")
        return []
    
    finally:
        try:
            driver.quit()
        except:
            pass

def extract_complaints_from_page(driver, seen):
    """Extract complaints from the current page with optimized performance"""
    results = []
    
    # Scroll down just once to load more content but avoid excessive scrolling
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(0.5)  # Reduced wait time
    except Exception as e:
        print(f"Error scrolling: {e}")
    
    # Parse the page
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Try multiple selectors to find complaint items
        selectors = [
            "span.search__item-text",
            ".complaint-item",
            ".complaint-title",
            "h3 a",
            ".complaint a",
            ".complaints-list a"
        ]
        
        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                print(f"Found {len(items)} items with selector: {selector}")
                break
        
        # Limit the number of items processed to avoid timeouts
        max_items = min(len(items), 10)  # Process at most 10 items per page
        
        for item in items[:max_items]:
            try:
                # For search__item-text elements
                parent_a = item.find_parent("a", href=True)
                if not parent_a:
                    # For complaint-item elements
                    parent_a = item.find("a", href=True)
                    if not parent_a and item.name == "a" and "href" in item.attrs:
                        parent_a = item
                
                if parent_a:
                    href = parent_a['href']
                    # Fix: Use a more lenient approach to match complaint URLs
                    if href.startswith('/'):
                        page_url = "https://www.complaintsboard.com" + href.split('#')[0]
                        complaint_id = href.split('#')[1] if '#' in href else ''
                        key = (page_url, complaint_id)
                        if key not in seen:
                            title = item.text.strip()
                            if not title and parent_a.text:
                                title = parent_a.text.strip()
                            
                            results.append({
                                "title": title or f"Complaint about {page_url.split('/')[-1]}",
                                "url": f"{page_url}#{complaint_id}" if complaint_id else page_url,
                                "text": ""
                            })
                            seen.add(key)
            except Exception as e:
                print(f"Error processing item: {e}")
                continue
    
    except Exception as e:
        print(f"Error extracting complaints: {e}")
    
    return results

if __name__ == "__main__":
    # Test the function
    keyword = "salesforce"
    results = improved_complaintsboard_scraper(keyword)
    print(f"Found {len(results)} complaints for '{keyword}'")
    for i, complaint in enumerate(results[:5], 1):
        print(f"{i}. {complaint['title']} - {complaint['url']}")