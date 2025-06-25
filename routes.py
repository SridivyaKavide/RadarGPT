from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, SearchQuery
from data_sources import data_source_manager
from twitter_source import twitter_source
from app_store_source import app_store_source
from industry_forum_source import industry_forum_source
from analytics import TrendAnalytics
from vertical_insights import vertical_insights
from integrations import integration_manager

# Create Blueprint
bp = Blueprint('new_features', __name__)

# Initialize analytics
trend_analytics = TrendAnalytics(db)

# Routes for verticals and pain dashboard
@bp.route('/verticals')
@login_required
def verticals_page():
    """Render the vertical insights page"""
    return render_template('vertical_insights.html')

@bp.route('/pain-dashboard')
@login_required
def pain_dashboard():
    """Render the pain dashboard page"""
    return render_template('pain_dashboard.html')

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
    comp_data = trend_analytics.get_competitive_analysis(keyword)
    if not comp_data:
        return jsonify({"error": "No data available"}), 404
    return jsonify(comp_data)

@bp.route('/api/verticals')
def get_verticals():
    """Get list of all supported verticals"""
    return jsonify(vertical_insights.get_all_verticals())

@bp.route('/api/verticals/<vertical>/<keyword>', methods=['POST'])
@login_required
def get_vertical_insights(vertical, keyword):
    """Get vertical-specific insights"""
    data = request.json
    content = data.get('content', '')
    
    insights = vertical_insights.get_vertical_insights(
        vertical, keyword, content
    )
    
    return jsonify(insights)

