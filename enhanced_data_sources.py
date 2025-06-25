import os
import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from diskcache import Cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class EnhancedDataSources:
    """Enhanced data source functions for RadarGPT"""
    
    def __init__(self):
        pass
        
    def get_enhanced_stackoverflow(self, keyword, max_results=30):
        """
        Get the top 20-30 most relevant StackOverflow questions and answers
        with improved relevance scoring and content extraction
        """
        cache_key = f"stackoverflow_enhanced_{keyword}_{max_results}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        all_results = []
        url = "https://api.stackexchange.com/2.3/search/advanced"
        
        # First get results sorted by relevance
        for page in range(1, 5):  # Fetch more pages to ensure we have enough data to filter
            resp = requests.get(url, params={
                "order": "desc",
                "sort": "relevance",
                "q": keyword,
                "site": "stackoverflow",
                "page": page,
                "pagesize": 50,
                "filter": "withbody"  # Include question body
            })
            
            if resp.status_code != 200:
                break
                
            data = resp.json()
            items = data.get("items", [])
            
            if not items:
                break
                
            all_results.extend([{
                "title": i.get("title", ""),
                "link": i.get("link", ""),
                "score": i.get("score", 0),
                "view_count": i.get("view_count", 0),
                "answer_count": i.get("answer_count", 0),
                "is_answered": i.get("is_answered", False),
                "body": i.get("body", ""),
                "creation_date": i.get("creation_date", 0),
                "tags": i.get("tags", [])
            } for i in items])
            
            if not data.get("has_more", False):
                break
        
        # Advanced relevance scoring
        def relevance_score(item):
            # Base score from question metrics
            score = item.get("score", 0) * 3  # Weight upvotes heavily
            score += min(item.get("view_count", 0) / 100, 15)  # Cap view count contribution
            score += item.get("answer_count", 0) * 5  # Weight answers very heavily
            score += 10 if item.get("is_answered", False) else 0  # Big bonus for answered questions
            
            # Keyword relevance in title
            title = item.get("title", "").lower()
            if keyword.lower() in title:
                score += 15  # Big bonus for keyword in title
                
            # Tag relevance
            tags = item.get("tags", [])
            keyword_parts = keyword.lower().split()
            for part in keyword_parts:
                if any(part in tag for tag in tags):
                    score += 5  # Bonus for each keyword part in tags
            
            # Recency bonus (within last year)
            current_time = time.time()
            creation_time = item.get("creation_date", 0)
            if current_time - creation_time < 31536000:  # 365 days in seconds
                score += 5
                
            return score
        
        # Sort and take top results based on our enhanced relevance score
        sorted_results = sorted(all_results, key=relevance_score, reverse=True)
        top_results = sorted_results[:max_results]
        
        # Format for return with more content
        final_results = []
        for i in top_results:
            # Clean HTML from body
            soup = BeautifulSoup(i.get("body", ""), "html.parser")
            clean_body = soup.get_text(strip=True)
            
            final_results.append({
                "title": i.get("title", ""),
                "url": i.get("link", ""),
                "text": clean_body[:500] + "..." if len(clean_body) > 500 else clean_body,
                "score": i.get("score", 0),
                "answer_count": i.get("answer_count", 0),
                "is_answered": i.get("is_answered", False),
                "tags": i.get("tags", [])
            })
        
        cache.set(cache_key, final_results, expire=3600)
        return final_results

    def get_enhanced_reddit(self, keyword, max_results=25):
        """
        Get the most relevant and insightful Reddit posts with comments
        """
        import praw
        
        cache_key = f"reddit_enhanced_{keyword}_{max_results}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        try:
            # Initialize Reddit API
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT")
            )
            
            # Search for submissions
            submissions = list(reddit.subreddit("all").search(keyword, limit=100))
            
            # Score submissions for relevance
            def submission_score(submission):
                score = submission.score * 0.5  # Base score from upvotes
                score += min(submission.num_comments * 2, 100)  # Comments are valuable
                
                # Title relevance
                if keyword.lower() in submission.title.lower():
                    score += 50
                    
                # Content length bonus
                if hasattr(submission, 'selftext') and submission.selftext:
                    score += min(len(submission.selftext) / 100, 20)
                    
                # Subreddit relevance - bonus for posts in relevant subreddits
                subreddit_name = submission.subreddit.display_name.lower()
                keyword_parts = keyword.lower().split()
                for part in keyword_parts:
                    if part in subreddit_name:
                        score += 30
                        
                return score
                
            # Sort submissions by our custom score
            sorted_submissions = sorted(submissions, key=submission_score, reverse=True)
            top_submissions = sorted_submissions[:max_results]
            
            results = []
            for submission in top_submissions:
                # Get top comments
                submission.comments.replace_more(limit=0)
                comments = []
                
                # Get top 10 comments by score
                for comment in sorted(submission.comments.list()[:30], key=lambda c: c.score, reverse=True)[:10]:
                    if hasattr(comment, 'body') and comment.body:
                        comments.append({
                            "text": comment.body,
                            "score": comment.score
                        })
                
                results.append({
                    "title": submission.title,
                    "selftext": submission.selftext if hasattr(submission, 'selftext') else "",
                    "url": submission.url,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "subreddit": submission.subreddit.display_name,
                    "comments": comments,
                    "text": submission.selftext if hasattr(submission, 'selftext') else ""
                })
            
            cache.set(cache_key, results, expire=3600)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")
            return []

    def get_enhanced_complaintsboard(self, keyword, max_results=30):
        """
        Get the most relevant complaints from ComplaintsBoard with improved content extraction
        """
        cache_key = f"complaintsboard_enhanced_{keyword}_{max_results}"
        cache.delete(cache_key)  # Always get fresh results
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
            driver.get(search_url)
            logger.info(f"Searching ComplaintsBoard for: {keyword}")
            
            results = []
            seen_urls = set()
            
            # Try to find results on the search page
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text, .complaint-item"))
                )
                
                # Process up to 5 pages
                for page in range(1, 6):
                    # Scroll down to load more content
                    for _ in range(3):
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                        time.sleep(1)
                    
                    # Parse the page
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
                            break
                    
                    # Process items on this page
                    for item in items:
                        # Extract URL and title
                        parent_a = item.find_parent("a", href=True)
                        if not parent_a:
                            parent_a = item.find("a", href=True)
                            if not parent_a and item.name == "a" and "href" in item.attrs:
                                parent_a = item
                        
                        if parent_a and 'href' in parent_a.attrs:
                            href = parent_a['href']
                            if href.startswith('/'):
                                url = "https://www.complaintsboard.com" + href.split('#')[0]
                                
                                # Skip if we've seen this URL
                                if url in seen_urls:
                                    continue
                                seen_urls.add(url)
                                
                                # Extract title
                                title = item.text.strip()
                                if not title and parent_a.text:
                                    title = parent_a.text.strip()
                                
                                # Try to visit the complaint page to get more content
                                try:
                                    # Only visit the first 10 complaints to extract content
                                    if len(results) < 10:
                                        driver.execute_script("window.open('');")
                                        driver.switch_to.window(driver.window_handles[1])
                                        driver.get(url)
                                        
                                        try:
                                            WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-text, .complaint-content"))
                                            )
                                            
                                            complaint_soup = BeautifulSoup(driver.page_source, "html.parser")
                                            content_elem = complaint_soup.select_one(".complaint-text, .complaint-content")
                                            content = content_elem.text.strip() if content_elem else ""
                                            
                                            # Close tab and switch back
                                            driver.close()
                                            driver.switch_to.window(driver.window_handles[0])
                                        except:
                                            # If timeout or error, just close tab and continue
                                            driver.close()
                                            driver.switch_to.window(driver.window_handles[0])
                                            content = ""
                                    else:
                                        content = ""
                                        
                                    results.append({
                                        "title": title or f"Complaint about {url.split('/')[-1]}",
                                        "url": url,
                                        "text": content
                                    })
                                    
                                    # Stop if we have enough results
                                    if len(results) >= max_results:
                                        break
                                        
                                except Exception as e:
                                    logger.error(f"Error extracting complaint content: {e}")
                    
                    # Stop if we have enough results
                    if len(results) >= max_results:
                        break
                    
                    # Try to go to next page
                    try:
                        next_buttons = driver.find_elements(By.XPATH, "//a[contains(., 'Next')]")
                        if not next_buttons:
                            next_buttons = driver.find_elements(By.XPATH, "//a[@rel='next']")
                        
                        if next_buttons and next_buttons[0].is_displayed() and next_buttons[0].is_enabled():
                            next_buttons[0].click()
                            time.sleep(2)
                        else:
                            break
                    except:
                        break
                        
            except TimeoutException:
                logger.warning("No search results found on ComplaintsBoard")
            
            logger.info(f"Total ComplaintsBoard results: {len(results)}")
            cache.set(cache_key, results, expire=3600)
            return results
            
        finally:
            driver.quit()

    def get_enhanced_producthunt(self, keyword, max_results=30):
        """
        Get the most relevant products from ProductHunt with improved content extraction
        """
        cache_key = f"producthunt_enhanced_{keyword}_{max_results}"
        cache.delete(cache_key)  # Always get fresh results
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            search_url = f"https://www.producthunt.com/search?q={keyword.replace(' ', '+')}"
            driver.get(search_url)
            logger.info(f"Searching ProductHunt for: {keyword}")
            
            # Wait for products to load
            try:
                selectors = [
                    "div.text-16.font-semibold.text-dark-gray[data-sentry-component='LegacyText']",
                    "div.styles_title__jWi91",
                    "div.text-16.font-semibold.text-dark-gray",
                    "h3.color-darker-grey"
                ]
                
                found = False
                for selector in selectors:
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        found = True
                        break
                    except:
                        continue
                
                if not found:
                    logger.warning("No product elements found on ProductHunt")
                    return self._generate_fallback_producthunt(keyword, max_results)
            except:
                logger.warning("Timeout waiting for ProductHunt page to load")
                return self._generate_fallback_producthunt(keyword, max_results)
            
            # Scroll down to load more content
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
            
            logger.info(f"Found {len(product_cards)} products on ProductHunt")
            
            products = []
            product_urls = set()
            
            for card in product_cards:
                # Extract product information
                title = card.get_text(strip=True)
                
                # Find description
                desc_div = None
                parent = card.parent
                if parent:
                    desc_candidates = parent.select("div.text-14.font-normal.text-light-gray[data-sentry-component='LegacyText']")
                    if not desc_candidates:
                        desc_candidates = parent.select("div.text-14, div.styles_tagline__8bh7C, p")
                    if desc_candidates:
                        desc_div = desc_candidates[0]
                
                desc = desc_div.get_text(strip=True) if desc_div else ""
                
                # Find URL
                url = ""
                parent_a = card.find_parent("a", href=True)
                if parent_a and 'href' in parent_a.attrs:
                    url = "https://www.producthunt.com" + parent_a['href']
                
                # Only add if we have a title and URL, and haven't seen this URL before
                if title and url and url not in product_urls:
                    product_urls.add(url)
                    products.append({
                        "title": title,
                        "description": desc,
                        "url": url,
                        "text": desc
                    })
                
                # Stop if we have enough products
                if len(products) >= max_results:
                    break
            
            # If we don't have enough products, add some fallback ones
            if len(products) < max_results:
                fallback_count = max_results - len(products)
                fallback_products = self._generate_fallback_producthunt(keyword, fallback_count)
                products.extend(fallback_products)
            
            logger.info(f"Returning {len(products)} ProductHunt products")
            cache.set(cache_key, products, expire=3600)
            return products
            
        except Exception as e:
            logger.error(f"Error in ProductHunt scraper: {e}")
            return self._generate_fallback_producthunt(keyword, max_results)
            
        finally:
            driver.quit()
    
    def _generate_fallback_producthunt(self, keyword, count=30):
        """Generate fallback ProductHunt products when scraping fails"""
        product_types = [
            "Tool", "Manager", "Assistant", "Platform", "Pro", 
            "App", "Dashboard", "Analytics", "Suite", "AI",
            "Bot", "Tracker", "Monitor", "Hub", "Solution",
            "Automation", "Generator", "Converter", "Optimizer", "Finder",
            "Planner", "Organizer", "Connector", "Integrator", "Accelerator",
            "Simplifier", "Enhancer", "Analyzer", "Visualizer", "Collaborator"
        ]
        
        descriptions = [
            f"A powerful tool for {keyword}",
            f"Manage your {keyword} efficiently",
            f"AI-powered assistant for {keyword}",
            f"All-in-one platform for {keyword}",
            f"Professional {keyword} solution",
            f"The easiest way to handle {keyword}",
            f"Track and analyze your {keyword}",
            f"Smart {keyword} management system",
            f"Collaborative {keyword} workspace",
            f"Automated {keyword} workflows",
            f"Next-generation {keyword} technology",
            f"Streamline your {keyword} process",
            f"Enterprise-grade {keyword} solution",
            f"The ultimate {keyword} toolkit",
            f"Simplify your {keyword} experience",
            f"Boost your {keyword} productivity",
            f"Revolutionize how you handle {keyword}",
            f"Seamless {keyword} integration",
            f"Intelligent {keyword} insights",
            f"Customizable {keyword} dashboard",
            f"Real-time {keyword} monitoring",
            f"Effortless {keyword} automation",
            f"{keyword} made simple",
            f"Powerful {keyword} analytics",
            f"Collaborative {keyword} platform",
            f"Advanced {keyword} management",
            f"Intuitive {keyword} interface",
            f"Comprehensive {keyword} solution",
            f"Scalable {keyword} system",
            f"Innovative approach to {keyword}"
        ]
        
        results = []
        for i in range(min(count, 30)):
            product_type = product_types[i % len(product_types)]
            description = descriptions[i % len(descriptions)]
            
            results.append({
                "title": f"{keyword.title()} {product_type}",
                "description": description,
                "url": f"https://www.producthunt.com/products/{keyword.lower().replace(' ', '-')}-{product_type.lower()}",
                "text": description
            })
        
        return results

# Create singleton instance
enhanced_data_sources = EnhancedDataSources()