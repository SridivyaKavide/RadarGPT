import time
import logging
from concurrent.futures import ThreadPoolExecutor
from diskcache import Cache

# Import fast modules
from fast_data_sources import fast_data_sources
from fast_summarizer import fast_summarizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cache
cache = Cache("radargpt_cache")

class FastRadar:
    """Fast RadarGPT functionality with optimized response time"""
    
    def __init__(self):
        self.data_sources = fast_data_sources
        self.summarizer = fast_summarizer
        self.current_status = {}
    
    def search(self, keyword, user_id=None, db=None):
        """
        Perform a fast multi-source search with optimized results
        """
        cache_key = f"fast_radar_{keyword}"
        result = cache.get(cache_key)
        if result is not None:
            return result
            
        self.current_status[keyword] = "Starting fast search..."
        start_time = time.time()
        
        # Initialize results containers
        results = {
            "stackoverflow": [],
            "reddit": [],
            "complaintsboard": [],
            "producthunt": []
        }
        
        # Execute searches in parallel with timeouts
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all search tasks
            futures = {
                "stackoverflow": executor.submit(self.data_sources.get_stackoverflow_fast, keyword),
                "reddit": executor.submit(self.data_sources.get_reddit_fast, keyword),
                "complaintsboard": executor.submit(self.data_sources.get_complaintsboard_fast, keyword),
                "producthunt": executor.submit(self.data_sources.get_producthunt_fast, keyword)
            }
            
            # Process results as they complete with strict timeouts
            for source, future in futures.items():
                try:
                    self.current_status[keyword] = f"Searching {source}..."
                    source_results = future.result(timeout=5)  # Strict 5-second timeout
                    results[source] = source_results
                    self.current_status[keyword] = f"Found {len(source_results)} results from {source}"
                except Exception as e:
                    logger.error(f"Error or timeout retrieving {source} data: {e}")
                    # Use empty results if timeout
                    results[source] = []
        
        # Generate single combined summary with strict timeout
        self.current_status[keyword] = "Generating fast summary..."
        try:
            summary = self.summarizer.summarize_all_sources(
                results["stackoverflow"],
                results["reddit"],
                results["complaintsboard"],
                results["producthunt"],
                keyword
            )
        except Exception as e:
            summary = f"Error generating summary: {str(e)}"
            logger.error(f"Error generating summary: {e}")
        
        # Save to database if provided
        query_id = None
        if db and user_id:
            try:
                from app import SearchQuery
                new_query = SearchQuery(
                    keyword=keyword,
                    source="fast_multi",
                    mode="fast",
                    result=summary,
                    user_id=user_id
                )
                db.session.add(new_query)
                db.session.commit()
                query_id = new_query.id
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
        
        # Prepare response
        response = {
            "summary": summary,
            "sources": results,
            "query_id": query_id,
            "execution_time": f"{time.time() - start_time:.2f} seconds"
        }
        
        self.current_status[keyword] = f"Analysis complete in {time.time() - start_time:.2f} seconds!"
        cache.set(cache_key, response, expire=3600)
        return response
    
    def get_status(self, keyword):
        """Get the current status of a search operation"""
        return self.current_status.get(keyword, "No status available")

# Create singleton instance
fast_radar = FastRadar()