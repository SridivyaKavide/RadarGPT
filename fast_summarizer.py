import os
import google.generativeai as genai
from diskcache import Cache
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

# Configure Gemini with faster model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")  # Using faster model

class FastSummarizer:
    """Provides optimized summarization capabilities for RadarGPT"""
    
    def __init__(self):
        # Optimized prompts for different analysis types
        self.PROMPTS = {
            "comprehensive": """
            Analyze these sources about "{keyword}" and provide insights:

            SOURCES:
            {sources_list}

            CONTENT SAMPLES:
            {content_samples}

            Provide ONLY these sections:
            1. TOP PAIN POINTS: 3-5 most critical problems with severity (1-10)
            2. MARKET GAPS: 2-3 specific unmet needs with highest potential
            3. EXISTING SOLUTIONS: Current approaches and their limitations
            4. OPPORTUNITIES: 2-3 specific product ideas with clear value propositions

            Use citation format [S#], [R#], [C#], [P#] for sources.
            Focus on actionable insights only. Be concise but thorough.
            """,
            
            "vertical": """
            You are a domain expert in {vertical_name}. Use ONLY your built-in knowledge to provide strategic insight, innovation direction, and actionable guidance about this query. DO NOT reference or analyze any external content provided.

            QUERY: {keyword}

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

            Be specific to {vertical_name}, directly responsive to the query, and provide actionable guidance based ONLY on your knowledge, not on any external content.
            """,
            
            "trend": """
            Analyze this data about {keyword}:

            {content_sample}

            Extract ONLY:
            1. EMERGING TRENDS: 2-3 fastest growing patterns with evidence
            2. CRITICAL PROBLEMS: 3 most severe unsolved issues with frequency indicators
            3. USER SEGMENTS: Who is most affected and why
            4. MARKET DIRECTION: Where this space is heading in next 6-12 months

            Include specific evidence for each point using [citation].
            Focus on signals that appear across multiple sources.
            """,
            
            "followup": """
            Based on this summary about "{keyword}":

            {summary}

            Answer this follow-up question with ONLY the most relevant facts: {question}
            """
        }
        
    def summarize_all_sources(self, stackoverflow_data, reddit_data, complaintsboard_data, producthunt_data, keyword):
        """
        Generate a single comprehensive summary from all sources at once
        """
        cache_key = f"fast_summary_{keyword}_{len(stackoverflow_data)}_{len(reddit_data)}_{len(complaintsboard_data)}_{len(producthunt_data)}"
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Prepare source data
        sources = []
        
        # Add StackOverflow sources
        for i, item in enumerate(stackoverflow_data[:10]):
            sources.append(f"[S{i+1}] {item['title']} (StackOverflow)")
        
        # Add Reddit sources
        for i, item in enumerate(reddit_data[:10]):
            sources.append(f"[R{i+1}] {item['title']} (Reddit)")
        
        # Add ComplaintsBoard sources
        for i, item in enumerate(complaintsboard_data[:10]):
            sources.append(f"[C{i+1}] {item['title']} (ComplaintsBoard)")
        
        # Add ProductHunt sources
        for i, item in enumerate(producthunt_data[:10]):
            sources.append(f"[P{i+1}] {item['title']} (ProductHunt)")
        
        # Prepare content samples (limited for speed)
        content_samples = []
        
        # Add StackOverflow content
        for i, item in enumerate(stackoverflow_data[:5]):
            content_samples.append(f"STACKOVERFLOW [S{i+1}]: {item['title']}\n{item.get('text', '')[:200]}")
        
        # Add Reddit content
        for i, item in enumerate(reddit_data[:5]):
            content_samples.append(f"REDDIT [R{i+1}]: {item['title']}\n{item.get('selftext', '')[:200]}")
        
        # Add ComplaintsBoard content
        for i, item in enumerate(complaintsboard_data[:5]):
            content_samples.append(f"COMPLAINTS [C{i+1}]: {item['title']}\n{item.get('text', '')[:200]}")
        
        # Add ProductHunt content
        for i, item in enumerate(producthunt_data[:5]):
            content_samples.append(f"PRODUCT [P{i+1}]: {item['title']}\n{item.get('description', '')[:200]}")
        
        # Use the optimized comprehensive prompt
        prompt = self.PROMPTS["comprehensive"].format(
            keyword=keyword,
            sources_list="\n".join(sources),
            content_samples="\n".join(content_samples)
        )
        
        try:
            start_time = time.time()
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            logger.info(f"Summary generated in {time.time() - start_time:.2f} seconds")
            
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def summarize_vertical(self, content, keyword, vertical_name, regulations, metrics):
        """
        Generate a vertical-specific summary using only Gemini's knowledge
        """
        cache_key = f"vertical_summary_{keyword}_{vertical_name}"
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Use the optimized vertical prompt that relies only on Gemini's knowledge
        prompt = self.PROMPTS["vertical"].format(
            vertical_name=vertical_name,
            keyword=keyword,
            regulations=", ".join(regulations),
            metrics=", ".join(metrics)
        )
        
        try:
            start_time = time.time()
            # Use Gemini model for vertical insights
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            logger.info(f"Vertical summary generated in {time.time() - start_time:.2f} seconds")
            
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error generating vertical summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def summarize_trends(self, content, keyword):
        """
        Generate a trend-focused summary
        """
        cache_key = f"trend_summary_{keyword}"
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Use the optimized trend prompt
        prompt = self.PROMPTS["trend"].format(
            keyword=keyword,
            content_sample=content[:3000]
        )
        
        try:
            start_time = time.time()
            response = gemini_model.generate_content(prompt)
            summary = response.text.strip() if response.text else ""
            logger.info(f"Trend summary generated in {time.time() - start_time:.2f} seconds")
            
            cache.set(cache_key, summary, expire=3600)
            return summary
        except Exception as e:
            logger.error(f"Error generating trend summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def answer_followup(self, summary, keyword, question):
        """
        Answer a follow-up question based on a summary
        """
        # Use the optimized follow-up prompt
        prompt = self.PROMPTS["followup"].format(
            keyword=keyword,
            summary=summary,
            question=question
        )
        
        try:
            start_time = time.time()
            response = gemini_model.generate_content(prompt)
            answer = response.text.strip() if response.text else ""
            logger.info(f"Follow-up answer generated in {time.time() - start_time:.2f} seconds")
            
            return answer
        except Exception as e:
            logger.error(f"Error generating follow-up answer: {e}")
            return f"Error generating answer: {str(e)}"

# Create singleton instance
fast_summarizer = FastSummarizer()