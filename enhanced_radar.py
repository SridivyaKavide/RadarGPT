import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import jsonify
from diskcache import Cache

# Import enhanced modules
from enhanced_data_sources import enhanced_data_sources
from enhanced_summarizer import enhanced_summarizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class EnhancedRadar:
    """Enhanced RadarGPT functionality with optimized data sources and summarization"""
    
    def __init__(self):
        self.data_sources = enhanced_data_sources
        self.summarizer = enhanced_summarizer
        self.current_status = {}
    
    def search(self, keyword, user_id=None, db=None):
        """
        Perform an enhanced multi-source search with optimized results
        
        Args:
            keyword: Search term
            user_id: User ID for database storage (optional)
            db: Database session for storage (optional)
            
        Returns:
            JSON response with summaries and source data
        """
        cache_key = f"enhanced_radar_{keyword}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        self.current_status[keyword] = "Starting enhanced search..."
        
        # Initialize results containers
        results = {
            "stackoverflow": [],
            "reddit": [],
            "complaintsboard": [],
            "producthunt": []
        }
        errors = {}
        
        # Execute searches in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all search tasks
            futures = {
                "stackoverflow": executor.submit(self.data_sources.get_enhanced_stackoverflow, keyword),
                "reddit": executor.submit(self.data_sources.get_enhanced_reddit, keyword),
                "complaintsboard": executor.submit(self.data_sources.get_enhanced_complaintsboard, keyword),
                "producthunt": executor.submit(self.data_sources.get_enhanced_producthunt, keyword)
            }
            
            # Process results as they complete
            for source, future in as_completed(futures):
                try:
                    self.current_status[keyword] = f"Searching {source.capitalize()}..."
                    source_results = future.result(timeout=60)  # Increased timeout for thorough search
                    results[source] = source_results
                    self.current_status[keyword] = f"Found {len(source_results)} results from {source.capitalize()}"
                    logger.info(f"Successfully retrieved {len(source_results)} results from {source}")
                except Exception as e:
                    errors[source] = str(e)
                    logger.error(f"Error retrieving {source} data: {e}")
                    self.current_status[keyword] = f"Error searching {source}: {str(e)}"
        
        # Generate summaries in parallel
        self.current_status[keyword] = "Analyzing data and generating summaries..."
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            summary_futures = {
                "stackoverflow": executor.submit(self.summarizer.summarize_stackoverflow, results["stackoverflow"]),
                "reddit": executor.submit(self.summarizer.summarize_reddit, results["reddit"]),
                "complaintsboard": executor.submit(self.summarizer.summarize_complaintsboard, results["complaintsboard"]),
                "producthunt": executor.submit(self.summarizer.summarize_producthunt, results["producthunt"])
            }
            
            summaries = {}
            for source, future in as_completed(summary_futures):
                try:
                    summaries[source] = future.result()
                    logger.info(f"Successfully generated summary for {source}")
                except Exception as e:
                    summaries[source] = f"Error generating {source} summary: {str(e)}"
                    logger.error(f"Error generating {source} summary: {e}")
        
        # Generate combined summary
        try:
            self.current_status[keyword] = "Creating comprehensive analysis..."
            combined_summary = self.summarizer.generate_combined_summary(
                summaries["stackoverflow"],
                summaries["reddit"],
                summaries["complaintsboard"],
                summaries["producthunt"],
                keyword
            )
        except Exception as e:
            combined_summary = f"Error generating combined summary: {str(e)}"
            logger.error(f"Error generating combined summary: {e}")
        
        # Save to database if provided
        query_id = None
        if db and user_id:
            try:
                from app import SearchQuery
                new_query = SearchQuery(
                    keyword=keyword,
                    source="enhanced_multi",
                    mode="comprehensive",
                    result=combined_summary,
                    user_id=user_id
                )
                db.session.add(new_query)
                db.session.commit()
                query_id = new_query.id
                logger.info(f"Saved search results to database with ID {query_id}")
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
        
        # Prepare response
        response = {
            "summary": combined_summary,
            "source_summaries": summaries,
            "sources": results,
            "query_id": query_id,
            "errors": errors if errors else None
        }
        
        self.current_status[keyword] = "Analysis complete!"
        cache.set(cache_key, response, expire=3600)
        return response
    
    def get_status(self, keyword):
        """Get the current status of a search operation"""
        return self.current_status.get(keyword, "No status available")

# Create singleton instance
enhanced_radar = EnhancedRadar()