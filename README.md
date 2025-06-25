# Pain Cloud Realtime

A real-time pain point analysis tool that scrapes data from multiple sources to identify common issues and generate insights for different job roles.

## Features

- Real-time data scraping from Reddit, Stack Overflow, and ComplaintsBoard
- Emotional scoring of complaints
- AI-powered theme generation using Google's Gemini
- Interactive pain cloud visualization
- Trend analysis using Google Trends
- Caching for improved performance
- Support for multiple personas (Product Manager, Frontend Developer, Designer, Support Manager)

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- API keys for:
  - Reddit API
  - Stack Overflow API
  - Google API (for Gemini)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pain-cloud-realtime
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your API keys:
```
# Reddit API credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=PainRadar/1.0

# Stack Overflow API key
STACKOVERFLOW_API_KEY=your_stackoverflow_api_key

# Google API key for Gemini
GOOGLE_API_KEY=your_google_api_key

# Database URI
DATABASE_URI=postgresql://username:password@localhost:5432/painradar

# Flask secret key
SECRET_KEY=your-secret-key
```

5. Set up the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000/pain-cloud-realtime
```

## Usage

1. Select a persona from the dropdown menu (e.g., "Product Manager")
2. Choose a mode:
   - "Real Data": Shows actual complaints and issues from various sources
   - "AI Themes": Generates AI-powered insights and startup ideas
3. Click "Fetch Data" to generate the pain cloud and analysis

## Project Structure

```
pain-cloud-realtime/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── scrapers.py           # Scraping functionality
├── pain_cloud_realtime.py # Pain cloud endpoint
├── requirements.txt      # Python dependencies
├── templates/           # HTML templates
│   └── pain_cloud_realtime.html
├── static/             # Static files
│   ├── css/
│   └── js/
└── .env               # Environment variables
```

## API Endpoints

### GET /pain-cloud-realtime
Renders the main pain cloud interface.

### POST /pain-cloud-realtime/api
Accepts JSON data with:
```json
{
    "persona": "Product Manager",
    "mode": "real"  // or "AI themes"
}
```

Returns JSON response with:
- For "real" mode:
  - Top complaints
  - Keywords
  - Trends data
- For "AI themes" mode:
  - AI-generated themes
  - Startup ideas
  - Keywords

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.