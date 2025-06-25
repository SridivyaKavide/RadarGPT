from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db  # Import db from the original app
import os
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Create Blueprint
bp = Blueprint('new_features', __name__)

# Routes for new features
@bp.route('/verticals')
@login_required
def verticals_page():
    return render_template('vertical_insights.html')

@bp.route('/teams')
@login_required
def teams_page():
    return render_template('team_collaboration.html')

@bp.route('/integrations')
@login_required
def integrations_page():
    return render_template('integrations.html')

# API Routes
@bp.route('/api/competitors/<keyword>')
@login_required
def get_competitors(keyword):
    try:
        competitor_data = trend_analytics.get_competitive_analysis(keyword)
        if not competitor_data:
            return jsonify({"error": f"No competitor data found for '{keyword}'"}), 404
        return jsonify(competitor_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/verticals')
def get_verticals():
    # Return list of supported verticals
    verticals = {
        "fintech": "Financial Technology",
        "healthcare": "Healthcare & Medical",
        "ecommerce": "E-Commerce & Retail",
        "saas": "Software as a Service",
        "edtech": "Education Technology"
    }
    return jsonify(verticals)

@bp.route('/api/verticals/<vertical>/<keyword>', methods=['POST'])
@login_required
def get_vertical_insights(vertical, keyword):
    data = request.json
    content = data.get('content', '')
    
    # Use Gemini to generate insights
    prompt = f"""
    You are an expert market analyst specializing in {vertical}.
    
    Analyze this keyword "{keyword}" from a {vertical} industry perspective.
    
    Provide insights in these specific areas:
    
    1. Industry-Specific Pain Points:
       - Identify pain points specific to the {vertical} industry
       - Rate severity on scale of 1-10
       - Note if these are emerging or established problems
    
    2. Regulatory & Compliance Considerations:
       - Identify any relevant regulatory concerns
       - Note compliance challenges that create opportunities
    
    3. Key Performance Indicators:
       - Which metrics matter most for solutions in this space
       - How solutions should measure success
    
    4. Competitive Landscape:
       - Identify key players in this specific vertical
       - Note gaps in their offerings
    
    5. Vertical-Specific Opportunities:
       - Suggest 2-3 specific product ideas tailored to {vertical}
       - For each, note target user, core value proposition, and potential go-to-market strategy
    
    Format your response with clear headings and bullet points. Be specific to {vertical} industry.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        insights = response.text.strip()
    except Exception as e:
        insights = f"Error generating insights: {str(e)}"
    
    return jsonify({
        "vertical": vertical,
        "vertical_name": verticals.get(vertical, vertical.capitalize()),
        "insights": insights
    })

@bp.route('/api/teams', methods=['GET', 'POST'])
@login_required
def teams():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({"error": "Team name required"}), 400
        
        # In a real implementation, this would create a team in the database
        return jsonify({
            "success": True, 
            "team_id": 1, 
            "name": name
        }), 201
    else:
        # Return mock teams data
        return jsonify({
            "teams": [
                {
                    "id": 1,
                    "name": "Product Team",
                    "created_at": "2023-01-01T00:00:00"
                },
                {
                    "id": 2,
                    "name": "Marketing Team",
                    "created_at": "2023-01-02T00:00:00"
                }
            ]
        })

@bp.route('/api/teams/<int:team_id>/members', methods=['GET', 'POST'])
@login_required
def team_members(team_id):
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        if not username:
            return jsonify({"error": "Username required"}), 400
        
        # In a real implementation, this would add a member to the team
        return jsonify({"success": True, "username": username}), 201
    else:
        # Return mock members data
        return jsonify({
            "members": [
                {
                    "id": 1,
                    "username": "user1",
                    "role": "admin"
                },
                {
                    "id": 2,
                    "username": "user2",
                    "role": "member"
                }
            ]
        })

@bp.route('/api/integrations/jira', methods=['POST'])
@login_required
def create_jira():
    data = request.json
    project_key = data.get('project_key')
    summary = data.get('summary')
    description = data.get('description')
    
    if not all([project_key, summary, description]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # In a real implementation, this would create a Jira issue
    return jsonify({
        "success": True,
        "issue_key": "DEMO-123",
        "issue_url": f"https://example.atlassian.net/browse/DEMO-123"
    }), 201

@bp.route('/api/integrations/trello', methods=['POST'])
@login_required
def create_trello():
    data = request.json
    board_id = data.get('board_id')
    list_id = data.get('list_id')
    name = data.get('name')
    description = data.get('description')
    
    if not all([board_id, list_id, name, description]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # In a real implementation, this would create a Trello card
    return jsonify({
        "success": True,
        "card_id": "abc123",
        "card_url": "https://trello.com/c/abc123"
    }), 201

@bp.route('/api/integrations/slack', methods=['POST'])
@login_required
def send_slack():
    data = request.json
    channel = data.get('channel')
    summary = data.get('summary')
    details_url = data.get('details_url')
    
    if not all([channel, summary, details_url]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # In a real implementation, this would send a message to Slack
    return jsonify({
        "success": True
    }), 200

# Dictionary of verticals for the vertical insights endpoint
verticals = {
    "fintech": "Financial Technology",
    "healthcare": "Healthcare & Medical",
    "ecommerce": "E-Commerce & Retail",
    "saas": "Software as a Service",
    "edtech": "Education Technology"
}