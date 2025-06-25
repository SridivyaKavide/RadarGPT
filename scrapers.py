import praw
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
import time
import logging
import os
from datetime import datetime, timedelta
from diskcache import Cache
from config import PERSONA_SOURCES, EMOTIONAL_KEYWORDS, CACHE_SETTINGS, RATE_LIMITS, SCRAPING_SETTINGS
import google.generativeai as genai
from dotenv import load_dotenv
import re
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache('./cache')

class ScraperManager:
    def __init__(self):
        # Initialize Reddit client
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        # Initialize Google Trends client
        self.trends = TrendReq(hl='en-US', tz=360)
        
        # Initialize Gemini
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.cache = Cache("scraper_cache")
        self.driver = None

    def _init_driver(self):
        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            self.driver = webdriver.Chrome(service=Service(webdriver.ChromeDriverManager().install()), options=options)

    def _get_cache_key(self, source, query):
        """Generate a cache key for a source and query."""
        return f"{source}_{query}_{datetime.now().strftime('%Y%m%d')}"

    def _get_cached_data(self, source, persona):
        cache_key = f"{source}_{persona}"
        return self.cache.get(cache_key)

    def _cache_data(self, source, persona, data):
        cache_key = f"{source}_{persona}"
        self.cache.set(cache_key, data, expire=3600)  # Cache for 1 hour

    def _calculate_emotional_score(self, text):
        """Calculate emotional score based on keywords."""
        text_lower = text.lower()
        score = 0
        
        for word in EMOTIONAL_KEYWORDS['negative']:
            if word in text_lower:
                score -= 1
                
        for word in EMOTIONAL_KEYWORDS['positive']:
            if word in text_lower:
                score += 1
                
        return score

    def scrape_reddit(self, persona):
        """Scrape Reddit posts for a persona."""
        try:
            # Check cache first
            cached_data = self._get_cached_data('reddit', persona)
            if cached_data:
                return cached_data

            subreddits = PERSONA_SOURCES[persona]['reddit']
            all_posts = []
            
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Get top posts from last 6 months
                    for post in subreddit.top(time_filter='month', limit=SCRAPING_SETTINGS['max_results']):
                        if (post.score >= SCRAPING_SETTINGS['min_score'] and 
                            post.num_comments >= SCRAPING_SETTINGS['min_comments']):
                            
                            emotional_score = self._calculate_emotional_score(post.title + ' ' + post.selftext)
                            
                            all_posts.append({
                                'source': 'reddit',
                                'subreddit': subreddit_name,
                                'title': post.title,
                                'text': post.selftext,
                                'score': post.score,
                                'comments': post.num_comments,
                                'url': f"https://reddit.com{post.permalink}",
                                'timestamp': post.created_utc,
                                'emotional_score': emotional_score
                            })
                            
                    time.sleep(RATE_LIMITS['reddit'])
                    
                except Exception as e:
                    logger.error(f"Error scraping subreddit {subreddit_name}: {str(e)}")
                    continue
            
            # Cache the results
            self._cache_data('reddit', persona, all_posts)
            return all_posts
            
        except Exception as e:
            logger.error(f"Error in scrape_reddit: {str(e)}")
            return []

    def scrape_stackoverflow(self, persona):
        """Scrape Stack Overflow for a persona."""
        try:
            # Check cache first
            cached_data = self._get_cached_data('stackoverflow', persona)
            if cached_data:
                return cached_data

            tags = PERSONA_SOURCES[persona]['stackoverflow']
            all_questions = []
            
            for tag in tags:
                try:
                    url = f"https://stackoverflow.com/questions/tagged/{tag}?sort=votes"
                    response = self.session.get(url)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    questions = soup.select('.s-post-summary')
                    
                    for question in questions[:SCRAPING_SETTINGS['max_results']]:
                        try:
                            title_elem = question.select_one('.s-post-summary--content-title')
                            if not title_elem:
                                continue
                            
                            title = title_elem.text.strip()
                            link = title_elem.find('a')['href']
                            if not link.startswith('http'):
                                link = 'https://stackoverflow.com' + link
                            
                            # Get question details
                            score_elem = question.select_one('.s-post-summary--stats-item-number')
                            score = int(score_elem.text.strip()) if score_elem else 0
                            
                            answers_elem = question.select_one('.s-post-summary--stats-item.has-answers')
                            answers = int(answers_elem.text.strip()) if answers_elem else 0
                            
                            # Get question body
                            question_response = self.session.get(link)
                            question_response.raise_for_status()
                            question_soup = BeautifulSoup(question_response.text, 'html.parser')
                            body_elem = question_soup.select_one('.s-prose')
                            body = body_elem.text.strip() if body_elem else ''
                            
                            emotional_score = self._calculate_emotional_score(title + ' ' + body)
                            
                            all_questions.append({
                                'source': 'stackoverflow',
                                'tag': tag,
                                'title': title,
                                'text': body,
                                'url': link,
                                'score': score,
                                'answers': answers,
                                'timestamp': datetime.now().timestamp(),
                                'emotional_score': emotional_score
                            })
                            
                            time.sleep(RATE_LIMITS['stackoverflow'])
                            
                        except Exception as e:
                            logger.error(f"Error scraping question {link}: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error scraping Stack Overflow tag {tag}: {str(e)}")
                    continue
            
            # Cache the results
            self._cache_data('stackoverflow', persona, all_questions)
            return all_questions
            
        except Exception as e:
            logger.error(f"Error in scrape_stackoverflow: {str(e)}")
            return []

    def scrape_complaintsboard(self, persona):
        """Scrape ComplaintsBoard for a persona."""
        try:
            # Check cache first
            cached_data = self._get_cached_data('complaintsboard', persona)
            if cached_data:
                return cached_data

            keywords = PERSONA_SOURCES[persona]['complaintsboard']
            all_complaints = []
            
            # Initialize Selenium driver if not already done
            self._init_driver()
            
            for keyword in keywords:
                try:
                    search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
                    self.driver.get(search_url)
                    
                    # Wait for results to load
                    try:
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text"))
                        )
                    except TimeoutException:
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-item"))
                            )
                        except TimeoutException:
                            logger.error(f"No complaint elements found for keyword: {keyword}")
                            continue
                    
                    page = 1
                    seen = set()
                    
                    while page <= SCRAPING_SETTINGS['max_pages']:
                        # Scroll to load more content
                        for _ in range(5):
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                            time.sleep(1)
                        
                        soup = BeautifulSoup(self.driver.page_source, "html.parser")
                        items = soup.select("span.search__item-text")
                        if not items:
                            items = soup.select(".complaint-item")
                        
                        for item in items:
                            try:
                                parent_a = item.find_parent("a", href=True)
                                if not parent_a:
                                    parent_a = item.find("a", href=True)
                                
                                if parent_a:
                                    href = parent_a['href']
                                    if href.startswith('/'):
                                        page_url = "https://www.complaintsboard.com" + href.split('#')[0]
                                        complaint_id = href.split('#')[1] if '#' in href else ''
                                        key = (page_url, complaint_id)
                                        
                                        if key not in seen:
                                            # Get complaint details
                                            self.driver.get(f"{page_url}#{complaint_id}")
                                            complaint_soup = BeautifulSoup(self.driver.page_source, "html.parser")
                                            
                                            title = item.text.strip()
                                            body_elem = complaint_soup.select_one('.complaint-body')
                                            body = body_elem.text.strip() if body_elem else ''
                                            
                                            company_elem = complaint_soup.select_one('.company-name')
                                            company = company_elem.text.strip() if company_elem else 'Unknown'
                                            
                                            emotional_score = self._calculate_emotional_score(title + ' ' + body)
                                            
                                            all_complaints.append({
                                                'source': 'complaintsboard',
                                                'keyword': keyword,
                                                'title': title,
                                                'text': body,
                                                'company': company,
                                                'url': f"{page_url}#{complaint_id}" if complaint_id else page_url,
                                                'timestamp': datetime.now().timestamp(),
                                                'emotional_score': emotional_score
                                            })
                                            seen.add(key)
                                            
                                            time.sleep(RATE_LIMITS['complaintsboard'])
                            
                            except Exception as e:
                                logger.error(f"Error processing complaint item: {str(e)}")
                                continue
                        
                        try:
                            next_button = self.driver.find_element(By.XPATH, "//a[contains(., 'Next')]")
                            if next_button.is_enabled():
                                next_button.click()
                                page += 1
                                time.sleep(2)
                            else:
                                break
                        except Exception:
                            break
                    
                except Exception as e:
                    logger.error(f"Error scraping ComplaintsBoard keyword {keyword}: {str(e)}")
                    continue
            
            # Cache the results
            self._cache_data('complaintsboard', persona, all_complaints)
            return all_complaints
            
        except Exception as e:
            logger.error(f"Error in scrape_complaintsboard: {str(e)}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def get_google_trends(self, persona):
        """Get Google Trends data for a persona."""
        try:
            # Check cache first
            cached_data = self._get_cached_data('trends', persona)
            if cached_data:
                return cached_data

            keywords = PERSONA_SOURCES[persona]['keywords']
            trends_data = []
            
            for keyword in keywords:
                try:
                    self.trends.build_payload([keyword], timeframe='today 6-m')
                    interest_over_time = self.trends.interest_over_time()
                    
                    if not interest_over_time.empty:
                        trends_data.append({
                            'keyword': keyword,
                            'trend': interest_over_time[keyword].tolist(),
                            'dates': interest_over_time.index.strftime('%Y-%m-%d').tolist()
                        })
                    
                    time.sleep(RATE_LIMITS['trends'])
                    
                except Exception as e:
                    logger.error(f"Error getting trends for keyword {keyword}: {str(e)}")
                    continue
            
            # Cache the results
            self._cache_data('trends', persona, trends_data)
            return trends_data
            
        except Exception as e:
            logger.error(f"Error in get_google_trends: {str(e)}")
            return []

    def generate_summary(self, persona, complaints):
        """Generate summary using Gemini."""
        try:
            # Check cache first
            cached_data = self._get_cached_data('summaries', persona)
            if cached_data:
                return cached_data

            # Format complaints for the prompt
            formatted_complaints = "\n".join([
                f"- {c['title']}: {c['text'][:200]}..."
                for c in complaints[:10]  # Use top 10 complaints
            ])
            
            # Generate summary using Gemini
            prompt = PROMPT_TEMPLATES['summarize_pains'].format(
                persona=persona,
                complaints=formatted_complaints
            )
            
            response = self.model.generate_content(prompt)
            summary = response.text
            
            # Cache the results
            self._cache_data('summaries', persona, summary)
            return summary
            
        except Exception as e:
            logger.error(f"Error in generate_summary: {str(e)}")
            return None

    def scrape_all_sources(self, persona):
        """Scrape data from all sources for a persona."""
        try:
            # Scrape from all sources
            reddit_data = self.scrape_reddit(persona)
            stackoverflow_data = self.scrape_stackoverflow(persona)
            complaintsboard_data = self.scrape_complaintsboard(persona)
            trends_data = self.get_google_trends(persona)
            
            # Combine all data
            all_data = {
                'reddit': reddit_data,
                'stackoverflow': stackoverflow_data,
                'complaintsboard': complaintsboard_data,
                'trends': trends_data
            }
            
            # Generate summary
            all_complaints = reddit_data + stackoverflow_data + complaintsboard_data
            summary = self.generate_summary(persona, all_complaints)
            
            if summary:
                all_data['summary'] = summary
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error in scrape_all_sources: {str(e)}")
            return {} 