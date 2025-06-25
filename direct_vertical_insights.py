import os
import google.generativeai as genai
import logging
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from vertical_insights import vertical_insights as vi

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Create blueprint
direct_vertical_routes = Blueprint('direct_vertical_routes', __name__)

@direct_vertical_routes.route('/direct_vertical')
@login_required
def direct_vertical_page():
    """
    Render the direct vertical insights page
    """
    return render_template('direct_vertical.html')

@direct_vertical_routes.route('/direct_vertical/<vertical>/<query>', methods=['POST'])
@login_required
def direct_vertical_insights(vertical, query):
    """
    Get vertical-specific insights using ONLY Gemini's internal knowledge
    """
    try:
        # Get vertical data
        if vertical not in vi.VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = vi.VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        regulations = ", ".join(vertical_data["regulations"])
        metrics = ", ".join(vertical_data["metrics"])
        
        # Create prompt that uses ONLY Gemini's knowledge
        prompt = f"""
        You are a domain expert in {vertical_name}. Use ONLY your built-in knowledge to provide strategic insight about this query.
        DO NOT reference any external content. Rely SOLELY on what you already know.

        QUERY: {query}

        STEP 1: QUERY CLASSIFICATION
        Classify the query as one of:
        - Information-seeking question
        - Product or startup idea needing validation
        - Problem or challenge needing solutions
        - "Where do I start?" guidance request
        - Broad topic exploration

        STEP 2: INDUSTRY CONTEXT IN {vertical_name}
        - What does this query represent in {vertical_name}?
        - What is the current state of this area in {vertical_name}?
        - Why is this topic important in {vertical_name} now?

        STEP 3: INNOVATION OPPORTUNITIES
        List 3-4 high-potential innovation areas in {vertical_name} related to the query:
        - Opportunity title
        - Pain point severity (1-10)
        - Why it's still unsolved
        - Target user segments

        STEP 4: KEY CONSIDERATIONS
        - Relevant regulations in {vertical_name}: {regulations}
        - Technical challenges to overcome
        - Integration requirements

        STEP 5: SUCCESS METRICS
        - Key performance indicators in {vertical_name}: {metrics}
        - User adoption metrics
        - Business viability indicators

        STEP 6: STARTING POINTS
        - 2-3 specific product concepts with clear value propositions
        - Research areas to explore first
        - Potential partners or stakeholders
        - Initial validation approaches

        Be specific to {vertical_name}, directly responsive to the query, and provide actionable guidance based ONLY on your knowledge.
        """
        
        # Generate insights using only Gemini's knowledge
        response = gemini_model.generate_content(prompt)
        insights = response.text.strip() if response.text else ""
        
        return jsonify({
            "vertical": vertical,
            "vertical_name": vertical_name,
            "query": query,
            "insights": insights
        })
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500