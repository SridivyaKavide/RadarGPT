import os
import json
import logging
import re
import time
from bs4 import BeautifulSoup
from flask import Flask, render_template, jsonify
import google.generativeai as genai
import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from diskcache import Cache

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    print("ERROR: GOOGLE_API_KEY not found. Please set it in your environment variables.")
    exit(1)

genai.configure(api_key=api_key)
# Use the more capable model for detailed insights
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Initialize cache
cache = Cache("radargpt_cache")

# Create Flask app
app = Flask(__name__)
app.secret_key = 'pain_dashboard_secret_key'

# Define verticals
VERTICALS = {
    "fintech": {
        "name": "Financial Technology",
        "regulations": ["PSD2", "GDPR", "KYC", "AML", "PCI DSS", "Basel III", "Dodd-Frank", "MiFID II"],
        "metrics": ["user acquisition cost", "lifetime value", "churn rate", "transaction volume", "fraud rate", "customer satisfaction", "regulatory compliance score", "API uptime", "payment success rate"]
    },
    "healthcare": {
        "name": "Healthcare & Medical",
        "regulations": ["HIPAA", "FDA", "GDPR", "CCPA", "HITECH Act", "21st Century Cures Act", "Medicare/Medicaid compliance", "Joint Commission standards"],
        "metrics": ["patient acquisition cost", "readmission rate", "treatment efficacy", "patient satisfaction", "care coordination score", "preventative care adoption", "telehealth utilization", "clinical workflow efficiency"]
    },
    "ecommerce": {
        "name": "E-Commerce & Retail",
        "regulations": ["GDPR", "CCPA", "PCI DSS", "CAN-SPAM", "COPPA", "ADA compliance", "Sales tax nexus", "Consumer protection laws"],
        "metrics": ["conversion rate", "cart abandonment", "average order value", "customer lifetime value", "inventory turnover", "return rate", "customer acquisition cost", "net promoter score", "fulfillment accuracy"]
    },
    "saas": {
        "name": "Software as a Service",
        "regulations": ["GDPR", "CCPA", "SOC 2", "ISO 27001", "HIPAA (if applicable)", "FedRAMP", "FISMA", "Cloud Security Alliance standards"],
        "metrics": ["MRR", "ARR", "CAC", "LTV", "churn rate", "NPS", "feature adoption rate", "time-to-value", "support ticket resolution time", "API reliability", "system uptime"]
    },
    "edtech": {
        "name": "Education Technology",
        "regulations": ["FERPA", "COPPA", "GDPR", "CCPA", "Section 508", "ADA compliance", "State education privacy laws", "ESSA requirements"],
        "metrics": ["completion rate", "engagement", "knowledge retention", "student satisfaction", "teacher adoption rate", "accessibility compliance", "learning outcome improvement", "time-to-proficiency"]
    }
}

def improved_complaintsboard_scraper(keyword, max_pages=10):
    """
    Improved version of scrape_complaintsboard_full_text that better handles pagination
    to extract more results, just like in RadarGPT.
    """
    cache_key = f"complaintsboard_{keyword}_{max_pages}"
    # Clear the cache to ensure we get fresh results
    cache.delete(cache_key)
    
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Add a realistic user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Use webdriver_manager to handle driver installation
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # First try the search page
        search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
        driver.get(search_url)
        logger.info(f"Searching ComplaintsBoard for: {keyword}")
        
        results = []
        seen = set()
        
        # Try to find results on the search page
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text, .complaint-item"))
            )
            logger.info("Found search results")
            
            # Process the first page
            results.extend(extract_complaints_from_page(driver, seen))
            
            # Navigate through pagination
            page = 1
            while page < max_pages:
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
                        logger.info(f"Navigating to page {page}")
                        
                        # Wait for the page to load
                        time.sleep(2)
                        
                        # Extract complaints from this page
                        new_results = extract_complaints_from_page(driver, seen)
                        results.extend(new_results)
                        logger.info(f"Found {len(new_results)} new results on page {page}")
                        
                        if not new_results:
                            logger.info("No new results found, stopping pagination")
                            break
                    else:
                        logger.info("No next button found or it's disabled")
                        break
                except Exception as e:
                    logger.error(f"Error navigating to next page: {e}")
                    break
        except TimeoutException:
            logger.warning("No search results found, trying category browsing")
            
            # If search doesn't work, try browsing categories
            try:
                # Go to the main page
                driver.get("https://www.complaintsboard.com/")
                
                # Find categories
                categories = driver.find_elements(By.CSS_SELECTOR, ".categories a")
                if categories:
                    # Click on a relevant category
                    for category in categories[:3]:  # Try first 3 categories
                        category.click()
                        time.sleep(2)
                        
                        # Extract complaints
                        new_results = extract_complaints_from_page(driver, seen)
                        results.extend(new_results)
                        
                        # Go back to categories
                        driver.back()
                        time.sleep(1)
            except Exception as e:
                logger.error(f"Error browsing categories: {e}")
        
        logger.info(f"Total ComplaintsBoard results: {len(results)}")
        cache.set(cache_key, results, expire=3600)
        return results
    
    finally:
        driver.quit()

def extract_complaints_from_page(driver, seen):
    """Extract complaints from the current page"""
    results = []
    
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
            logger.info(f"Found {len(items)} items with selector: {selector}")
            break
    
    for item in items:
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
    
    return results

