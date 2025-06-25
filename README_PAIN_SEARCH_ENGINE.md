# Pain Search Engine

A comprehensive search engine for discovering pain points, problems, and startup opportunities across multiple data sources.

## Overview

The Pain Search Engine is a consumer-facing search experience that aggregates data from multiple sources to identify pain points and startup opportunities. It integrates with News API, Reddit, Stack Overflow, and ComplaintsBoard to provide comprehensive insights.

## Features

### 🔍 Multi-Source Search
- **Reddit**: Searches across all subreddits for user complaints and discussions
- **News API**: Finds news articles related to problems and pain points
- **Stack Overflow**: Identifies technical issues and challenges
- **ComplaintsBoard**: Discovers customer complaints and service issues

### 🤖 AI-Powered Analysis
- **Pain Point Extraction**: Identifies specific problems and frustrations
- **Startup Opportunity Generation**: Suggests potential business ideas
- **Severity Scoring**: Rates pain points from 1-10 based on urgency and impact
- **User Segmentation**: Identifies who is affected by each problem

### 📊 Rich Analytics
- **Source Statistics**: Shows results from each data source
- **Category Filtering**: Filter by health, productivity, dev tools, finance
- **Real-time Search**: Instant results with loading indicators
- **Export Capabilities**: Save and share findings

## API Endpoints

### GET `/pain-search-engine`
Renders the main search interface.

**Authentication**: Required (login)

### POST `/api/pain-search`
Performs the multi-source search and AI analysis.

**Request Body**:
```json
{
    "query": "string",
    "category": "all|health|productivity|dev_tools|finance"
}
```

**Response**:
```json
{
    "query": "string",
    "category": "string",
    "results": {
        "reddit": [...],
        "news": [...],
        "stackoverflow": [...],
        "complaintsboard": [...]
    },
    "analysis": {
        "pain_points": [
            {
                "title": "string",
                "description": "string",
                "severity": 8,
                "user_segments": ["string"],
                "frequency": "string",
                "business_impact": "string",
                "emotional_intensity": "string",
                "quotes": ["string"]
            }
        ],
        "startup_opportunities": [
            {
                "idea": "string",
                "value_proposition": "string",
                "validation_score": 8,
                "target_users": ["string"],
                "urgency": "string"
            }
        ]
    },
    "total_sources": 4,
    "total_items": 25
}
```

## Data Sources

### Reddit Integration
- Searches across all subreddits using PRAW
- Extracts post titles, content, and comments
- Caches results for 1 hour
- Configurable post limits and subreddit targeting

### News API Integration
- Uses your News API key for article search
- Searches for pain-related keywords
- Filters by language and date range
- Caches results for 30 minutes

### Stack Overflow Integration
- Uses Stack Exchange API
- Searches for technical problems
- Configurable page limits and sorting

### ComplaintsBoard Integration
- Web scraping with Selenium
- Extracts customer complaints
- Handles pagination and rate limiting

## AI Analysis

The system uses Groq AI (with OpenRouter fallback) to:

1. **Extract Pain Points**: Identify specific problems from source data
2. **Generate Opportunities**: Suggest startup ideas based on pain points
3. **Score Severity**: Rate problems from 1-10
4. **Segment Users**: Identify affected user groups
5. **Analyze Trends**: Determine frequency and urgency

## Setup

### Prerequisites
- Python 3.8+
- Flask application running
- Required API keys (see below)

### Environment Variables
```bash
# News API
NEWS_API_KEY=your_news_api_key

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_user_agent

# Groq AI
GROQ_API_KEY=your_groq_api_key
GROQ_API_KEY_1=your_groq_api_key_1
# ... (up to GROQ_API_KEY_29 for rotation)

# OpenRouter (fallback)
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Installation
1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your environment variables in `.env` file

3. Start the Flask application:
   ```bash
   python app.py
   ```

4. Access the Pain Search Engine at:
   ```
   http://localhost:5000/pain-search-engine
   ```

## Usage

### Basic Search
1. Navigate to the Pain Search Engine page
2. Enter your search query (e.g., "project management", "customer service")
3. Select a category (optional)
4. Click "Search"
5. Review pain points and startup opportunities

### Advanced Features
- **Category Filtering**: Filter results by industry/domain
- **Source Tabs**: View raw data from each source
- **Severity Analysis**: Focus on high-severity pain points
- **Opportunity Validation**: Review startup idea scores

## Technical Details

### Caching
- Reddit results: 1 hour
- News API results: 30 minutes
- Stack Overflow results: 1 hour
- ComplaintsBoard results: 1 hour

### Rate Limiting
- Concurrent requests limited to 4 workers
- 30-second timeout per source
- Automatic fallback for failed sources

### Error Handling
- Graceful degradation when sources fail
- Fallback AI responses when Groq/OpenRouter unavailable
- User-friendly error messages

## Customization

### Adding New Sources
1. Create a new search function
2. Add it to the ThreadPoolExecutor in `/api/pain-search`
3. Update the results processing logic
4. Add source tab in the frontend

### Modifying AI Analysis
1. Update the `analysis_prompt` in the API endpoint
2. Adjust JSON structure for pain points and opportunities
3. Modify severity scoring logic

### Styling
The interface uses Bootstrap 5 and custom CSS. Modify `templates/pain_search_engine.html` for styling changes.

## Troubleshooting

### Common Issues

**"No results found"**
- Check API keys are configured
- Verify network connectivity
- Review source-specific error logs

**"AI analysis failed"**
- Check Groq API key and quota
- Verify OpenRouter fallback is configured
- Review prompt length limits

**"Slow performance"**
- Reduce concurrent workers
- Increase cache duration
- Optimize search queries

### Debug Mode
Enable Flask debug mode for detailed error messages:
```python
app.run(debug=True)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is part of the Radar AI application. See the main LICENSE file for details. 