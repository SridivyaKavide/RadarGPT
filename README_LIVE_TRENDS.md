# 🌍 Live Trends Dashboard

A real-time trending topics dashboard that aggregates data from multiple sources to provide live insights into what's trending globally and regionally.

## 🚀 Features

### 📊 Real-Time Data Sources
- **News API**: Latest headlines and trending topics
- **Reddit**: Hot posts from popular subreddits
- **Stack Overflow**: Trending programming tags and topics
- **ComplaintsBoard**: Recent complaints and issues from popular companies

### 🎯 Smart Filtering
- **Region-based**: Global, US, UK, Europe, Asia
- **Category-based**: Technology, Business, Health, Entertainment, Science
- **Time windows**: 24 hours, 7 days, 30 days

### 🤖 AI-Powered Insights
- Automatic trend analysis and pattern recognition
- Market opportunity identification
- Regional trend comparisons
- Predictive insights for emerging topics

### 🔄 Live Updates
- Auto-refresh every 30 seconds
- Real-time countdown timer
- Manual refresh button
- Dynamic keyword extraction

## 🛠️ Technical Implementation

### Backend Routes

#### `/live-trends`
- **Method**: GET
- **Description**: Renders the Live Trends dashboard page
- **Authentication**: Required

#### `/api/live-trends`
- **Method**: POST
- **Description**: Main API endpoint for fetching live trends data
- **Parameters**:
  - `region`: Global, us, uk, eu, asia
  - `category`: all, technology, business, health, entertainment, science
  - `time_window`: 24h, 7d, 30d
- **Response**: JSON with trends data from all sources

#### `/api/trending-keywords`
- **Method**: GET
- **Description**: Get real-time trending keywords across all sources
- **Response**: JSON with keyword frequency and trend data

### Data Processing

#### News API Integration
```python
def get_news_trends():
    # Get top headlines for trending topics
    # Extract key phrases from titles
    # Filter by region and category
    # Return structured trend data
```

#### Reddit Integration
```python
def get_reddit_trends():
    # Map categories to relevant subreddits
    # Get hot posts with high scores
    # Extract trending topics
    # Return with engagement metrics
```

#### Stack Overflow Integration
```python
def get_stackoverflow_trends():
    # Get trending tags via API
    # Sort by popularity
    # Return with usage counts
```

#### ComplaintsBoard Integration
```python
def get_complaints_trends():
    # Monitor popular companies
    # Get recent complaints
    # Cache results for performance
```

### Frontend Features

#### Real-Time Dashboard
- **Responsive Design**: Works on desktop and mobile
- **Live Updates**: Auto-refresh with countdown
- **Interactive Elements**: Clickable trends and keywords
- **Visual Indicators**: Trend direction and severity

#### Data Visualization
- **Stats Cards**: Total trends, active sources, hot keywords
- **Source Grids**: Separate cards for each data source
- **Keyword Cloud**: Interactive trending keywords
- **AI Insights**: Generated analysis and predictions

## 📱 User Interface

### Main Dashboard
```
┌─────────────────────────────────────────────────────────┐
│                    Live Trends Dashboard                │
├─────────────────────────────────────────────────────────┤
│ Region: [Global ▼] Category: [Technology ▼] [Load]     │
├─────────────────────────────────────────────────────────┤
│ [Total: 150] [Sources: 4] [Keywords: 25] [Updated: Now] │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ News Trends │ │Reddit Trends│ │Stack Overflow│        │
│ │             │ │             │ │             │        │
│ └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────┤
│                    Hot Keywords                         │
│ [AI] [Machine Learning] [Startup] [Tech] [Innovation]  │
├─────────────────────────────────────────────────────────┤
│                    AI Insights                          │
│ Analysis of emerging patterns and opportunities...     │
└─────────────────────────────────────────────────────────┘
```

### Navigation
- **Sidebar Link**: "Trends" with trending-up icon
- **URL**: `/live-trends`
- **Authentication**: Required (login needed)

## 🔧 Configuration

### Environment Variables
```bash
# News API (required for news trends)
NEWS_API_KEY=your_news_api_key_here

# Reddit API (required for Reddit trends)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_user_agent
```

### API Limits
- **News API**: 1000 requests/day (free plan)
- **Reddit API**: Rate limited per subreddit
- **Stack Overflow API**: 10,000 requests/day
- **ComplaintsBoard**: Web scraping with delays