def analyze_complaints(complaints, query, vertical_name):
    """Analyze complaints data using Gemini and return insights"""
    if not complaints:
        return "No complaints data available to analyze."
    
    # Format complaints for analysis
    complaints_text = "\n\n".join([
        f"Title: {c['title']}\nURL: {c['url']}" 
        for c in complaints[:15]  # Limit to 15 complaints to avoid token limits
    ])
    
    prompt = f"""
    You are a domain expert in {vertical_name}. Analyze these user complaints related to "{query}" and extract insights.
    
    COMPLAINTS:
    {complaints_text}
    
    Provide a structured analysis with:
    1. Common pain points mentioned (with severity 1-10)
    2. User segments affected
    3. Underlying issues
    4. Potential solutions
    5. Trends or patterns
    
    Format your response as a concise, actionable report with bullet points.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip() if response.text else "No insights generated."
    except Exception as e:
        logger.error(f"Error analyzing complaints with Gemini: {e}")
        return f"Error analyzing complaints: {str(e)}"

@app.route('/')
def index():
    """Render the pain dashboard page"""
    return render_template('pain_dashboard.html')

@app.route('/analyze/<vertical>/<query>', methods=['POST'])
def analyze(vertical, query):
    """Get vertical-specific insights with real data from ComplaintsBoard"""
    try:
        # Get vertical data
        if vertical not in VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        regulations = ", ".join(vertical_data["regulations"])
        metrics = ", ".join(vertical_data["metrics"])
        
        # Get current date for context
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        # Scrape ComplaintsBoard using the improved scraper
        complaints = improved_complaintsboard_scraper(query, max_pages=10)
        
        # Format the scraped data for display in the UI
        formatted_sources = {
            "complaintsboard": complaints
        }
        
        # Prepare scraped data for the prompt
        complaintsboard_examples = "\n\n".join([
            f"COMPLAINT: {post['title']}\nURL: {post['url']}"
            for post in complaints[:15]
        ])
        
        # Create enhanced prompt with scraped data
        prompt = f"""
You are a world-class industry analyst and product strategist in the {vertical_name} sector. You have access to comprehensive internal knowledge, proprietary market research, product roadmaps, funding trends, and deep technical insights as of {current_date}.

Your task is to analyze the following query from a startup founder and return the output in a structured, startup-actionable JSON format.

QUERY: {query}

I've collected REAL USER COMPLAINTS from ComplaintsBoard that you should analyze. Focus specifically on the most relevant feedback related to "{query}" and ignore any irrelevant content:

COMPLAINTSBOARD DATA:
{complaintsboard_examples}

== RULES OF RESPONSE ==
- Analyze the REAL USER COMPLAINTS above to identify actual pain points and opportunities
- Include SPECIFIC companies, metrics, trends, and pain points from within the {vertical_name} space
- Focus on ACTIONABLE, INSIGHTFUL, NON-GENERIC content
- Prioritize insights that would help a founder assess opportunity, build, and go to market quickly
- Mention ACTUAL products, strategies, or technologies that currently exist or are being explored

== OUTPUT JSON FORMAT ==
{{
  "classification": "string",

  "context": {{
    "description": "string",
    "current_state": "string",
    "importance": "string",
    "key_players": ["string"],
    "market_size": "string"
  }},

  "pain_points": [
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"],
      "real_world_examples": ["string"]
    }}
  ],

  "considerations": {{
    "regulations": ["string"],
    "technical_challenges": ["string"],
    "integration_points": ["string"],
    "market_barriers": ["string"]
  }},

  "metrics": {{
    "kpis": ["string"],
    "adoption_metrics": ["string"],
    "business_metrics": ["string"]
  }},

  "opportunities": [
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string",
      "differentiation": "string",
      "revenue_model": "string"
    }}
  ]
}}

Be highly specific and practical. Imagine this will directly help a founder build, pitch, or launch a product in {vertical_name} in the next 60 days.
"""

        # Generate structured insights
        response = gemini_model.generate_content(prompt)
        insights_text = response.text.strip() if response.text else ""
        
        # Generate a separate complaints analysis
        complaints_analysis = analyze_complaints(complaints, query, vertical_name)
        
        # Parse JSON response (add error handling)
        try:
            # Find JSON in the response (in case there's any extra text)
            json_match = re.search(r'({[\s\S]*})', insights_text)
            if json_match:
                insights_text = json_match.group(1)
            
            # Clean up the JSON string - remove comments and fix any trailing commas
            cleaned_json = re.sub(r'//.*?(\n|$)', '', insights_text)  # Remove comments
            cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)  # Remove trailing commas
            
            insights_json = json.loads(cleaned_json)
            
            # Add scraped data to the response
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text,
                "complaints_analysis": complaints_analysis,
                "sources": formatted_sources
            })
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw text: {insights_text}")
            # Fallback to text response if JSON parsing fails
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "insights": insights_text,
                "complaints_analysis": complaints_analysis,
                "error": f"Could not parse structured insights: {str(e)}",
                "sources": formatted_sources
            })
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Pain Dashboard with ComplaintsBoard Scraping...")
    print("Visit http://127.0.0.1:5000/ in your browser")
    app.run(debug=True)