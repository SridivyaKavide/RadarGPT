# Persona to source mapping
PERSONA_SOURCES = {
    'Product Manager': {
        'reddit': ['ProductManagement', 'startups', 'productmanagement'],
        'stackoverflow': ['product-management', 'product-owner', 'agile', 'scrum', 'jira'],
        'complaintsboard': ['product management software', 'project management software', 'agile tools'],
        'keywords': ['meeting', 'roadmap', 'stakeholder', 'agile', 'sprint', 'backlog']
    },
    'Frontend Developer': {
        'reddit': ['webdev', 'frontend', 'javascript', 'reactjs'],
        'stackoverflow': ['javascript', 'reactjs', 'css', 'html', 'frontend', 'web-development'],
        'complaintsboard': ['web development tools', 'frontend frameworks', 'javascript libraries'],
        'keywords': ['browser', 'responsive', 'framework', 'css', 'javascript']
    },
    'Designer': {
        'reddit': ['UXDesign', 'web_design', 'design', 'userexperience'],
        'stackoverflow': ['design', 'ui', 'ux', 'css', 'user-interface', 'user-experience'],
        'complaintsboard': ['design software', 'ui tools', 'ux tools', 'prototyping tools'],
        'keywords': ['design', 'ui', 'ux', 'prototype', 'wireframe']
    },
    'Support Manager': {
        'reddit': ['sysadmin', 'techsupport', 'ITSupport'],
        'stackoverflow': ['support', 'customer-service', 'helpdesk', 'troubleshooting', 'technical-support'],
        'complaintsboard': ['customer service software', 'help desk software', 'support tools'],
        'keywords': ['ticket', 'support', 'customer', 'helpdesk']
    }
}

# Emotional keywords for scoring
EMOTIONAL_KEYWORDS = {
    'negative': [
        'hate', 'broken', 'frustrating', 'confusing', 'annoying', 'terrible',
        'awful', 'horrible', 'useless', 'waste', 'problem', 'issue', 'bug',
        'error', 'fail', 'failed', 'failing', 'difficult', 'hard', 'complex'
    ],
    'positive': [
        'love', 'great', 'awesome', 'excellent', 'amazing', 'perfect',
        'best', 'easy', 'simple', 'helpful', 'useful', 'good', 'nice'
    ]
}

# Cache settings
CACHE_SETTINGS = {
    'reddit': 3600,  # 1 hour
    'stackoverflow': 3600,
    'complaintsboard': 3600,
    'trends': 3600,
    'summaries': 86400  # 24 hours
}

# API rate limits
RATE_LIMITS = {
    'reddit': 1,  # seconds between requests
    'stackoverflow': 1,
    'complaintsboard': 1,
    'trends': 1
}

# Scraping settings
SCRAPING_SETTINGS = {
    'max_results': 100,
    'timeframe': '6 months',
    'min_score': 5,  # minimum score for Reddit posts
    'min_comments': 3  # minimum comments for Reddit posts
}

# Gemini prompt templates
PROMPT_TEMPLATES = {
    'summarize_pains': '''
You are analyzing user complaints from {persona}. Given the following complaints:
{complaints}

Please:
1. Identify the top 3 pain themes
2. Extract recurring keywords and emotions
3. Suggest startup ideas to solve each pain

Format the response as JSON with:
{
    "pain_themes": [
        {
            "theme": "string",
            "description": "string",
            "startup_ideas": ["string"]
        }
    ],
    "keywords": [
        {
            "word": "string",
            "frequency": number,
            "emotion": "positive/negative"
        }
    ]
}
''',
    'generate_themes': '''
Based on the following data about {persona}:
{data}

Generate 5 innovative startup ideas that could solve their pain points.
Format as JSON array of strings.
'''
}


DOMAIN = "https://yourdomain.com" 
RAZORPAY_KEY_ID = "rzp_live_inBesRIYGuo2OX"
RAZORPAY_KEY_SECRET = "UrImjOs9XeXHEgPTfOvlxdbs"