@bp.route('/analyze/<vertical>/<query>', methods=['POST'])
@login_required
def analyze_vertical(vertical, query):
    """Get vertical-specific insights with structured data"""
    try:
        # Get vertical data
        if vertical not in vertical_insights.VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = vertical_insights.VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        regulations = ", ".join(vertical_data["regulations"])
        metrics = ", ".join(vertical_data["metrics"])
        
        # Create prompt for structured analysis
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
        
        # Generate insights
        response = gemini_model.generate_content(prompt)
        insights_text = response.text.strip() if response.text else ""
        
        # Parse JSON response
        try:
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
        except json.JSONDecodeError:
            return jsonify({
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "insights": insights_text,
                "error": "Could not parse structured insights"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/integrations/jira', methods=['POST'])
@login_required
def create_jira():
    data = request.json
    project_key = data.get('project_key')
    summary = data.get('summary')
    description = data.get('description')
    issue_type = data.get('issue_type', 'Task')
    
    if not all([project_key, summary, description]):
        return jsonify({"error": "Missing required fields"}), 400
        
    return integration_manager.create_jira_issue(
        project_key, summary, description, issue_type
    )

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
        
    return integration_manager.create_trello_card(
        board_id, list_id, name, description
    )

@bp.route('/api/integrations/slack', methods=['POST'])
@login_required
def send_slack():
    data = request.json
    channel = data.get('channel')
    summary = data.get('summary')
    details_url = data.get('details_url')
    
    if not all([channel, summary, details_url]):
        return jsonify({"error": "Missing required fields"}), 400
        
    return integration_manager.send_to_slack(
        channel, summary, details_url
    )

# Function to register all routes with the main app
def register_routes(app):
    app.register_blueprint(bp)
    
    # Update the multi_search route to include new data sources
    @app.route("/multi_search", methods=['POST'])
    @login_required
    def multi_search():
        try:
            data = request.get_json()
            keyword = data.get("keyword", "").strip()
            mode = data.get("mode", "future_pain")
            vertical = data.get("vertical", "")  # Optional vertical
            
            if not keyword:
                return jsonify({"error": "Missing keyword"}), 400
            
            sources = {
                "Reddit": [],
                "Stack Overflow": [],
                "ComplaintsBoard": [],
                "Product Hunt": [],
                "Twitter": [],  # New source
                "App Store": [],  # New source
                "Industry Forums": []  # New source
            }
            
            errors = {}
            
            # Use ThreadPoolExecutor to fetch data from all sources in parallel
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=7) as executor:
                # Define jobs for each source
                def reddit_job():
                    try:
                        results = data_source_manager.get_reddit_posts(keyword, max_posts=5)
                        sources["Reddit"] = [{
                            "title": r["title"], 
                            "url": r["url"], 
                            "text": r["selftext"]
                        } for r in results]
                    except Exception as e:
                        errors["Reddit"] = str(e)
                        sources["Reddit"] = []
                
                def stackoverflow_job():
                    try:
                        from app import search_stackoverflow
                        results = search_stackoverflow(keyword, max_pages=2, pagesize=25)
                        sources["Stack Overflow"] = [{
                            "title": s["title"], 
                            "url": s["link"], 
                            "text": ""
                        } for s in results]
                    except Exception as e:
                        errors["Stack Overflow"] = str(e)
                        sources["Stack Overflow"] = []
                
                def complaints_job():
                    try:
                        from app import scrape_complaintsboard_full_text
                        results = scrape_complaintsboard_full_text(keyword, max_pages=20)
                        sources["ComplaintsBoard"] = [{
                            "title": c["title"], 
                            "url": c["url"], 
                            "text": ""
                        } for c in results]
                    except Exception as e:
                        errors["ComplaintsBoard"] = str(e)
                        sources["ComplaintsBoard"] = []
                
                def producthunt_job():
                    try:
                        from app import scrape_producthunt_products
                        results = scrape_producthunt_products(keyword, max_pages=3, max_products=30)
                        sources["Product Hunt"] = [{
                            "title": p["title"], 
                            "url": p["url"], 
                            "text": p["description"]
                        } for p in results]
                    except Exception as e:
                        errors["Product Hunt"] = str(e)
                        sources["Product Hunt"] = []
                
                def twitter_job():
                    try:
                        results = twitter_source.get_twitter_posts(keyword, max_posts=30)
                        sources["Twitter"] = [{
                            "title": f"Tweet by @{t['user']}", 
                            "url": t["url"], 
                            "text": t["text"]
                        } for t in results]
                    except Exception as e:
                        errors["Twitter"] = str(e)
                        sources["Twitter"] = []
                
                def appstore_job():
                    try:
                        # For demo, use a popular app ID related to keyword
                        # In production, would search for relevant app IDs first
                        app_id = "389801252"  # Instagram as example
                        results = app_store_source.get_app_store_reviews(app_id, max_reviews=20)
                        sources["App Store"] = [{
                            "title": f"Review: {r['title']}", 
                            "url": "", 
                            "text": r["content"],
                            "rating": r["rating"]
                        } for r in results]
                    except Exception as e:
                        errors["App Store"] = str(e)
                        sources["App Store"] = []
                
                def forums_job():
                    try:
                        # Use vertical-specific forums if available
                        if vertical in industry_forum_source.forums:
                            results = industry_forum_source.get_forum_posts_by_vertical(
                                vertical, keyword, max_posts=20
                            )
                        else:
                            # Example forum URL - would have multiple in production
                            forum_url = "https://community.khoros.com/forgerock"
                            results = industry_forum_source.get_industry_forum_posts(
                                forum_url, keyword, max_posts=20
                            )
                        sources["Industry Forums"] = [{
                            "title": r["title"], 
                            "url": r["url"], 
                            "text": r.get("excerpt", "")
                        } for r in results]
                    except Exception as e:
                        errors["Industry Forums"] = str(e)
                        sources["Industry Forums"] = []
                
                # Submit all jobs
                futures = [
                    executor.submit(reddit_job),
                    executor.submit(stackoverflow_job),
                    executor.submit(complaints_job),
                    executor.submit(producthunt_job),
                    executor.submit(twitter_job),
                    executor.submit(appstore_job),
                    executor.submit(forums_job),
                ]
                
                # Wait for all to complete
                for future in as_completed(futures):
                    future.result()
            
            # Combine all sources for analysis
            all_posts = []
            for src_name, src_data in sources.items():
                all_posts.extend(src_data)
            
            # Get the appropriate prompt based on mode
            from app import MODE_PROMPTS, groq_summarize_with_citations
            prompt_prefix = MODE_PROMPTS.get(mode, MODE_PROMPTS["future_pain"])
            
            # If vertical is specified, add vertical-specific context
            if vertical and vertical in vertical_insights.VERTICALS:
                v_data = vertical_insights.VERTICALS[vertical]
                prompt_prefix += f"\n\nThis analysis is specifically for the {v_data['name']} industry. "
                prompt_prefix += f"Consider industry-specific metrics like {', '.join(v_data['metrics'][:3])} "
                prompt_prefix += f"and regulations like {', '.join(v_data['regulations'][:3])}."
            
            # Generate summary with citations
            summary = groq_summarize_with_citations(all_posts, prompt_prefix)
            
            # Save to database
            new_query = SearchQuery(
                keyword=keyword,
                source="multi",
                mode=mode,
                result=summary,
                user_id=current_user.id,
                vertical=vertical if vertical else None
            )
            db.session.add(new_query)
            db.session.commit()
            
            # Get trend data if available
            trend_data = trend_analytics.get_trend_data(keyword, days=90)
            chart_image = None
            if trend_data:
                chart_image = trend_analytics.generate_trend_chart(trend_data)
            
            return jsonify({
                "summary": summary,
                "sources": sources,
                "query_id": new_query.id,
                "errors": errors if errors else None,
                "trend_data": trend_data,
                "chart_image": chart_image,
                "vertical": vertical if vertical else None
            })
        
        except Exception as e:
            return jsonify({"error": f"Server error: {str(e)}"}), 500