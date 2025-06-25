# PainRadar - Enhanced Version

This is the enhanced version of PainRadar with additional data sources, advanced analytics, team collaboration, integration capabilities, and vertical specialization.

## Quick Start

1. Run the setup script:
```
python setup.py
```

2. Edit the `.env` file with your API keys

3. Run the application:
```
python run_full.py
```

4. Access the application at http://localhost:5000

## New Features

### 1. Additional Data Sources
- **Twitter/X Integration**: Analyze tweets and social media conversations
- **App Store Reviews**: Extract insights from iOS and Android app reviews
- **Industry Forums**: Gather data from vertical-specific community forums

### 2. Advanced Analytics
- **Trend Tracking**: Monitor how topics and pain points evolve over time
- **Sentiment Analysis**: Track emotional responses to products and features
- **Competitive Analysis**: Identify strengths and weaknesses of market players
- **Visualization**: Charts and graphs to better understand market dynamics

### 3. Team Collaboration
- **Team Management**: Create teams and invite members
- **Shared Insights**: Share research findings with team members
- **Comments**: Discuss and collaborate on market insights

### 4. Integration Capabilities
- **Jira**: Create issues directly from market insights
- **Trello**: Add cards to your product planning boards
- **Slack**: Share findings with your team via Slack
- **Notion**: Save insights to your knowledge base

### 5. Vertical Specialization
- **Industry-Specific Insights**: Tailored analysis for different verticals
- **Fintech**: Banking, payments, lending, investment solutions
- **Healthcare**: Medical and health management solutions
- **E-Commerce**: Online retail and marketplace insights
- **SaaS**: Software-as-a-Service and enterprise solutions
- **EdTech**: Educational technology and learning platforms

## File Structure

- `app.py`: Original application
- `run_full.py`: Enhanced application entry point
- `models.py`: Database models for all features
- `app_routes.py`: Routes for all new features
- `app_integration.py`: Integration with original app
- `data_sources.py`: Data source manager
- `twitter_source.py`: Twitter data source
- `app_store_source.py`: App store reviews data source
- `industry_forum_source.py`: Industry forum data source
- `analytics.py`: Trend analytics and visualization
- `vertical_insights.py`: Industry-specific insights
- `integrations.py`: External tool integrations
- `templates/`: HTML templates for all features

## API Endpoints

### Data Sources
- `POST /multi_search`: Search across all data sources
- `GET /api/twitter/<keyword>`: Get Twitter data
- `GET /api/appstore/<app_id>`: Get app store reviews
- `GET /api/forums/<keyword>`: Get forum posts

### Analytics
- `GET /api/trends/<keyword>`: Get trend data
- `GET /api/competitors/<keyword>`: Get competitive analysis

### Vertical Insights
- `GET /api/verticals`: Get list of supported verticals
- `POST /api/verticals/<vertical>/<keyword>`: Get vertical-specific insights

### Team Collaboration
- `GET/POST /api/teams`: Get or create teams
- `GET/POST /api/teams/<team_id>/members`: Get or add team members

### Integrations
- `POST /api/integrations/jira`: Create a Jira issue
- `POST /api/integrations/trello`: Create a Trello card
- `POST /api/integrations/slack`: Send to Slack

## Troubleshooting

If you encounter any issues:

1. Make sure all dependencies are installed:
```
pip install -r requirements.txt
```

2. Check that your API keys are correctly set in the `.env` file

3. Make sure the instance directory exists and is writable

4. If using Selenium-based features (app store reviews, forums), ensure Chrome is installed

5. Check the console for specific error messages