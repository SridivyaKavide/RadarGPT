"""
This file contains the updates to be added to app.py
"""

# Import new modules
from data_sources import data_source_manager
from analytics import TrendAnalytics
from collaboration import CollaborationManager
from integrations import integration_manager
from vertical_insights import vertical_insights

# Initialize modules with app context
def init_modules(app, db):
    # Initialize analytics
    trend_analytics = TrendAnalytics(db)
    
    # Initialize collaboration
    collab_manager = CollaborationManager(db)
    collab_models = collab_manager.setup_models()
    
    return {
        'trend_analytics': trend_analytics,
        'collab_manager': collab_manager,
        'collab_models': collab_models
    }

# New routes to add to app.py
def add_routes(app, db, modules):
    trend_analytics = modules['trend_analytics']
    collab_manager = modules['collab_manager']
    
    @app.route('/api/competitors/<keyword>')
    @login_required
    def get_competitors(keyword):
        comp_data = trend_analytics.get_competitive_analysis(keyword)
        if not comp_data:
            return jsonify({"error": "No data available"}), 404
        return jsonify(comp_data)
    
    @app.route('/api/teams', methods=['GET', 'POST'])
    @login_required
    def teams():
        if request.method == 'POST':
            data = request.json
            name = data.get('name')
            if not name:
                return jsonify({"error": "Team name required"}), 400
            return collab_manager.create_team(name)
        else:
            # Get user's teams
            Team = modules['collab_models']['Team']
            TeamMember = modules['collab_models']['TeamMember']
            
            teams = db.session.query(Team).join(
                TeamMember, Team.id == TeamMember.team_id
            ).filter(
                TeamMember.user_id == current_user.id
            ).all()
            
            return jsonify({
                "teams": [{
                    "id": team.id,
                    "name": team.name,
                    "created_at": team.created_at.isoformat()
                } for team in teams]
            })
    
    @app.route('/api/teams/<int:team_id>/members', methods=['GET', 'POST'])
    @login_required
    def team_members(team_id):
        if request.method == 'POST':
            data = request.json
            username = data.get('username')
            if not username:
                return jsonify({"error": "Username required"}), 400
            return collab_manager.add_team_member(team_id, username)
        else:
            # Get team members
            TeamMember = modules['collab_models']['TeamMember']
            User = db.Model.User
            
            members = db.session.query(
                User.id, User.username, TeamMember.role
            ).join(
                TeamMember, User.id == TeamMember.user_id
            ).filter(
                TeamMember.team_id == team_id
            ).all()
            
            return jsonify({
                "members": [{
                    "id": member[0],
                    "username": member[1],
                    "role": member[2]
                } for member in members]
            })
    
    @app.route('/api/share/<int:query_id>', methods=['POST'])
    @login_required
    def share_query(query_id):
        data = request.json
        team_id = data.get('team_id')
        if not team_id:
            return jsonify({"error": "Team ID required"}), 400
        return collab_manager.share_query(query_id, team_id)
    
    @app.route('/api/comments/<int:query_id>', methods=['GET', 'POST'])
    @login_required
    def comments(query_id):
        if request.method == 'POST':
            data = request.json
            text = data.get('text')
            if not text:
                return jsonify({"error": "Comment text required"}), 400
            return collab_manager.add_comment(query_id, text)
        else:
            return collab_manager.get_comments(query_id)
    
    @app.route('/api/integrations/jira', methods=['POST'])
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
    
    @app.route('/api/integrations/trello', methods=['POST'])
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
    
    @app.route('/api/integrations/slack', methods=['POST'])
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
    
    @app.route('/api/verticals')
    def get_verticals():
        return jsonify(vertical_insights.get_all_verticals())
    
    @app.route('/api/verticals/<vertical>/<keyword>', methods=['POST'])
    @login_required
    def get_vertical_insights(vertical, keyword):
        data = request.json
        content = data.get('content', '')
        
        insights = vertical_insights.get_vertical_insights(
            vertical, keyword, content
        )
        
        return jsonify(insights)
    
    # Enhanced multi_search to include new data sources
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
                        results = data_source_manager.get_twitter_posts(keyword, max_posts=30)
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
                        results = data_source_manager.get_app_store_reviews(app_id, max_reviews=20)
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
                        # Example forum URL - would have multiple in production
                        forum_url = "https://community.khoros.com/forgerock"
                        results = data_source_manager.get_industry_forum_posts(
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