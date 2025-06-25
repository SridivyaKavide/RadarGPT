from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from enhanced_radar import enhanced_radar
from app import db, SearchQuery, QueryChat
import datetime
import google.generativeai as genai
import os

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Create blueprint
enhanced_routes = Blueprint('enhanced_routes', __name__)

@enhanced_routes.route('/enhanced_search', methods=['POST'])
@login_required
def enhanced_search():
    """
    Endpoint for enhanced multi-source search with optimized results
    """
    try:
        data = request.get_json()
        keyword = data.get("keyword", "").strip()
        
        if not keyword:
            return jsonify({"error": "Missing keyword"}), 400
        
        # Perform enhanced search
        response = enhanced_radar.search(keyword, user_id=current_user.id, db=db)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@enhanced_routes.route('/enhanced_status')
def enhanced_status():
    """
    Check the status of an enhanced search operation
    """
    keyword = request.args.get('keyword', '')
    status = enhanced_radar.get_status(keyword)
    return jsonify({"status": status})

@enhanced_routes.route('/enhanced_chat/<int:query_id>', methods=['POST'])
@login_required
def enhanced_chat(query_id):
    """
    Enhanced chat functionality for follow-up questions
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

    # Create context with original query and summary
    base_context = {
        "role": "user",
        "parts": [f"""This is a follow-up question based on the enhanced radar summary below.

Original query keyword: {query.keyword}

Original result summary:
{query.result or "No summary available."}

Follow-up question: {user_text}"""]
    }
    
    # Add chat history
    chat_history = []
    for m in query.chats:
        role = "user" if m.role == "user" else "model"
        chat_history.append({"role": role, "parts": [m.text]})
    full_history = [base_context] + chat_history

    try:
        # Use Gemini for chat
        chat = gemini_model.start_chat(history=full_history)
        bot_response = chat.send_message(user_text).text.strip()
    except Exception as e:
        bot_response = f"Error: {e}"

    # Save bot response
    bot_msg = QueryChat(query_id=query_id, role='model', text=bot_response)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"bot_reply": bot_response})

@enhanced_routes.route('/enhanced_radargpt')
@login_required
def enhanced_radargpt():
    """
    Enhanced RadarGPT UI page
    """
    # Only send IDs and keywords to the template
    queries = SearchQuery.query.filter_by(user_id=current_user.id)\
        .order_by(SearchQuery.timestamp.desc()).all()
    return render_template('enhanced_radargpt.html', queries=queries)

@enhanced_routes.route('/enhanced_query/<int:query_id>')
@login_required
def enhanced_query(query_id):
    """
    Get enhanced query details
    """
    query = SearchQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({
        "id": query.id,
        "keyword": query.keyword,
        "summary": query.result,
        "timestamp": query.timestamp.isoformat()
    })