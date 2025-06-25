import os
import json
import logging
import re
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
gemini_model = genai.GenerativeModel("gemini-2.0-flash", 
                              generation_config={"temperature": 0.9, "max_output_tokens": 8192})

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
    """Get vertical-specific insights using only Gemini's internal knowledge"""
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
        
        # Use the detailed prompt requested by the user with instructions for more comprehensive output
        prompt = f"""
You are a billion-dollar product strategist, domain analyst, and venture expert in the {vertical_name} sector. You are trusted by top-tier VCs and founders for your unmatched depth of insight into product-market fit, unsolved user pain, competitive edge, and fast-execution strategy.

You have access to comprehensive internal knowledge — proprietary market intelligence, user needs, technology gaps, funding trends, and real competitive landscapes — up to {current_date}.

---

Your task is to analyze the following startup query as if you were advising a world-class founder preparing to launch in the next 60 days.

Use only your **internal knowledge** — do not pull from external web sources. Be extremely specific, avoid vague statements, and act as if your answer will be used to raise funding and guide the product roadmap.

---

QUERY: {query}

== STRUCTURED OUTPUT FORMAT ==
Return your analysis in the following **strict JSON format**, tailored for startup execution:

{{
  "classification": "string",  // One of: "information", "validation", "problem", "guidance", "exploration"

  "context": {{
    "description": "string",  // Specific interpretation of the query within {vertical_name}
    "current_state": "string",  // What's happening in this space right now (real trends, user behavior)
    "importance": "string",  // Why this matters urgently (e.g. user shift, funding boom, tech unlock)
    "key_players": ["string"],  // Real companies, tools, or open gaps in this area
    "market_size": "string"  // Estimated TAM/SAM/SOM if known, or strategic value
  }},

  "pain_points": [
    {{
      "title": "string",  // Name of problem or unmet need
      "description": "string",  // Clear real-world user pain and how it manifests
      "severity": number,  // 1-10 based on urgency + impact
      "reason_unsolved": "string",  // Why current solutions fail (tech, UX, trust, cost, etc.)
      "user_segments": ["string"]  // Specific user personas or roles
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }}
  ],

  "considerations": {{
    "regulations": ["string"],  // Compliance factors, privacy laws, regional rules
    "technical_challenges": ["string"],  // Infra, scalability, ML, integrations
    "integration_points": ["string"],  // APIs, platforms, CRMs, ecosystems to plug into
    "market_barriers": ["string"]  // Friction in adoption, education, procurement, etc.
  }},

  "metrics": {{
    "kpis": ["string"],  // Metrics that show product is working (e.g. activation rate, ROI)
    "adoption_metrics": ["string"],  // Signs of early traction (e.g. signups per week, usage per cohort)
    "business_metrics": ["string"]  // CAC, LTV, churn, ACV — startup health metrics
  }},

  "opportunities": [
    {{
      "product_concept": "string",  // Clear product idea grounded in the pain point
      "value_proposition": "string",  // Specific user benefit (save time, unlock revenue, reduce risk)
      "target_users": ["string"],  // Exact persona or vertical
      "go_to_market": "string"  // 60-day GTM plan: how to reach and acquire users fast
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }}
  ]
}}

IMPORTANT INSTRUCTIONS:
1. Provide AT LEAST 10 most relevant most useful trending upto {current_date} detailed pain points with comprehensive descriptions
2. Provide AT LEAST 10-15 most relevant most useful not implemented till now detailed opportunities with specific go-to-market strategies
3. Be extremely detailed and specific in all descriptions
4. Use real-world examples, metrics, and data where possible
5. Name specific companies, technologies existing in the market and their relevance and gaps what they are not solving
6. Include real company names, market sizes, and specific metrics where possible
7. Make all descriptions at least 3-4 sentences long with specific details
8. Ensure all arrays have multiple detailed items

Be highly specific and practical about {vertical_name}. Imagine this will directly help a founder build, pitch, or launch a product in the next 60 days.
Do not output anything other than the JSON structure above.
"""
        # Generate structured insights
        response = gemini_model.generate_content(prompt)
        insights_text = response.text.strip() if response.text else ""
        
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
            
            # Return the insights without any scraped data
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text,
                "sources": {
                    "reddit": [],
                    "stackoverflow": [],
                    "complaintsboard": []
                }
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
                "error": f"Could not parse structured insights: {str(e)}",
                "sources": {
                    "reddit": [],
                    "stackoverflow": [],
                    "complaintsboard": []
                }
            })
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Simple Pain Dashboard (No Scraping)...")
    print("Visit http://127.0.0.1:5000/ in your browser")
    app.run(debug=True)