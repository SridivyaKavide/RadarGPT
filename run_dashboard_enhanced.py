import os
import json
import logging
from flask import Flask, render_template, jsonify
import google.generativeai as genai
import datetime
from dotenv import load_dotenv

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

@app.route('/')
def index():
    """Render the pain dashboard page"""
    return render_template('pain_dashboard.html')

@app.route('/analyze/<vertical>/<query>', methods=['POST'])
def analyze(vertical, query):
    """Get vertical-specific insights with enhanced detail and accuracy"""
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
        
        # Create enhanced prompt for more detailed, accurate insights
        prompt = f"""
You are a world-class industry analyst and product strategist in the {vertical_name} sector. You have access to comprehensive internal knowledge, proprietary market research, product roadmaps, funding trends, and deep technical insights as of {current_date}.

Your task is to analyze the following query from a startup founder and return the output in a structured, startup-actionable JSON format.

QUERY: {query}

== RULES OF RESPONSE ==
- Do NOT speculate or invent facts. Base everything on known industry knowledge.
- Include SPECIFIC companies, metrics, trends, and pain points from within the {vertical_name} space.
- Focus on ACTIONABLE, INSIGHTFUL, NON-GENERIC content.
- Prioritize insights that would help a founder assess opportunity, build, and go to market quickly.
- Mention ACTUAL products, strategies, or technologies that currently exist or are being explored.

== OUTPUT JSON FORMAT ==
{{
  "classification": "string", // Type of query: one of [information, validation, problem, guidance, exploration]

  "context": {{
    "description": "string", // What this query means in {vertical_name} with industry framing
    "current_state": "string", // What is happening right now? Include market data, real trends, competitors
    "importance": "string", // Why this matters now in the context of shifts in {vertical_name}
    "key_players": ["string"], // Real companies/products involved
    "market_size": "string", // Known global or regional market size (with source/date if possible)
    "recent_developments": ["string"] // Real recent events, trends, funding, acquisitions
  }},

  "pain_points": [
    {{
      "title": "string",
      "description": "string", // Include user quotes if possible
      "severity": number, // 1 to 10
      "reason_unsolved": "string", // Explain why current solutions fall short
      "user_segments": ["string"], // Affected personas
      "real_world_examples": ["string"], // Links or events if known
      "current_solutions": ["string"], // Actual solutions and what’s missing
      "opportunity_size": "string" // TAM/SAM if known or inferred
    }}
  ],

  "considerations": {{
    "regulations": ["string"], // Specific to this vertical and region
    "technical_challenges": ["string"], // System, AI/ML, API, scaling issues
    "integration_points": ["string"], // Common platforms/tools startups must plug into
    "market_barriers": ["string"], // Adoption, trust, distribution, etc.
    "competitive_landscape": ["string"] // Known players and approaches
  }},

  "metrics": {{
    "kpis": ["string"], // Product or growth KPIs tracked in {vertical_name}
    "adoption_metrics": ["string"], // MAUs, retention, conversion, etc.
    "business_metrics": ["string"], // ACV, churn, CAC, CLTV
    "industry_benchmarks": ["string"] // If available
  }},

  "opportunities": [
    {{
      "product_concept": "string", // Title of a potential product
      "value_proposition": "string", // Who benefits, and how
      "target_users": ["string"],
      "go_to_market": "string", // Actual channels, sequences, B2B/B2C, etc.
      "differentiation": "string", // Clear comparison to others
      "revenue_model": "string", // Freemium? SaaS? B2B sales?
      "technical_requirements": ["string"], // APIs, AI, infra, etc.
      "success_stories": ["string"] // Real startups/products solving similar issues
    }}
  ],

  "resources": [
    {{
      "type": "string", // Research, community, tool, dataset, framework
      "name": "string",
      "description": "string"
    }}
  ]
}}

== FINAL INSTRUCTIONS ==
Be highly specific and practical. Imagine this will directly help a founder build, pitch, or launch a product in {vertical_name} in the next 60 days.
Do not output anything other than the JSON structure above.
"""

        
        # Generate structured insights
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
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text
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
                "error": f"Could not parse structured insights: {str(e)}"
            })
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Enhanced Pain Dashboard server...")
    print("Visit http://127.0.0.1:5000/ in your browser")
    app.run(debug=True)