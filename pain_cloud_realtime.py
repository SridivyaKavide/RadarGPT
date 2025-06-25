from flask import Blueprint, request, jsonify, render_template
from scrapers import ScraperManager
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from config import PERSONA_SOURCES
import json
from keyword_utils import extract_top_keywords
from functools import lru_cache
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
pain_cloud_realtime_bp = Blueprint('pain_cloud_realtime', __name__)

# Initialize scraper manager
scraper_manager = ScraperManager()

# Cache for storing results
cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 3600  # 1 hour

@lru_cache(maxsize=100)
def get_cached_data(persona, mode):
    """Get cached data with thread safety"""
    with cache_lock:
        cache_key = f"{persona}_{mode}"
        if cache_key in cache:
            timestamp, data = cache[cache_key]
            if time.time() - timestamp < CACHE_EXPIRY:
                return data
    return None

def set_cached_data(persona, mode, data):
    """Set cached data with thread safety"""
    with cache_lock:
        cache_key = f"{persona}_{mode}"
        cache[cache_key] = (time.time(), data)

@pain_cloud_realtime_bp.route('/')
def pain_cloud_realtime():
    """Render the pain cloud realtime page."""
    return render_template('pain_cloud_realtime.html')

@pain_cloud_realtime_bp.route('/api', methods=['POST'])
def pain_cloud_realtime_api():
    """API endpoint for pain cloud realtime data."""
    try:
        # Ensure request has JSON content
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()
        persona = data.get('persona')
        mode = data.get('mode', 'real')  # 'real' or 'AI themes'
        
        if not persona:
            return jsonify({'error': 'Persona is required'}), 400
            
        if persona not in PERSONA_SOURCES:
            return jsonify({'error': 'Invalid persona'}), 400

        # Check cache first
        cached_data = get_cached_data(persona, mode)
        if cached_data:
            return jsonify(cached_data)

        # Scrape data from all sources concurrently with timeout
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(scraper_manager.scrape_reddit, persona): 'reddit',
                executor.submit(scraper_manager.scrape_stackoverflow, persona): 'stackoverflow',
                executor.submit(scraper_manager.scrape_complaintsboard, persona): 'complaintsboard',
                executor.submit(scraper_manager.get_google_trends, persona): 'trends'
            }
            
            results = {}
            for future in as_completed(futures, timeout=20):  # 20 second timeout
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as e:
                    logger.error(f"Error fetching {source} data: {e}")
                    results[source] = []

        # Process data in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Process complaints
            complaints_future = executor.submit(process_complaints, results)
            # Process keywords
            keywords_future = executor.submit(process_keywords, results, persona)
            
            all_complaints = complaints_future.result()
            keywords_data = keywords_future.result()

        # Prepare response data
        if mode == 'real':
            response_data = {
                'complaints': all_complaints[:10],  # Top 10 most negative complaints
                'keywords': keywords_data['trends'],
                'relevant_keywords': keywords_data['combined'][:15],
                'mode': 'real'
            }
        else:
            # Generate AI themes
            summary = scraper_manager.generate_summary(persona, all_complaints)
            response_data = {
                'themes': summary,
                'keywords': keywords_data['trends'],
                'relevant_keywords': keywords_data['combined'][:15],
                'mode': 'AI themes'
            }

        # Cache the response
        set_cached_data(persona, mode, response_data)
        
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error in pain_cloud_realtime_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_complaints(results):
    """Process complaints data in parallel"""
    all_complaints = []
    all_texts = []
    
    # Process Reddit data
    for post in results.get('reddit', []):
        all_complaints.append({
            'source': 'reddit',
            'title': post['title'],
            'text': post['text'],
            'score': post['score'],
            'url': post['url'],
            'emotional_score': post['emotional_score']
        })
        all_texts.append(post['title'] + ' ' + post['text'])
    
    # Process Stack Overflow data
    for question in results.get('stackoverflow', []):
        all_complaints.append({
            'source': 'stackoverflow',
            'title': question['title'],
            'text': question['text'],
            'score': question['score'],
            'url': question['url'],
            'emotional_score': question['emotional_score']
        })
        all_texts.append(question['title'] + ' ' + question['text'])
    
    # Process ComplaintsBoard data
    for complaint in results.get('complaintsboard', []):
        all_complaints.append({
            'source': 'complaintsboard',
            'title': complaint['title'],
            'text': complaint['text'],
            'score': 0,
            'url': complaint['url'],
            'emotional_score': complaint['emotional_score']
        })
        all_texts.append(complaint['title'] + ' ' + complaint['text'])
    
    # Sort complaints by emotional score
    all_complaints.sort(key=lambda x: x['emotional_score'])
    return all_complaints

def process_keywords(results, persona):
    """Process keywords data in parallel"""
    # Extract top keywords from all collected texts
    relevant_keywords = extract_top_keywords(results.get('all_texts', []), top_n=12)
    
    # Add persona/industry keywords and Google Trends keywords
    persona_keywords = PERSONA_SOURCES[persona]['keywords']
    trends_keywords = [k['keyword'] for k in results.get('trends', [])] if isinstance(results.get('trends'), list) else []
    
    # Combine and deduplicate, prioritizing extracted keywords
    combined_keywords = list(dict.fromkeys(relevant_keywords + persona_keywords + trends_keywords))
    
    return {
        'trends': results.get('trends', []),
        'combined': combined_keywords
    }