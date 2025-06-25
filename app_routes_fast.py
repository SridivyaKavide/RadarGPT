from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from fast_radar import fast_radar
from app import db, SearchQuery, QueryChat
import datetime
import google.generativeai as genai
import os

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")  # Using faster model

# Create blueprint
fast_routes = Blueprint('fast_routes', __name__)

@fast_routes.route('/fast_search', methods=['POST'])
@login_required
def fast_search():
    """
    Endpoint for fast multi-source search with optimized results
    """
    try:
        data = request.get_json()
        keyword = data.get("keyword", "").strip()
        
        if not keyword:
            return jsonify({"error": "Missing keyword"}), 400
        
        # Perform fast search
        response = fast_radar.search(keyword, user_id=current_user.id, db=db)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@fast_routes.route('/fast_status')
def fast_status():
    """
    Check the status of a fast search operation
    """
    keyword = request.args.get('keyword', '')
    status = fast_radar.get_status(keyword)
    return jsonify({"status": status})

@fast_routes.route('/fast_chat/<int:query_id>', methods=['POST'])
@login_required
def fast_chat(query_id):
    """
    Fast chat functionality for follow-up questions
    """
    query = SearchQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    user_text = data.get('text', '').strip()
    if not user_text:
        return jsonify({"error": "Empty input"}), 400

    # Save user message
    user_msg = QueryChat(query_id=query_id, role='user', text=user_text)
    db.session.add(user_msg)

    # Use the optimized follow-up prompt from fast_summarizer
    from fast_summarizer import fast_summarizer
    bot_response = fast_summarizer.answer_followup(
        summary=query.result or "No summary available.",
        keyword=query.keyword,
        question=user_text
    )

    # Save bot response
    bot_msg = QueryChat(query_id=query_id, role='model', text=bot_response)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"bot_reply": bot_response})

@fast_routes.route('/fast_radargpt')
@login_required
def fast_radargpt():
    """
    Fast RadarGPT UI page
    """
    # Only send IDs and keywords to the template
    queries = SearchQuery.query.filter_by(user_id=current_user.id)\
        .order_by(SearchQuery.timestamp.desc()).all()
    return render_template('fast_radargpt.html', queries=queries)

@fast_routes.route('/fast_vertical/<vertical>/<query>', methods=['POST'])
@login_required
def fast_vertical_insights(vertical, query):
    """
    Fast vertical-specific insights using only Gemini's knowledge
    """
    try:
        from vertical_insights import vertical_insights as vi
        from fast_summarizer import fast_summarizer
        
        # Get vertical data
        if vertical not in vi.VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = vi.VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        
        # Generate insights using only Gemini's knowledge
        insights = fast_summarizer.summarize_vertical(
            content="",  # No content needed, using only Gemini's knowledge
            keyword=query,
            vertical_name=vertical_name,
            regulations=vertical_data['regulations'],
            metrics=vertical_data['metrics']
        )
        
        return jsonify({
            "vertical": vertical,
            "vertical_name": vertical_name,
            "query": query,
            "insights": insights
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@fast_routes.route('/fast_trends/<query>', methods=['POST'])
@login_required
def fast_trends(query):
    """
    Fast trend analysis
    """
    try:
        from fast_summarizer import fast_summarizer
        
        # Use the existing fast search to get data
        search_results = fast_radar.search(query)
        
        # Collect all content from the search results
        all_content = ""
        for source_name, source_data in search_results["sources"].items():
            if isinstance(source_data, list):
                for item in source_data:
                    if isinstance(item, dict):
                        title = item.get('title', '')
                        text = item.get('text', '') or item.get('description', '') or item.get('selftext', '')
                        all_content += f"{title}\n{text}\n\n"
        
        # Generate trend insights using the optimized trend prompt
        insights = fast_summarizer.summarize_trends(
            content=all_content,
            keyword=query
        )
        
        return jsonify({
            "query": query,
            "insights": insights
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500