## 🚀 Usage

### 1. Access the Dashboard
1. Navigate to the main page
2. Click "Trends" in the sidebar navigation
3. Or go directly to `/live-trends`

### 2. Configure Filters
1. Select your desired region (Global, US, UK, etc.)
2. Choose a category (Technology, Business, etc.)
3. Set time window (24h, 7d, 30d)
4. Click "Load Trends"

### 3. Explore Data
- **Click on trends** to open source links
- **Click on keywords** to search for related pain points
- **Watch for auto-refresh** every 30 seconds
- **Use manual refresh** button for immediate updates

### 4. Analyze Insights
- Review AI-generated insights about patterns
- Identify market opportunities
- Track regional differences
- Monitor emerging topics

## 📊 Data Sources Details

### News API Trends
- **Source**: Top headlines from major news outlets
- **Filtering**: By country, category, and relevance
- **Processing**: Key phrase extraction from titles
- **Update Frequency**: Every 30 seconds

### Reddit Trends
- **Source**: Hot posts from relevant subreddits
- **Categories**: Technology, Business, Health, etc.
- **Metrics**: Score, comments, engagement
- **Filtering**: High-scoring posts only (>100 score)

### Stack Overflow Trends
- **Source**: Trending programming tags
- **API**: Stack Exchange API v2.3
- **Metrics**: Tag usage count and popularity
- **Categories**: Technology-focused

### ComplaintsBoard Trends
- **Source**: Recent complaints from popular companies
- **Companies**: Amazon, Netflix, Spotify, Uber, etc.
- **Processing**: Cached results for performance
- **Categories**: Customer service issues

## 🎯 Use Cases

### For Founders
- **Market Research**: Identify trending problems and opportunities
- **Competitive Analysis**: Monitor what users are complaining about
- **Product Validation**: See if your idea addresses current pain points
- **Timing**: Understand when to launch based on trending topics

### For Product Managers
- **Feature Prioritization**: Focus on trending user needs
- **User Research**: Understand current frustrations
- **Market Timing**: Launch features when demand is high
- **Competitive Intelligence**: Monitor competitor issues

### For Investors
- **Due Diligence**: Validate market demand for startups
- **Trend Analysis**: Identify emerging market opportunities
- **Risk Assessment**: Understand market sentiment
- **Portfolio Monitoring**: Track relevant industry trends

## 🔮 Future Enhancements

### Planned Features
- **Social Media Integration**: Twitter, LinkedIn trends
- **Geographic Heatmaps**: Visual trend distribution
- **Sentiment Analysis**: Positive/negative trend classification
- **Custom Alerts**: Notifications for specific keywords
- **Export Functionality**: Download trend reports
- **Historical Data**: Trend evolution over time

### API Improvements
- **WebSocket Support**: Real-time streaming updates
- **Rate Limit Optimization**: Better API key rotation
- **Caching Strategy**: Improved performance
- **Error Handling**: More robust fallbacks

## 🧪 Testing

Run the test script to verify functionality:
```bash
python test_live_trends.py
```

This will test:
- Live Trends API endpoint
- Trending Keywords API
- Page accessibility
- Data retrieval from all sources

## 📈 Performance

### Optimization Features
- **Parallel Processing**: Multiple sources fetched simultaneously
- **Caching**: Results cached for 1 hour
- **Rate Limiting**: Respects API limits
- **Error Handling**: Graceful fallbacks
- **Timeout Management**: Prevents hanging requests

### Monitoring
- **Source Status**: Track which sources are active
- **Response Times**: Monitor API performance
- **Error Rates**: Track failed requests
- **Data Quality**: Validate returned data

## 🤝 Contributing

To add new data sources or improve the dashboard:

1. **Add Source Function**: Create a new function in `app.py`
2. **Update API**: Modify `/api/live-trends` to include new source
3. **Frontend Integration**: Add new card to dashboard
4. **Testing**: Update test script
5. **Documentation**: Update this README

## 📞 Support

For issues or questions:
- Check the test script output
- Verify API keys are configured
- Ensure all dependencies are installed
- Review error logs in the console

---

**Live Trends Dashboard** - Your real-time window into what the world is talking about! 🌍📊 