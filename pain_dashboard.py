import os
import json
import logging
import time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from vertical_insights import vertical_insights as vi
from concurrent.futures import ThreadPoolExecutor, as_completed
from diskcache import Cache

# Import the improved ComplaintsBoard scraper
from improved_complaintsboard import improved_complaintsboard_scraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize cache
cache = Cache("radargpt_cache")

# Create Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = 'pain_dashboard_secret_key'

@app.route('/')
def index():
    """Render the pain dashboard page"""
    return render_template('pain_dashboard.html')
    
@app.route('/pain-dashboard')
def pain_dashboard():
    """Render the pain dashboard page with query parameters"""
    return render_template('pain_dashboard.html')

def scrape_complaintsboard(keyword, max_pages=3):
    """
    Scrape ComplaintsBoard for the given keyword using the improved scraper
    with a cache to avoid repeated scraping
    """
    try:
        # Use cache to avoid repeated scraping
        cache_key = f"complaintsboard_{keyword}_{max_pages}"
        cached_results = cache.get(cache_key)
        
        if cached_results:
            logger.info(f"Using cached ComplaintsBoard results for '{keyword}'")
            return cached_results
            
        logger.info(f"Scraping ComplaintsBoard for: {keyword}")
        results = improved_complaintsboard_scraper(keyword, max_pages=max_pages)
        logger.info(f"Found {len(results)} ComplaintsBoard results for '{keyword}'")
        
        # Cache the results for future use
        cache.set(cache_key, results, expire=3600)  # Cache for 1 hour
        return results
    except Exception as e:
        logger.error(f"Error scraping ComplaintsBoard: {e}")
        return []

def gemini_analyze_complaints(complaints, query, vertical_name):
    """
    Analyze complaints data using Gemini and return insights
    with optimized prompt and error handling
    """
    if not complaints:
        return "No complaints data available to analyze."
    
    # Format complaints for analysis - limit to 10 complaints to reduce token usage
    complaints_text = "\n\n".join([
        f"Title: {c['title']}\nURL: {c['url']}" 
        for c in complaints[:10]  # Reduced from 20 to 10 to avoid token limits
    ])
    
    # Simplified prompt to reduce token usage
    prompt = f"""
    As a {vertical_name} expert, analyze these complaints about "{query}":
    
    {complaints_text}
    
    Provide a brief analysis with:
    1. Top 3 pain points (with severity 1-10)
    2. Main user segments affected
    3. Key underlying issues
    4. Quick solution ideas
    
    Keep your response concise with bullet points.
    """
    
    try:
        # Use a more efficient model with a timeout
        response = gemini_model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 1000}  # Limit output size
        )
        return response.text.strip() if response.text else "No insights generated."
    except Exception as e:
        logger.error(f"Error analyzing complaints with Gemini: {e}")
        return "Unable to analyze complaints due to processing limitations."

@app.route('/analyze/<vertical>/<query>', methods=['POST'])
def analyze(vertical, query):
    """Get vertical-specific insights using Gemini's knowledge and ComplaintsBoard data"""
    try:
        # Get vertical data
        if vertical not in vi.VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = vi.VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        regulations = ", ".join(vertical_data["regulations"])
        metrics = ", ".join(vertical_data["metrics"])
        
        # Create prompt that uses Gemini's knowledge but returns structured data
        prompt = f"""
        You are a domain expert in {vertical_name}. Analyze this query and return insights in a structured JSON format.
        
        QUERY: {query}
        
        Return your response in this exact JSON structure:
        {{
          "classification": "string", // Type of query (information, validation, problem, guidance, exploration)
          "context": {{
            "description": "string", // What this query means in {vertical_name}
            "current_state": "string", // Current state of this area
            "importance": "string" // Why this is important now
          }},
          "pain_points": [
            {{
              "title": "string",
              "description": "string",
              "severity": number, // 1-10
              "reason_unsolved": "string",
              "user_segments": ["string"]
            }}
          ],
          "considerations": {{
            "regulations": ["string"],
            "technical_challenges": ["string"],
            "integration_points": ["string"]
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
              "go_to_market": "string"
            }}
          ]
        }}
        
        Use your built-in knowledge about {vertical_name}. Be specific and actionable.
        """
        
        # Generate structured insights first (this is faster and more reliable)
        response = gemini_model.generate_content(prompt)
        insights_text = response.text.strip() if response.text else ""
        
        # Parse JSON response (add error handling)
        try:
            # Find JSON in the response (in case there's any extra text)
            import re
            json_match = re.search(r'({[\s\S]*})', insights_text)
            if json_match:
                insights_text = json_match.group(1)
            
            insights_json = json.loads(insights_text)
            
            # Start ComplaintsBoard scraping in a separate thread with a shorter timeout
            # This way we can return the main insights even if scraping fails
            complaints = []
            complaints_analysis = ""
            
            try:
                # Use a shorter timeout for the scraper to prevent hanging
                with ThreadPoolExecutor(max_workers=1) as executor:
                    complaints_future = executor.submit(scrape_complaintsboard, query, max_pages=3)  # Reduced max pages
                    complaints = complaints_future.result(timeout=30)  # Reduced timeout to 30 seconds
                    
                    # If we have complaints data, analyze it
                    if complaints:
                        complaints_analysis = gemini_analyze_complaints(complaints, query, vertical_name)
            except Exception as e:
                logger.error(f"Error getting ComplaintsBoard results: {e}")
                # Continue without complaints data
            
            # Return both the structured insights and the complaints data (if available)
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text,
                "complaints_analysis": complaints_analysis,
                "sources": {
                    "complaintsboard": complaints
                }
            })
        except json.JSONDecodeError:
            # Fallback to text response if JSON parsing fails
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "insights": insights_text,
                "complaints_analysis": "",
                "sources": {
                    "complaintsboard": []
                },
                "error": "Could not parse structured insights"
            })
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

# Add a route to directly scrape ComplaintsBoard
@app.route('/scrape_complaints/<query>', methods=['POST'])
def scrape_complaints_route(query):
    """Endpoint to directly scrape ComplaintsBoard for a query"""
    try:
        max_pages = request.json.get('max_pages', 10) if request.is_json else 10
        results = scrape_complaintsboard(query, max_pages=max_pages)
        
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        logger.error(f"Error in scrape_complaints route: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)