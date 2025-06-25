# Migration from Gemini to Ollama

## Overview
This document describes the migration from Google's Gemini API to Ollama for the Flask application.

## Changes Made

### 1. Dependencies Updated
- **Removed**: `google-generativeai>=0.3.0`
- **Added**: `langchain-ollama>=0.0.1`

### 2. Files Modified

#### `app.py`
- Replaced Gemini setup with Ollama setup
- Updated all LLM calls from `gemini_model.generate_content()` to `llm.invoke()`
- Updated chat functionality to use Ollama's interface
- Updated error messages and comments to reference Ollama instead of Gemini

#### `vertical_insights.py`
- Replaced Gemini setup with Ollama setup
- Updated all LLM calls to use Ollama
- Added `get_vertical_context()` method for better integration

#### `requirements.txt`
- Updated dependencies to use `langchain-ollama` instead of `google-generativeai`

### 3. Key Changes in Code

#### Before (Gemini):
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

response = gemini_model.generate_content(prompt)
return response.text.strip()
```

#### After (Ollama):
```python
from langchain_ollama import OllamaLLM
llm = OllamaLLM(model="mistral:7b-instruct-q4_0")

response = llm.invoke(prompt)
return response.strip()
```

### 4. Functionality Preserved
All existing functionality has been preserved:
- Multi-source search and analysis
- Vertical insights generation
- Chat functionality
- Pain point extraction
- Startup idea generation
- Analytics and trend analysis

### 5. Setup Requirements

#### For Ollama:
1. Install Ollama: https://ollama.ai/
2. Pull the Mistral model: `ollama pull mistral:7b-instruct-q4_0`
3. Install Python dependencies: `pip install -r requirements.txt`

#### Environment Variables:
- Remove `GOOGLE_API_KEY` (no longer needed)
- Keep all other environment variables (Reddit, database, etc.)

### 6. Testing
Run the test script to verify Ollama integration:
```bash
python test_ollama.py
```

### 7. Benefits of Migration
- **Local Processing**: No API calls to external services
- **Privacy**: All data processed locally
- **Cost**: No API costs
- **Reliability**: No dependency on external API availability
- **Customization**: Can use different models or fine-tune locally

### 8. Notes
- The `mistral:7b-instruct-q4_0` model is used as the default (quantized version for better performance)
- Response format may vary slightly between Gemini and Ollama, but functionality remains the same
- All existing API endpoints and frontend functionality work without changes 