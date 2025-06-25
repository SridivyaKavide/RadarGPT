import os
import json
import re
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from diskcache import Cache

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

# Define verticals directly in this file to avoid import issues
VERTICALS = {
    "fintech": {
        "name": "Financial Technology",
        "regulations": ["PSD2", "GDPR", "KYC", "AML", "PCI DSS"],
        "metrics": ["user acquisition cost", "lifetime value", "churn rate", "transaction volume"]
    },
    "healthcare": {
        "name": "Healthcare & Medical",
        "regulations": ["HIPAA", "FDA", "GDPR", "CCPA"],
        "metrics": ["patient acquisition cost", "readmission rate", "treatment efficacy"]
    },
    "ecommerce": {
        "name": "E-Commerce & Retail",
        "regulations": ["GDPR", "CCPA", "PCI DSS"],
        "metrics": ["conversion rate", "cart abandonment", "average order value", "customer lifetime value"]
    },
    "saas": {
        "name": "Software as a Service",
        "regulations": ["GDPR", "CCPA", "SOC 2"],
        "metrics": ["MRR", "ARR", "CAC", "LTV", "churn rate", "NPS"]
    },
    "edtech": {
        "name": "Education Technology",
        "regulations": ["FERPA", "COPPA", "GDPR"],
        "metrics": ["completion rate", "engagement", "knowledge retention", "student satisfaction"]
    }
}

@app.route('/')
def index():
    """Render the pain dashboard page"""
    return render_template('pain_dashboard.html')

@app.route('/analyze/<vertical>/<query>', methods=['POST'])
def analyze(vertical, query):
    """Get vertical-specific insights using ONLY Gemini's knowledge in structured format"""
    try:
        # Get vertical data
        if vertical not in VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        regulations = ", ".join(vertical_data["regulations"])
        metrics = ", ".join(vertical_data["metrics"])
        
        # Check cache first
        cache_key = f"insights_{vertical}_{query}"
        cached_insights = cache.get(cache_key)
        
        if cached_insights:
            logger.info(f"Using cached insights for {vertical}/{query}")
            return jsonify(cached_insights)
        
        # Create prompt that uses ONLY Gemini's knowledge but returns structured data
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
        
        Use ONLY your built-in knowledge about {vertical_name}. Be specific and actionable.
        """
        
        # Generate structured insights with a timeout
        response = gemini_model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 2000}  # Limit output size
        )
        insights_text = response.text.strip() if response.text else ""
        
        # Parse JSON response (add error handling)
        try:
            # Find JSON in the response (in case there's any extra text)
            json_match = re.search(r'({[\s\S]*})', insights_text)
            if json_match:
                insights_text = json_match.group(1)
            
            insights_json = json.loads(insights_text)
            result = {
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text
            }
            
            # Cache the result
            cache.set(cache_key, result, expire=3600 * 24)  # Cache for 24 hours
            
            return jsonify(result)
        except json.JSONDecodeError:
            # Fallback to text response if JSON parsing fails
            result = {
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "insights": insights_text,
                "error": "Could not parse structured insights"
            }
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)