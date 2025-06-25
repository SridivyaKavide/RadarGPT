# Pain Dashboard - RadarGPT

A visual dashboard for analyzing pain points and opportunities in different industry verticals.

## Features

- **Pain Point Visualization**: Charts showing severity of different pain points
- **Opportunity Mapping**: Visual representation of product opportunities
- **Pain Points Analysis**: Detailed table of pain points with severity ratings
- **1-Click MVP Generator**: Quickly generate landing page and go-to-market plans

## How to Run

1. Make sure you have the required packages installed:
   ```
   pip install flask flask-cors python-dotenv google-generativeai
   ```

2. Set up your Google API key in the `.env` file:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

3. Run the application:
   ```
   python run_dashboard.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

1. Select an industry vertical (FinTech, Healthcare, E-Commerce, SaaS, EdTech)
2. Enter your query (e.g., "I'm interested in giving new innovative solutions but I don't know where to start")
3. Click "Analyze" to generate insights
4. View the visualized pain points, opportunities, and MVP ideas

## Next Steps for Billion-Dollar Startup

1. **Data Moat**: Add scrapers for Reddit, Twitter, StackOverflow, etc.
2. **Collections/Boards**: Implement saving and organizing insights
3. **Export Functionality**: Add export to Notion, Slack, etc.
4. **User Authentication**: Add user accounts and team collaboration
5. **Database**: Create proper database for storing insights and user data