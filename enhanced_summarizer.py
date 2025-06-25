import os
import google.generativeai as genai
from diskcache import Cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

class EnhancedSummarizer:
    """Provides enhanced summarization capabilities for RadarGPT"""
    
    def __init__(self):
        pass
        
    def summarize_stackoverflow(self, content_list):
        """
        Summarize StackOverflow content with focused insights on technical problems and solutions
        """
        cache_key = f"summary_stackoverflow_{hash(str(content_list))}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        # Create a structured prompt for StackOverflow content
        sources_str = ""
        for idx, item in enumerate(content_list, 1):
            sources_str += f"[{idx}] {item['title']} ({item.get('url','')})\n"
            
        content_str = "\n\n".join([
            f"TITLE: {item['title']}\n"
            f"TAGS: {', '.join(item.get('tags', []))}\n"
            f"CONTENT: {item.get('text','')}\n"
            f"SCORE: {item.get('score', 0)} | ANSWERS: {item.get('answer_count', 0)} | ANSWERED: {'Yes' if item.get('is_answered', False) else 'No'}"
            for item in content_list
        ])
        
        prompt = f"""
        You are a technical expert analyzing StackOverflow questions and answers about a specific topic.
        
        Analyze these StackOverflow posts to extract the most valuable technical insights:
        
        1. MOST COMMON TECHNICAL PROBLEMS:
           - Identify the top 5-7 recurring technical issues or challenges
           - For each problem, note its frequency and severity
           - Include specific error messages, bugs, or limitations mentioned
        
        2. SOLUTION PATTERNS:
           - Identify the most effective solutions mentioned across posts
           - Note which solutions have the highest community approval (upvotes)
           - Highlight any official documentation or best practices referenced
        
        3. TECHNICAL LIMITATIONS & WORKAROUNDS:
           - Identify fundamental limitations of the technology/approach
           - Note clever workarounds developers have found
           - Highlight any performance implications or tradeoffs
        
        4. EMERGING TRENDS & ALTERNATIVES:
           - Note any newer approaches or alternatives being discussed
           - Identify if developers are moving away from certain methods
           - Highlight any upcoming features or changes mentioned
        
        5. EXPERT RECOMMENDATIONS:
           - Based on the collective wisdom, what are the top 3 recommendations?
           - What common mistakes should developers avoid?
           - What resources were most frequently recommended?
        
        After each insight, add a citation in the form [n] that refers to the n-th source in the list below.
        Only use citations for facts you can attribute to a specific source.
        
        Sources:
        {sources_str}
        
        Content:
        {content_str}
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing StackOverflow content: {e}")
            return f"Error generating summary: {str(e)}"
    
    def summarize_reddit(self, content_list):
        """
        Summarize Reddit content with focus on user experiences and pain points
        """
        cache_key = f"summary_reddit_{hash(str(content_list))}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        # Create a structured prompt for Reddit content
        sources_str = ""
        for idx, item in enumerate(content_list, 1):
            sources_str += f"[{idx}] {item['title']} (r/{item.get('subreddit','')}) - {item.get('permalink','')}\n"
            
        content_str = "\n\n".join([
            f"POST: {item['title']}\n"
            f"SUBREDDIT: r/{item.get('subreddit', '')}\n"
            f"CONTENT: {item.get('selftext', '')}\n"
            f"COMMENTS: " + "\n".join([f"- {c.get('text', '')}" for c in item.get('comments', [])[:5]])
            for item in content_list
        ])
        
        prompt = f"""
        You are a market researcher analyzing Reddit discussions to extract user sentiment and pain points.
        
        Analyze these Reddit posts and comments to extract the most valuable insights:
        
        1. USER PAIN POINTS:
           - Identify the top 5-7 recurring problems or frustrations
           - Note the emotional intensity of each pain point (mild, moderate, severe)
           - Include specific examples or quotes that illustrate each pain point
        
        2. USER NEEDS & DESIRES:
           - What are users explicitly asking for or wishing existed?
           - What features or solutions do they value most?
           - What workarounds are they currently using?
        
        3. SENTIMENT ANALYSIS:
           - What's the overall sentiment toward the topic/product?
           - Are there specific aspects that generate positive vs. negative reactions?
           - Note any shifts in sentiment over time if apparent
        
        4. COMPETITIVE INSIGHTS:
           - What alternatives or competitors are users mentioning?
           - What do they like/dislike about these alternatives?
           - Are users switching from/to other solutions? Why?
        
        5. EMERGING TRENDS:
           - What new concerns or interests are appearing in discussions?
           - Are there changing patterns in how users talk about the topic?
           - What predictions or expectations do users have for the future?
        
        After each insight, add a citation in the form [n] that refers to the n-th source in the list below.
        Only use citations for facts you can attribute to a specific source.
        
        Sources:
        {sources_str}
        
        Content:
        {content_str}
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing Reddit content: {e}")
            return f"Error generating summary: {str(e)}"
    
    def summarize_complaintsboard(self, content_list):
        """
        Summarize ComplaintsBoard content with focus on customer complaints and issues
        """
        cache_key = f"summary_complaintsboard_{hash(str(content_list))}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        # Create a structured prompt for ComplaintsBoard content
        sources_str = ""
        for idx, item in enumerate(content_list, 1):
            sources_str += f"[{idx}] {item['title']} ({item.get('url','')})\n"
            
        content_str = "\n\n".join([
            f"COMPLAINT: {item['title']}\n"
            f"CONTENT: {item.get('text', '')}"
            for item in content_list
        ])
        
        prompt = f"""
        You are a customer experience analyst reviewing customer complaints to identify patterns and insights.
        
        Analyze these customer complaints to extract the most valuable insights:
        
        1. MAJOR COMPLAINT CATEGORIES:
           - Identify the top 5-7 categories of complaints
           - For each category, note its frequency and severity
           - Include specific examples that illustrate each category
        
        2. ROOT CAUSES:
           - What are the underlying causes of these complaints?
           - Are there systemic issues vs. one-off problems?
           - What triggers customer dissatisfaction most frequently?
        
        3. CUSTOMER EXPECTATIONS:
           - What were customers expecting that wasn't delivered?
           - What specific promises or claims do customers feel were broken?
           - What would have prevented these complaints?
        
        4. RESOLUTION ATTEMPTS:
           - How have customers tried to resolve their issues?
           - What communication channels did they use?
           - What was their experience with customer service?
        
        5. BUSINESS IMPACT:
           - How are these issues affecting customer loyalty?
           - Are customers mentioning switching to competitors?
           - What reputational damage is occurring?
        
        After each insight, add a citation in the form [n] that refers to the n-th source in the list below.
        Only use citations for facts you can attribute to a specific source.
        
        Sources:
        {sources_str}
        
        Content:
        {content_str}
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing ComplaintsBoard content: {e}")
            return f"Error generating summary: {str(e)}"
    
    def summarize_producthunt(self, content_list):
        """
        Summarize ProductHunt content with focus on product features and market gaps
        """
        cache_key = f"summary_producthunt_{hash(str(content_list))}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        # Create a structured prompt for ProductHunt content
        sources_str = ""
        for idx, item in enumerate(content_list, 1):
            sources_str += f"[{idx}] {item['title']} ({item.get('url','')})\n"
            
        content_str = "\n\n".join([
            f"PRODUCT: {item['title']}\n"
            f"DESCRIPTION: {item.get('description', '')}"
            for item in content_list
        ])
        
        prompt = f"""
        You are a product strategist analyzing the competitive landscape of products in a specific market.
        
        Analyze these ProductHunt products to extract the most valuable insights:
        
        1. PRODUCT LANDSCAPE:
           - Identify the main categories or types of products in this space
           - Note how saturated each category appears to be
           - Highlight any unique or standout approaches
        
        2. FEATURE PATTERNS:
           - What features appear most frequently across products?
           - What unique features differentiate certain products?
           - What feature gaps or opportunities exist in the market?
        
        3. VALUE PROPOSITIONS:
           - What core problems are these products solving?
           - How are they positioning their solutions?
           - What customer segments are they targeting?
        
        4. MARKET TRENDS:
           - What emerging technologies or approaches are being adopted?
           - Are products moving toward certain features or capabilities?
           - What seems to be the direction of innovation in this space?
        
        5. OPPORTUNITY GAPS:
           - What unaddressed needs or underserved segments exist?
           - What feature combinations aren't currently available?
           - Where could a new entrant potentially differentiate?
        
        After each insight, add a citation in the form [n] that refers to the n-th source in the list below.
        Only use citations for facts you can attribute to a specific source.
        
        Sources:
        {sources_str}
        
        Content:
        {content_str}
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing ProductHunt content: {e}")
            return f"Error generating summary: {str(e)}"
    
    def generate_combined_summary(self, stackoverflow_summary, reddit_summary, complaintsboard_summary, producthunt_summary, keyword):
        """
        Generate a comprehensive summary combining insights from all sources
        """
        cache_key = f"summary_combined_{hash(stackoverflow_summary + reddit_summary + complaintsboard_summary + producthunt_summary)}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        prompt = f"""
        You are a strategic advisor synthesizing insights from multiple data sources about "{keyword}".
        
        Below are summaries from different platforms. Create a comprehensive analysis that integrates these insights:
        
        1. MOST CRITICAL PAIN POINTS:
           - Identify the top 5-7 problems that appear across multiple sources
           - Rate each on severity (1-10) and frequency (1-10)
           - Note which user segments are most affected by each
        
        2. MARKET GAPS & OPPORTUNITIES:
           - Where are current solutions falling short?
           - What specific needs remain unaddressed?
           - What combination of features would create a compelling new solution?
        
        3. COMPETITIVE LANDSCAPE:
           - What types of solutions currently exist?
           - What are their strengths and limitations?
           - Where are the opportunities for differentiation?
        
        4. EMERGING TRENDS:
           - What shifts in user needs or expectations are occurring?
           - What technological or market trends are influencing this space?
           - What's likely to change in the next 6-12 months?
        
        5. STRATEGIC RECOMMENDATIONS:
           - What are the 3-5 most promising opportunities?
           - For each, outline the core value proposition and target audience
           - What would be the key features needed to succeed?
        
        STACKOVERFLOW INSIGHTS:
        {stackoverflow_summary}
        
        REDDIT INSIGHTS:
        {reddit_summary}
        
        COMPLAINTS INSIGHTS:
        {complaintsboard_summary}
        
        PRODUCT HUNT INSIGHTS:
        {producthunt_summary}
        """
        
        try:
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error generating combined summary: {e}")
            return f"Error generating summary: {str(e)}"

# Create singleton instance
enhanced_summarizer = EnhancedSummarizer()