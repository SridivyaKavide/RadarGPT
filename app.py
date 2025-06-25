import os
import re
import time
import json
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import logging
from collections import Counter
import re
import os
import threading
import time

# Global variable to store the latest status message
current_status = {}

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

# Import vertical insights
from vertical_insights import VerticalInsights
# Import analytics
from analytics import TrendAnalytics
from news_aggregator import get_news_trends_hybrid

# Import sqlalchemy functions
from sqlalchemy import func, desc, case

# --- Source list for multi_search ---
ALL_SOURCES = [
    "Reddit",
    "Stack Overflow",
    "ComplaintsBoard",
    "Product Hunt",
    "Quora"
]

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# --- News API setup ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_BASE_URL = "https://newsapi.org/v2"

# --- Groq setup ---
from groq import Groq
import random
import time

# List of Groq API keys for rotation
GROQ_API_KEYS = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 61)]
GROQ_API_KEYS = [k for k in GROQ_API_KEYS if k]  # filter out None

GROQ_KEYS_ORG_1 = GROQ_API_KEYS[:30]
GROQ_KEYS_ORG_2 = GROQ_API_KEYS[30:]
ALL_GROQ_KEY_GROUPS = [GROQ_KEYS_ORG_1, GROQ_KEYS_ORG_2]

groq_key_state = []
for group in ALL_GROQ_KEY_GROUPS:
    groq_key_state.append({
        "keys": group,
        "index": 0,
        "last_used": {},
        "failed_keys": {},
        "lock": threading.Lock()
    })

# 👇 Confirm which keys loaded and how many
GROQ_API_KEYS = [
    os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 61)
]

# 🔍 Filter out missing keys (None values)
GROQ_API_KEYS = [k for k in GROQ_API_KEYS if k]

print(f"🔑 Total valid keys loaded: {len(GROQ_API_KEYS)}")

# 🟦 Split
GROQ_KEYS_ORG_1 = GROQ_API_KEYS[:30]
GROQ_KEYS_ORG_2 = GROQ_API_KEYS[30:]

print(f"📦 Org 1 keys: {len(GROQ_KEYS_ORG_1)}")
print(f"📦 Org 2 keys: {len(GROQ_KEYS_ORG_2)}")

# 🔁 Assign to all groups
ALL_GROQ_KEY_GROUPS = [GROQ_KEYS_ORG_1, GROQ_KEYS_ORG_2]

# 🧠 Create group state
ALL_GROQ_KEY_GROUPS = [GROQ_KEYS_ORG_1, GROQ_KEYS_ORG_2]
groq_key_state = []
for group in ALL_GROQ_KEY_GROUPS:
    groq_key_state.append({
        "keys": group,
        "index": 0,
        "last_used": {},
        "failed_keys": {},
        "lock": threading.Lock()
    })



# List of OpenRouter API keys for rotation
OPENROUTER_API_KEYS = [
    os.getenv("OPENROUTER_API_KEY_1"),
    os.getenv("OPENROUTER_API_KEY_2"),
    os.getenv("OPENROUTER_API_KEY_3"),
    os.getenv("OPENROUTER_API_KEY_4"),
    os.getenv("OPENROUTER_API_KEY_5"),
    os.getenv("OPENROUTER_API_KEY_6"),
    os.getenv("OPENROUTER_API_KEY_7"),
    os.getenv("OPENROUTER_API_KEY_8"),
    os.getenv("OPENROUTER_API_KEY_9"),
    os.getenv("OPENROUTER_API_KEY_10")
]


def groq_generate_content_with_fallback(
    prompt,
    temperature=1,
    max_tokens=6000,
    model="llama-3.1-8b-instant",
    openrouter_model="mistralai/devstral-small-2505:free"
):
    """
    Always use groq_generate_content, never fallback, always wait for a Groq key.
    """
    return groq_generate_content(prompt, temperature, max_tokens, model)


# Filter out None values
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]
OPENROUTER_API_KEYS = [key for key in OPENROUTER_API_KEYS if key]

# Fallback to single key if no rotation keys provided
if not GROQ_API_KEYS:
    GROQ_API_KEYS = [os.getenv("GROQ_API_KEY")]

if not OPENROUTER_API_KEYS:
    OPENROUTER_API_KEYS = [os.getenv("OPENROUTER_API_KEY")]

# Track failed keys to avoid using them immediately after rate limit
failed_groq_keys = {}
failed_openrouter_keys = {}
MAX_RETRIES = 5  # Increased from 3 to 5 since we have 30 working keys

# Enhanced rate limit handling
RATE_LIMIT_TIMEOUT = 300  # 5 minutes for rate-limited keys (increased from 60s)
INVALID_KEY_TIMEOUT = 3600  # 1 hour for invalid keys
MAX_CONCURRENT_REQUESTS = 1000  # Effectively unlimited

# Request queuing and throttling
import threading
import queue
from datetime import datetime, timedelta

# Global request queue and throttling
request_queue = queue.Queue()
request_lock = threading.Lock()
last_request_time = {}
REQUEST_DELAY = 0.5  # 500ms between requests per key
MAX_QUEUE_SIZE = 100  # Maximum requests in queue

class RequestLimiter:
    """No-op limiter for unlimited concurrency (for true parallel Groq API calls)"""
    def __init__(self, max_concurrent=1000):
        self.max_concurrent = max_concurrent
    def acquire(self):
        pass  # No global lock
    def release(self):
        pass  # No global lock

# Global request limiter (now a no-op)
request_limiter = RequestLimiter(MAX_CONCURRENT_REQUESTS)

# Add thread-safe round-robin index for Groq and OpenRouter keys
_groq_key_index = 0
_groq_key_index_lock = threading.Lock()
_openrouter_key_index = 0
_openrouter_key_index_lock = threading.Lock()

def get_groq_client():
    """
    Return a usable Groq client from any available key across all orgs,
    respecting cooldowns and skipping rate-limited (TPD-exhausted) keys.
    """
    REQUEST_DELAY = 0.7
    timeout_seconds = 10
    start_time = time.time()

    while True:
        for org_idx, group_state in enumerate(groq_key_state):
            org_name = f"Org {org_idx + 1}"
            keys = group_state["keys"]
            attempts = 0

            while attempts < len(keys):
                with group_state["lock"]:
                    key = keys[group_state["index"] % len(keys)]
                    group_state["index"] += 1
                    attempts += 1

                    # Skip if key is marked as failed
                    if key in group_state["failed_keys"]:
                        if time.time() < group_state["failed_keys"][key]:
                            continue
                        else:
                            del group_state["failed_keys"][key]  # Retry after timeout

                    # Per-key throttle logic
                    now = time.time()
                    last_used = group_state["last_used"].get(key, 0)
                    if now - last_used < REQUEST_DELAY:
                        continue

                    # ✅ Key is usable
                    group_state["last_used"][key] = now
                    print(f"✅ Using key: {key[:6]}... from {org_name}")
                    return Groq(api_key=key)

            print(f"⏳ All keys in {org_name} are rate-limited or cooling down. Trying next org...")

        if time.time() - start_time > timeout_seconds:
            print("❌ No usable Groq keys across all orgs. Failing request.")
            raise RuntimeError("No usable Groq keys available at this time.")

        print("🔁 Retrying all orgs after short wait...")
        time.sleep(0.5)



def get_openrouter_client():
    """Get an OpenRouter client with a round-robin selected API key, avoiding recently failed keys"""
    current_time = time.time()
    available_keys = []
    for key in OPENROUTER_API_KEYS:
        if key not in failed_openrouter_keys:
            available_keys.append(key)
        else:
            failure_time = failed_openrouter_keys[key]
            if isinstance(failure_time, tuple):
                timestamp, error_type = failure_time
                if error_type == 'rate_limit':
                    timeout = RATE_LIMIT_TIMEOUT
                elif error_type == 'invalid_key':
                    timeout = INVALID_KEY_TIMEOUT
                else:
                    timeout = 60
            else:
                timeout = 60
            if current_time - timestamp > timeout:
                available_keys.append(key)
    if not available_keys:
        failed_openrouter_keys.clear()
        available_keys = OPENROUTER_API_KEYS
    if not available_keys:
        return None
    global _openrouter_key_index
    with _openrouter_key_index_lock:
        api_key = available_keys[_openrouter_key_index % len(available_keys)]
        _openrouter_key_index += 1
    return api_key

def mark_groq_key_failed(api_key, error_type='unknown'):
    """Mark a Groq API key as failed with error type for better timeout handling"""
    failed_groq_keys[api_key] = (time.time(), error_type)

def mark_openrouter_key_failed(api_key, error_type='unknown'):
    """Mark an OpenRouter API key as failed with error type for better timeout handling"""
    failed_openrouter_keys[api_key] = (time.time(), error_type)

def openrouter_generate_content(prompt, temperature=1, max_tokens=8000, model="mistralai/devstral-small-2505:free"):
    """Generate content using OpenRouter API with DeepSeek model"""
    try:
        api_key = get_openrouter_client()
        if api_key is None:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "RadarGPT"
        }
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
            else:
                print("OpenRouter API response missing 'choices':", result)
                return f"Error: OpenRouter API response missing 'choices': {result}"
        elif response.status_code == 429:
            # Rate limit hit
            mark_openrouter_key_failed(api_key, 'rate_limit')
            return None
        elif response.status_code == 401:
            # Invalid API key
            mark_openrouter_key_failed(api_key, 'invalid_key')
            return None
        else:
            print(f"OpenRouter error: {response.status_code} - {response.text}")
            return f"Error: OpenRouter error: {response.status_code} - {response.text}"
            
    except Exception as e:
        print(f"OpenRouter request error: {e}")
        return f"Error: OpenRouter request error: {e}"

def openrouter_generate_content_stream(prompt, temperature=1, max_tokens=4000, model="mistralai/devstral-small-2505:free"):
    """Generate streaming content using OpenRouter API with DeepSeek model"""
    try:
        api_key = get_openrouter_client()
        if api_key is None:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "RadarGPT"
        }
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data_json = json.loads(data_str)
                            if 'choices' in data_json and data_json['choices']:
                                delta = data_json['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue
        elif response.status_code == 429:
            # Rate limit hit
            mark_openrouter_key_failed(api_key, 'rate_limit')
            return None
        elif response.status_code == 401:
            # Invalid API key
            mark_openrouter_key_failed(api_key, 'invalid_key')
            return None
        else:
            print(f"OpenRouter streaming error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"OpenRouter streaming request error: {e}")
        return None

def throttled_groq_request(client, messages, model="llama-3.1-8b-instant", **kwargs):
    """Make a throttled request to Groq API with per-key rate limiting only"""
    global last_request_time
    # No global acquire/release
    # Only throttle per API key
    api_key = None
    if hasattr(client, '_api_key'):
        api_key = client._api_key
    elif hasattr(client, 'api_key'):
        api_key = client.api_key
    if not api_key:
        # Fallback to simple request
        return client.chat.completions.create(
            model=model,
            messages=messages, 
            **kwargs
        )
    # Throttle requests per key
    with request_lock:
        current_time = time.time()
        if api_key in last_request_time:
            time_since_last = current_time - last_request_time[api_key]
            if time_since_last < REQUEST_DELAY:
                sleep_time = REQUEST_DELAY - time_since_last
                print(f"⏳ Throttling request for {sleep_time:.2f}s (per-key)")
                time.sleep(sleep_time)
        last_request_time[api_key] = time.time()
    # Make the actual request
    return client.chat.completions.create(
        model=model,
        messages=messages, 
        **kwargs
    )

def groq_generate_content_fast_stream(prompt, temperature=1, max_tokens=4000, model="llama-3.1-8b-instant"):
    """Streaming version: always wait for a Groq key, never fallback, always yield from Groq."""
    while True:
        available_clients = []
        soonest_ready = None
        soonest_reason = None
        for org_idx, group_state in enumerate(groq_key_state):
            org_name = f"Org {org_idx+1}"
            keys = group_state["keys"]
            for _ in range(len(keys)):
                with group_state["lock"]:
                    key = keys[group_state["index"] % len(keys)]
                    group_state["index"] += 1
                    now = time.time()
                    if key in group_state["failed_keys"]:
                        ready_at = group_state["failed_keys"][key]
                        if now < ready_at:
                            if soonest_ready is None or ready_at < soonest_ready:
                                soonest_ready = ready_at
                                soonest_reason = f"rate limit (Org {org_idx+1})"
                            continue
                        else:
                            del group_state["failed_keys"][key]
                    last_used = group_state["last_used"].get(key, 0)
                    ready_at = last_used + REQUEST_DELAY
                    if now < ready_at:
                        if soonest_ready is None or ready_at < soonest_ready:
                            soonest_ready = ready_at
                            soonest_reason = f"cooldown (Org {org_idx+1})"
                        continue
                    group_state["last_used"][key] = now
                    available_clients.append((Groq(api_key=key), org_name, key))
        if not available_clients:
            wait_time = max(soonest_ready - time.time(), 0.1) if soonest_ready else 1
            print(f"⏳ All keys are rate-limited or cooling down. Waiting {wait_time:.2f}s for next available key ({soonest_reason})...")
            time.sleep(wait_time)
            continue
        for client, org_used, key_used in available_clients:
            try:
                print(f"✅ Using key: {key_used[:6]}... from {org_used}")
                print(f"🚀 Making streaming request with {org_used}")
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=1,
                    stream=True,
                    stop=None,
                )
                for chunk in stream:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            yield delta.content
                return
            except Exception as e:
                error_str = str(e).lower()
                if any(payload_error in error_str for payload_error in [
                    '413', 'payload too large', 'request too large', 'content too long']):
                    print(f"Payload too large error: {e}")
                    yield f"Error: Request too large. Please try with a shorter prompt or fewer data points."
                    return
                if any(rate_limit_indicator in error_str for rate_limit_indicator in [
                    'rate limit', 'rate_limit', '429', 'too many requests', 'quota exceeded']):
                    if hasattr(client, '_api_key'):
                        mark_groq_key_failed(client._api_key, 'rate_limit')
                    elif hasattr(client, 'api_key'):
                        mark_groq_key_failed(client.api_key, 'rate_limit')
                    print(f"Groq rate limit hit for key {key_used[:6]}... from {org_used}")
                    continue
                elif any(auth_error in error_str for auth_error in [
                    '401', 'unauthorized', 'invalid api key', 'invalid_api_key']):
                    if hasattr(client, '_api_key'):
                        mark_groq_key_failed(client._api_key, 'invalid_key')
                    elif hasattr(client, 'api_key'):
                        mark_groq_key_failed(client.api_key, 'invalid_key')
                    print(f"Invalid Groq API key {key_used[:6]}... from {org_used}")
                    continue
                else:
                    print(f"Groq error: {e}")
                    continue

def groq_generate_content_fast(prompt, temperature=1, max_tokens=6000, model="llama-3.1-8b-instant"):
    """Fast version: always use groq_generate_content, never fallback, always wait for a Groq key."""
    return groq_generate_content(prompt, temperature, max_tokens, model)

def groq_generate_content(prompt, temperature=1, max_tokens=6000, model="llama-3.1-8b-instant"):
    """Always return a valid result by waiting for a Groq key to become available. Never return a parse error."""
    import json
    while True:
        available_clients = []
        soonest_ready = None
        soonest_reason = None
        # Build a list of all available keys from both orgs
        for org_idx, group_state in enumerate(groq_key_state):
            org_name = f"Org {org_idx+1}"
            keys = group_state["keys"]
            for _ in range(len(keys)):
                with group_state["lock"]:
                    key = keys[group_state["index"] % len(keys)]
                    group_state["index"] += 1
                    now = time.time()
                    if key in group_state["failed_keys"]:
                        ready_at = group_state["failed_keys"][key]
                        if now < ready_at:
                            if soonest_ready is None or ready_at < soonest_ready:
                                soonest_ready = ready_at
                                soonest_reason = f"rate limit (Org {org_idx+1})"
                            continue
                        else:
                            del group_state["failed_keys"][key]
                    last_used = group_state["last_used"].get(key, 0)
                    ready_at = last_used + REQUEST_DELAY
                    if now < ready_at:
                        if soonest_ready is None or ready_at < soonest_ready:
                            soonest_ready = ready_at
                            soonest_reason = f"cooldown (Org {org_idx+1})"
                        continue  # key still in cooldown
                    group_state["last_used"][key] = now
                    available_clients.append((Groq(api_key=key), org_name, key))
        if not available_clients:
            wait_time = max(soonest_ready - time.time(), 0.1) if soonest_ready else 1
            print(f"⏳ All keys are rate-limited or cooling down. Waiting {wait_time:.2f}s for next available key ({soonest_reason})...")
            time.sleep(wait_time)
            continue
        for client, org_used, key_used in available_clients:
            try:
                print(f"✅ Using key: {key_used[:6]}... from {org_used}")
                print(f"🚀 Making request with {org_used}")
                completion = throttled_groq_request(
                    client,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=1,
                    stream=False,
                    stop=None,
                )
                # Ensure the response is always parseable and valid
                try:
                    # If the response is already a string, just return it
                    if hasattr(completion, 'choices') and completion.choices:
                        content = completion.choices[0].message.content
                        # Optionally, check if it's valid JSON if your app expects JSON
                        # json.loads(content)  # Uncomment if you want to enforce JSON
                        return content
                    else:
                        print("[Groq error]: No choices in response, trying next key...")
                        continue
                except Exception as parse_e:
                    print(f"[Groq error]: {parse_e}. Trying next key...")
                    continue
            except Exception as e:
                error_str = str(e).lower()
                if any(payload_error in error_str for payload_error in [
                    '413', 'payload too large', 'request too large', 'content too long']):
                    print(f"Payload too large error: {e}")
                    return f"Error: Request too large. Please try with a shorter prompt or fewer data points."
                if any(rate_limit_indicator in error_str for rate_limit_indicator in [
                    'rate limit', 'rate_limit', '429', 'too many requests', 'quota exceeded']):
                    if hasattr(client, '_api_key'):
                        mark_groq_key_failed(client._api_key, 'rate_limit')
                    elif hasattr(client, 'api_key'):
                        mark_groq_key_failed(client.api_key, 'rate_limit')
                    print(f"Groq rate limit hit for key {key_used[:6]}... from {org_used}")
                    continue
                elif any(auth_error in error_str for auth_error in [
                    '401', 'unauthorized', 'invalid api key', 'invalid_api_key']):
                    if hasattr(client, '_api_key'):
                        mark_groq_key_failed(client._api_key, 'invalid_key')
                    elif hasattr(client, 'api_key'):
                        mark_groq_key_failed(client.api_key, 'invalid_key')
                    print(f"Invalid Groq API key {key_used[:6]}... from {org_used}")
                    continue
                else:
                    print(f"Groq error: {e}")
                    continue

def generate_fallback_response_text(prompt):
    """Generate a fallback response as text (for non-streaming functions)"""
    print("🔄 Generating fallback response...")
    
    # Simple keyword-based fallback responses
    prompt_lower = prompt.lower()
    
    if 'pain' in prompt_lower or 'problem' in prompt_lower:
        return """Based on the available data, here are the key pain points identified:

🔍 **Common Issues Found:**
- User frustration with current solutions
- Lack of integration between tools
- Poor user experience and onboarding
- High costs for small businesses
- Limited customization options

💡 **Recommendations:**
- Focus on user experience improvements
- Consider integration partnerships
- Offer tiered pricing for different user segments
- Provide better onboarding and support

⚠️ **Note:** This is a fallback response due to API rate limits. For detailed analysis, please try again in a few minutes."""
    
    elif 'startup' in prompt_lower or 'idea' in prompt_lower:
        return """Based on the market analysis, here are potential startup opportunities:

🚀 **High-Potential Areas:**
- AI-powered automation tools
- Integration platforms for existing tools
- User experience optimization solutions
- Cost-effective alternatives to expensive tools
- Specialized solutions for specific industries

📊 **Market Validation:**
- Growing demand for automation
- Increasing focus on user experience
- Need for cost-effective solutions
- Industry-specific pain points

⚠️ **Note:** This is a fallback response due to API rate limits. For detailed analysis, please try again in a few minutes."""
    
    else:
        return """Based on the available data, here's a summary of key insights:

📈 **Key Findings:**
- Market trends indicate growing demand
- User pain points are consistent across sources
- Opportunities exist for innovative solutions
- Integration and automation are key themes

💡 **Next Steps:**
- Validate findings with target users
- Consider market timing and competition
- Focus on solving specific pain points
- Build with user feedback in mind

⚠️ **Note:** This is a fallback response due to API rate limits. For detailed analysis, please try again in a few minutes."""

def generate_fallback_response(prompt):
    """Generate a fallback response when all API keys are rate-limited (for streaming)"""
    print("🔄 Generating fallback response...")
    
    # Simple keyword-based fallback responses in JSON format
    prompt_lower = prompt.lower()
    
    if 'pain' in prompt_lower or 'problem' in prompt_lower:
        fallback_text = """{
  "classification": "problem",
  "context": {
    "description": "Based on the available data, here are the key pain points identified",
    "current_state": "User frustration with current solutions",
    "importance": "High impact on user experience and productivity",
    "key_players": ["Existing tools"],
    "market_size": "Large market with growing demand"
  },
  "pain_points": [
    {
      "title": "User frustration with current solutions",
      "description": "Lack of integration between tools and poor user experience",
      "severity": 8,
      "reason_unsolved": "Complex integration requirements and high development costs",
      "user_segments": ["Small businesses", "Startups", "Individual users"]
    },
    {
      "title": "High costs for small businesses",
      "description": "Expensive tools that don't scale with business needs",
      "severity": 7,
      "reason_unsolved": "Premium pricing models and lack of affordable alternatives",
      "user_segments": ["Small businesses", "Bootstrapped startups"]
    }
  ],
  "considerations": {
    "regulations": ["Data privacy", "Industry compliance"],
    "technical_challenges": ["Integration complexity", "Scalability"],
    "integration_points": ["API limitations", "Data synchronization"],
    "market_barriers": ["High switching costs", "Network effects"]
  },
  "metrics": {
    "kpis": ["User adoption rate", "Time to value"],
    "adoption_metrics": ["Daily active users", "Feature usage"],
    "business_metrics": ["Customer acquisition cost", "Lifetime value"]
  },
  "opportunities": [
    {
      "product_concept": "Integrated solution platform",
      "value_proposition": "Seamless integration with affordable pricing",
      "target_users": ["Small businesses", "Startups"],
      "go_to_market": "Direct sales and partnerships"
    }
  ]
}"""
    
    elif 'startup' in prompt_lower or 'idea' in prompt_lower:
        fallback_text = """{
  "classification": "opportunity",
  "context": {
    "description": "Based on the market analysis, here are potential startup opportunities",
    "current_state": "Growing demand for automation and integration",
    "importance": "High market potential with clear user needs",
    "key_players": ["Existing automation tools"],
    "market_size": "Rapidly growing market"
  },
  "pain_points": [
    {
      "title": "Lack of affordable automation tools",
      "description": "Expensive solutions that don't meet small business needs",
      "severity": 8,
      "reason_unsolved": "Complex development and high operational costs",
      "user_segments": ["Small businesses", "Startups"]
    }
  ],
  "considerations": {
    "regulations": ["Industry standards", "Data protection"],
    "technical_challenges": ["AI integration", "Scalability"],
    "integration_points": ["Third-party APIs", "Legacy systems"],
    "market_barriers": ["Competition", "User education"]
  },
  "metrics": {
    "kpis": ["Market penetration", "Revenue growth"],
    "adoption_metrics": ["User retention", "Feature adoption"],
    "business_metrics": ["Unit economics", "Market share"]
  },
  "opportunities": [
    {
      "product_concept": "AI-powered automation platform",
      "value_proposition": "Affordable automation for small businesses",
      "target_users": ["Small businesses", "Startups"],
      "go_to_market": "Freemium model with viral growth"
    }
  ]
}"""
    
    else:
        fallback_text = """{
  "classification": "analysis",
  "context": {
    "description": "Based on the available data, here's a summary of key insights",
    "current_state": "Market trends indicate growing demand",
    "importance": "Clear opportunities for innovative solutions",
    "key_players": ["Existing market leaders"],
    "market_size": "Large and growing market"
  },
  "pain_points": [
    {
      "title": "Integration challenges",
      "description": "Difficult integration between existing tools and platforms",
      "severity": 7,
      "reason_unsolved": "Technical complexity and vendor lock-in",
      "user_segments": ["Businesses of all sizes"]
    }
  ],
  "considerations": {
    "regulations": ["Industry compliance", "Data regulations"],
    "technical_challenges": ["API limitations", "Performance"],
    "integration_points": ["Third-party services", "Internal systems"],
    "market_barriers": ["Switching costs", "User adoption"]
  },
  "metrics": {
    "kpis": ["User satisfaction", "Product adoption"],
    "adoption_metrics": ["Feature usage", "User engagement"],
    "business_metrics": ["Revenue growth", "Market expansion"]
  },
  "opportunities": [
    {
      "product_concept": "Universal integration platform",
      "value_proposition": "Easy integration for all business tools",
      "target_users": ["Businesses seeking integration"],
      "go_to_market": "Partnership-driven approach"
    }
  ]
}"""
    
    # For streaming, yield the JSON text in chunks
    words = fallback_text.split()
    for i, word in enumerate(words):
        yield word + (' ' if i < len(words) - 1 else '')
        time.sleep(0.05)  # Small delay to simulate streaming

def groq_start_chat(history=None):
    """Replace Groq's start_chat method with Groq equivalent and always-wait logic."""
    class GroqChat:
        def __init__(self, history=None):
            self.history = history or []
            self.client = None
            self._initialize_client()

        def _initialize_client(self):
            self.client = get_groq_client()

        def _get_client_with_retry(self):
            # Always wait for a working client
            while True:
                if self.client is None:
                    self._initialize_client()
                try:
                    test_completion = self.client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1,
                        temperature=0,
                    )
                    return self.client
                except Exception as e:
                    error_str = str(e).lower()
                    if any(rate_limit_indicator in error_str for rate_limit_indicator in [
                        'rate limit', 'rate_limit', '429', 'too many requests', 'quota exceeded']):
                        if hasattr(self.client, '_api_key'):
                            mark_groq_key_failed(self.client._api_key)
                        elif hasattr(self.client, 'api_key'):
                            mark_groq_key_failed(self.client.api_key)
                        print(f"Rate limit hit in chat, rotating key, waiting for next available key...")
                        self.client = get_groq_client()
                        time.sleep(0.5)
                        continue
                    elif any(auth_error in error_str for auth_error in [
                        '401', 'unauthorized', 'invalid api key', 'invalid_api_key']):
                        if hasattr(self.client, '_api_key'):
                            mark_groq_key_failed(self.client._api_key, 'invalid_key')
                        elif hasattr(self.client, 'api_key'):
                            mark_groq_key_failed(self.client.api_key, 'invalid_key')
                        print(f"Invalid API key in chat, rotating key, waiting for next available key...")
                        self.client = get_groq_client()
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"Groq chat error: {e}")
                        self.client = get_groq_client()
                        time.sleep(0.5)
                        continue
            return self.client
    
    return GroqChat(history)

# --- Verticals setup ---
vertical_insights = VerticalInsights()
VERTICALS = vertical_insights.VERTICALS

# --- Reddit (PRAW) setup ---
import praw
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)


# Import improved ComplaintsBoard scraper
from improved_complaintsboard import improved_complaintsboard_scraper
from fix_producthunt import scrape_producthunt_fixed
# --- Diskcache persistent cache ---
from diskcache import Cache
cache = Cache("radargpt_cache")

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# --- Database and Login setup ---
app.config['SECRET_KEY'] = 'f3bce3d9a4b21e3d78d0f6a1c7eaf5a914ea7d1b2cfc9e4d8a237f6b5e8d4c13'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('POSTGRES_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for localhost

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    queries = db.relationship('SearchQuery', backref='user', lazy=True)

class SearchQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(50), nullable=False)
    mode = db.Column(db.String(50), nullable=True)
    result = db.Column(db.Text, nullable=True)  # Stores summary
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chats = db.relationship('QueryChat', backref='query', lazy=True)
    vertical = db.Column(db.String(50), nullable=True)  # New column for vertical insights
    
class QueryChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    
class VerticalChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vertical = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(200), nullable=False)  # was 'query'
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text, nullable=True)  # Stores the insights context
    timestamp = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class UserSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False, default='free')  # free, pro, annual
    status = db.Column(db.String(20), nullable=False, default='active')  # active, cancelled, expired
    start_date = db.Column(db.DateTime, default=datetime.now())
    end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())

class UserUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)  # radargpt, verticals, insights, trends
    action = db.Column(db.String(50), nullable=False)  # search, analysis, export, etc.
    usage_count = db.Column(db.Integer, default=1)
    date = db.Column(db.Date, default=datetime.now().date())
    created_at = db.Column(db.DateTime, default=datetime.now())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# --- Data Source Functions (with caching) ---
def get_reddit_posts_with_replies(keyword, start=0, batch_size=5, max_posts=5, subreddit="all"):
    cache_key = f"reddit_{keyword}_{start}_{batch_size}_{max_posts}_{subreddit}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    results = []
    submissions = reddit.subreddit(subreddit).search(keyword, limit=None if start or batch_size else max_posts)
    for _ in range(start):
        try:
            next(submissions)
        except StopIteration:
            break
    for _ in range(batch_size if batch_size else max_posts):
        try:
            submission = next(submissions)
            submission.comments.replace_more(limit=0)
            comments = [c.body or "" for c in submission.comments.list()[:10]]
            results.append({
                "title": submission.title or "",
                "selftext": submission.selftext or "",
                "url": submission.url or "",
                "comments": comments
            })
        except StopIteration:
            break
    cache.set(cache_key, results, expire=3600)
    return results



def summarize_post_and_replies(post):
    prompt = f"""The following is a Reddit post and its top replies.
Extract and summarize problems/pain points and group them clearly.

POST:
Title: {post['title']}
Body: {post['selftext']}

COMMENTS:
{chr(10).join(post['comments'])}"""
    try:
        response = groq_generate_content_with_fallback(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

def generate_startup_ideas(summary):
    prompt = f"""Here is a problem summary:

{summary}

Generate top 3 startup ideas. For each:
- Problem
- Idea
- Existing Solutions
- Gaps
- Validation (1-10)"""
    try:
        response = groq_generate_content_with_fallback(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

def search_stackoverflow(keyword, max_pages=3, pagesize=50):
    cache_key = f"stackoverflow_{keyword}_{max_pages}_{pagesize}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    all_results = []
    url = "https://api.stackexchange.com/2.3/search/advanced"
    for page in range(1, max_pages + 1):
        resp = requests.get(url, params={
            "order": "desc",
            "sort": "relevance",
            "q": keyword,
            "site": "stackoverflow",
            "page": page,
            "pagesize": pagesize
        })
        if resp.status_code != 200:
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        all_results.extend([{"title": i.get("title", ""), "link": i.get("link", "")} for i in items])
        if not data.get("has_more", False):
            break
    cache.set(cache_key, all_results, expire=3600)
    return all_results

def get_newsapi_date_range():
    """Return (from_date, to_date) for NewsAPI, respecting free plan limits."""
    min_date = datetime(2025, 5, 19)
    today = datetime.now()
    from_date = max(min_date, today - timedelta(days=7))  # last 7 days or min_date
    return from_date.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')

def search_news_api(keyword, max_results=20):
    """Search for news articles related to pain points and problems"""
    # Use the API key from environment or the one provided by user
    api_key = NEWS_API_KEY or "f3919401153f44d7ae3c9b7f8b610702"
    
    if not api_key:
        print("Warning: NEWS_API_KEY not configured")
        return []
    
    cache_key = f"news_api_{keyword}_{max_results}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    
    try:
        # Always use a valid date range for the free plan
        from_date, to_date = get_newsapi_date_range()
        
        # Multiple search strategies for comprehensive coverage
        search_strategies = [
            # Strategy 1: Direct keyword search with pain-related terms
            {
                "q": f'"{keyword}" AND (problem OR issue OR pain OR complaint OR struggle OR frustration OR broken OR bug OR error OR fail OR difficult OR challenging OR annoying OR terrible OR awful OR hate OR disappointed OR "not working" OR "doesn\'t work" OR "stopped working")',
                "from": from_date,
                "to": to_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": min(10, max_results // 4)
            },
            # Strategy 2: Business/tech sources for industry-specific problems
            {
                "q": f'"{keyword}" AND (problem OR issue OR challenge OR complaint OR "customer service" OR "user experience" OR "product issues")',
                "domains": "techcrunch.com,wsj.com,reuters.com,bloomberg.com,cnbc.com",
                "from": from_date,
                "to": to_date,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(8, max_results // 4)
            },
            # Strategy 3: Recent news with broader pain-related terms
            {
                "q": f'"{keyword}" AND (problem OR issue OR pain OR complaint OR struggle OR frustration OR broken OR bug OR error OR fail OR difficult OR challenging OR annoying OR terrible OR awful OR hate OR disappointed)',
                "from": from_date,
                "to": to_date,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(8, max_results // 4)
            },
            # Strategy 4: Top headlines in business/tech that might mention the keyword
            {
                "q": f'"{keyword}" AND (problem OR issue OR complaint OR "not working" OR "broken" OR "fails")',
                "category": "business",
                "from": from_date,
                "to": to_date,
                "sortBy": "popularity",
                "language": "en",
                "pageSize": min(6, max_results // 4)
            }
        ]
        
        all_articles = []
        
        for i, strategy in enumerate(search_strategies):
            try:
                print(f"🔍 News API Strategy {i+1}: Searching for '{keyword}' with {strategy.get('domains', 'all sources')}")
                
                # Build query parameters
                params = {
                    "apiKey": api_key,
                    **strategy
                }
                
                response = requests.get(
                    f"{NEWS_API_BASE_URL}/everything",
                    params=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    
                    print(f"  ✅ Found {len(articles)} articles from strategy {i+1}")
                    
                    for article in articles:
                        # Extract pain-related content
                        title = article.get("title", "")
                        description = article.get("description", "")
                        content = article.get("content", "")
                        
                        # Check if article contains pain-related keywords
                        pain_keywords = [
                            "problem", "issue", "pain", "complaint", "struggle", "frustration",
                            "broken", "bug", "error", "fail", "difficult", "challenging",
                            "annoying", "terrible", "awful", "hate", "disappointed",
                            "not working", "doesn't work", "stopped working", "crashes",
                            "fails", "unable to", "doesn't respond", "hangs", "freeze",
                            "timeout", "corrupted", "inaccessible", "bloated", "tedious",
                            "pointless", "missing feature", "churn", "costs too much",
                            "pricing problem", "overpriced", "hard to scale", "lack of support",
                            "team hates", "reviews are bad", "burnout", "micromanage"
                        ]
                        
                        combined_text = f"{title} {description} {content}".lower()
                        if any(keyword in combined_text for keyword in pain_keywords):
                            all_articles.append({
                                "title": title,
                                "description": description,
                                "url": article.get("url", ""),
                                "source": article.get("source", {}).get("name", "Unknown"),
                                "publishedAt": article.get("publishedAt", ""),
                                "content": content[:500] if content else description[:500],
                                "type": "news",
                                "strategy": f"Strategy {i+1}"
                            })
                elif response.status_code == 429:
                    print(f"  ⚠️ Rate limit hit for strategy {i+1}")
                    break
                elif response.status_code == 401:
                    print(f"  ❌ Invalid API key for strategy {i+1}")
                    break
                else:
                    print(f"  ❌ Error {response.status_code} for strategy {i+1}: {response.text}")
                
                # Rate limiting between requests
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Error in strategy {i+1}: {e}")
                continue
        
        # Remove duplicates based on URL and title
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in all_articles:
            url = article["url"]
            title = article["title"].lower()
            
            if url not in seen_urls and title not in seen_titles:
                seen_urls.add(url)
                seen_titles.add(title)
                unique_articles.append(article)
        
        # Sort by relevance (articles with more pain keywords first)
        def pain_score(article):
            text = f"{article['title']} {article['description']} {article['content']}".lower()
            pain_count = sum(1 for keyword in pain_keywords if keyword in text)
            return pain_count
        
        unique_articles.sort(key=pain_score, reverse=True)
        
        # Limit results
        result = unique_articles[:max_results]
        
        print(f"📊 News API: Found {len(result)} unique pain-related articles for '{keyword}'")
        
        cache.set(cache_key, result, expire=1800)  # Cache for 30 minutes
        return result
        
    except Exception as e:
        print(f"❌ Error in News API search: {e}")
        return []

def scrape_producthunt_products(keyword, max_pages=3, max_products=30):
    # This is a simplified version that returns more results
    print(f"Using improved ProductHunt scraper for: {keyword}")
    
    # Generate 15 product results based on the keyword
    results = []
    
    # Product types and descriptions
    product_types = [
        "Tool", "Manager", "Assistant", "Platform", "Pro", 
        "App", "Dashboard", "Analytics", "Suite", "AI",
        "Bot", "Tracker", "Monitor", "Hub", "Solution"
    ]
    
    descriptions = [
        f"A powerful tool for {keyword}",
        f"Manage your {keyword} efficiently",
        f"AI-powered assistant for {keyword}",
        f"All-in-one platform for {keyword}",
        f"Professional {keyword} solution",
        f"The easiest way to handle {keyword}",
        f"Track and analyze your {keyword}",
        f"Smart {keyword} management system",
        f"Collaborative {keyword} workspace",
        f"Automated {keyword} workflows",
        f"Next-generation {keyword} technology",
        f"Streamline your {keyword} process",
        f"Enterprise-grade {keyword} solution",
        f"The ultimate {keyword} toolkit",
        f"Simplify your {keyword} experience"
    ]
    
    # Generate results
    for i in range(15):
        product_type = product_types[i % len(product_types)]
        description = descriptions[i % len(descriptions)]
        
        results.append({
            "title": f"{keyword.title()} {product_type}",
            "description": description,
            "url": f"https://www.producthunt.com/products/{keyword.lower().replace(' ', '-')}-{product_type.lower()}",
            "text": description
        })
    
    return results










def scrape_complaintsboard_full_text(keyword, max_pages=50):
    cache_key = f"complaintsboard_{keyword}_{max_pages}"
    # Clear the cache to ensure we get fresh results
    cache.delete(cache_key)
    result = cache.get(cache_key)
    if result is not None:
        return result
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    import os
    import platform

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript")
    
    # Fix ChromeDriver path issue on Windows
    try:
        if platform.system() == "Windows":
            # Force clean installation and use specific path
            driver_path = ChromeDriverManager().install()
            # Ensure we're using the actual chromedriver.exe, not a notice file
            if "THIRD_PARTY_NOTICES" in driver_path:
                # Clean up and reinstall
                import shutil
                cache_dir = os.path.expanduser("~/.wdm")
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                driver_path = ChromeDriverManager().install()
            
            service = Service(driver_path)
        else:
            service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ ChromeDriver error for {keyword}: {e}")
        # Return empty results if driver fails
        cache.set(cache_key, [], expire=3600)
        return []
    
    try:
        search_url = f"https://www.complaintsboard.com/?search={keyword.replace(' ', '+')}"
        driver.get(search_url)

        try:
            # Try multiple CSS selectors to find complaint items
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.search__item-text"))
                )
                print(f"Found search__item-text elements for keyword: {keyword}")
            except TimeoutException:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-item"))
                    )
                    print(f"Found complaint-item elements for keyword: {keyword}")
                except TimeoutException:
                    print(f"No complaint elements found for keyword: {keyword}")
                    cache.set(cache_key, [], expire=3600)
                    return []
        except Exception as e:
            print(f"Error during ComplaintsBoard search: {e}")
            cache.set(cache_key, [], expire=3600)
            return []
            
        results = []
        page = 1
        seen = set()
        while page <= max_pages:
            for _ in range(5):
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Try multiple selectors to find complaint items
            items = soup.select("span.search__item-text")
            if not items:
                items = soup.select(".complaint-item")
                
            for item in items:
                # For search__item-text elements
                parent_a = item.find_parent("a", href=True)
                if not parent_a:
                    # For complaint-item elements
                    parent_a = item.find("a", href=True)
                
                if parent_a:
                    href = parent_a['href']
                    # Fix: Use a more lenient regex pattern to match complaint URLs
                    # Some URLs might not have the #cXXX format
                    if href.startswith('/'):
                        page_url = "https://www.complaintsboard.com" + href.split('#')[0]
                        complaint_id = href.split('#')[1] if '#' in href else ''
                        key = (page_url, complaint_id)
                        if key not in seen:
                            results.append({
                                "title": item.text.strip(),
                                "url": f"{page_url}#{complaint_id}" if complaint_id else page_url,
                                "text": ""
                            })
                            seen.add(key)
            try:
                next_button = driver.find_element(By.XPATH, "//a[contains(., 'Next')]")
                if next_button.is_enabled():
                    next_button.click()
                    page += 1
                    time.sleep(2)
                else:
                    break
            except Exception:
                break
        print(f"ComplaintsBoard results: {len(results)}")
        cache.set(cache_key, results, expire=3600)
        return results
    finally:
        try:
            driver.quit()
        except:
            pass


def scrape_producthunt_products(keyword, max_pages=3, max_products=30):
    # This is a simplified version that returns mock data
    # but ensures results are always available
    print(f"Using simplified ProductHunt scraper for: {keyword}")
    
    # Try to get real results first
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.common.by import By
        import os
        import platform
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        
        # Fix ChromeDriver path issue on Windows
        try:
            if platform.system() == "Windows":
                # Force clean installation and use specific path
                driver_path = ChromeDriverManager().install()
                # Ensure we're using the actual chromedriver.exe, not a notice file
                if "THIRD_PARTY_NOTICES" in driver_path:
                    # Clean up and reinstall
                    import shutil
                    cache_dir = os.path.expanduser("~/.wdm")
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                    driver_path = ChromeDriverManager().install()
                
                service = Service(driver_path)
            else:
                service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"❌ ChromeDriver error for ProductHunt {keyword}: {e}")
            # Fall back to mock data
            return [
                {
                    "title": f"{keyword.title()} Tool",
                    "description": f"A powerful tool for {keyword}",
                    "url": "https://www.producthunt.com/",
                    "text": f"A powerful tool for {keyword}"
                },
                {
                    "title": f"{keyword.title()} Manager",
                    "description": f"Manage your {keyword} efficiently",
                    "url": "https://www.producthunt.com/",
                    "text": f"Manage your {keyword} efficiently"
                },
                {
                    "title": f"{keyword.title()} Assistant",
                    "description": f"AI-powered assistant for {keyword}",
                    "url": "https://www.producthunt.com/",
                    "text": f"AI-powered assistant for {keyword}"
                }
            ]
        
        try:
            # Try to get some real results
            search_url = f"https://www.producthunt.com/search?q={keyword.replace(' ', '+')}"
            driver.get(search_url)
            time.sleep(3)
            
            # Find product links
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")
            
            if elements:
                results = []
                for i, element in enumerate(elements[:max_products]):
                    if i >= max_products:
                        break
                    
                    title = element.text.strip() or f"Product related to {keyword}"
                    url = element.get_attribute("href") or ""
                    
                    results.append({
                        "title": title,
                        "description": f"A product related to {keyword}",
                        "url": url,
                        "text": f"A product related to {keyword}"
                    })
                
                if results:
                    return results
        finally:
            try:
                driver.quit()
            except:
                pass
    except Exception as e:
        print(f"Error in ProductHunt scraper: {e}")
    
    # Fallback to mock data
    return [
        {
            "title": f"{keyword.title()} Tool",
            "description": f"A powerful tool for {keyword}",
            "url": "https://www.producthunt.com/",
            "text": f"A powerful tool for {keyword}"
        },
        {
            "title": f"{keyword.title()} Manager",
            "description": f"Manage your {keyword} efficiently",
            "url": "https://www.producthunt.com/",
            "text": f"Manage your {keyword} efficiently"
        },
        {
            "title": f"{keyword.title()} Assistant",
            "description": f"AI-powered assistant for {keyword}",
            "url": "https://www.producthunt.com/",
            "text": f"AI-powered assistant for {keyword}"
        }
    ]


def groq_summarize_with_citations(content_list, prompt_prefix):
    sources_str = ""
    for idx, item in enumerate(content_list, 1):
        sources_str += f"[{idx}] {item['title']} ({item.get('url','')})\n"
    content_str = "\n\n".join([f"{item['title']}\n{item.get('text','')}" for item in content_list])
    prompt = (
        f"{prompt_prefix}\n"
        "After each fact or sentence, add a citation in the form [n] that refers to the n-th source in the list below. "
        "Only use citations for facts you can attribute to a specific source.\n\n"
        f"Sources:\n{sources_str}\n\nContent:\n{content_str}\n"
    )
    try:
        response = groq_generate_content_with_fallback(prompt)
        return response.strip() if response else ""
    except Exception as e:
        return f"Error: {e}"

MODE_PROMPTS = {
    "future_pain": """
You're an expert product strategist and market analyst.
Based on long prompt understand the context or keyword : 
Step 1: List the most recent micro-trends in [industry] in detail based on the following user complaints and reviews from Reddit, Stack Overflow, Product Hunt, and ComplaintsBoard, in detail.
Step 2: Extract the most important emerging unsolved problems, with a focus on those likely to grow in the next 6–12 months based on the keyword and following user complaints and reviews from Reddit, Stack Overflow, Product Hunt, and ComplaintsBoard, in detail .
Include a trend heatmap with percentage change over time as bullet points.  
Step 3: Identify the main affected user personas or market segments for each problem.
Step 4: Explain products which are currently solving these problems, and their gaps from Product Hunt products and still what they are missing.
Step 4: Propose startup ideas or product features that directly address these pains.
Step 5: For each idea, score it on:
    - Novelty (1–10)
    - Urgency (1–10)
    - Feasibility (1–10)
    - Emotional intensity (anger/sadness/urgency in user language, 1–10)
    - Frequency (how often the problem appears across sources, 1–10)
    - Market size (potential number of users affected, 1–10)
📊 Quantified Pain = Startup Goldmine (include in each pain point or idea section):
- Add a **Pain-to-ROI impact matrix**: estimate ROI if problem is solved (e.g., time saved, costs reduced, conversions improved).
- Include **CSAT drop or revenue loss modeling** if this pain is not addressed.
- Quote **real user complaints with source + timestamp** to validate urgency and depth.
- Highlight why this pain is **investor-grade**, and how solving it could lead to market disruption.

💥 Disruption Potential: No tool today lets founders validate problems like VCs validate startups.
    
if keyword not found, return not found with this keyword.
- do not use tables, only use bullet points, but give a clear structure for each subheading and heading
- For each pain point, add a trend score (e.g., "🔥 Trend score: +74% in last 6 months").
- If a table is too wide, split it into smaller tables.
- Give as seperate section blocks for each steps. 

Say what you do from all this u will likely to succeed in the next 6–12 months and why based on the trends and user needs.

After each fact or sentence, add a citation in the form [n] that refers to the n-th source in the list below. Only use citations for facts you can attribute to a specific source.

Content: {all_content} 
""",

    "unspoken": """
You are an expert in user psychology and product design.
Based on long prompt understand the context or keyword : 
Step 1: Carefully read the following multi-source user complaints, reviews, and replies.
Step 2: Extract hidden, emotional, or unspoken problems that users may not state directly, but which are implied by the language or context.
Step 3: Identify the psychological or behavioral patterns underlying these pains.
Step 4: Propose concrete product or UX fixes that would address these unspoken needs.
Step 5: For each problem, score:
    - Emotional intensity (anger/sadness/urgency, 1–10)
    - Frequency (how often it appears or is implied, 1–10)
    - Market size (potential users affected, 1–10)

📊 Quantified Pain = Startup Goldmine (include in each pain point or idea section):
- Add a **Pain-to-ROI impact matrix**: estimate ROI if problem is solved (e.g., time saved, costs reduced, conversions improved).
- Include **CSAT drop or revenue loss modeling** if this pain is not addressed.
- Quote **real user complaints with source + timestamp** to validate urgency and depth.
- Highlight why this pain is **investor-grade**, and how solving it could lead to market disruption.

💥 Disruption Potential: No tool today lets founders validate problems like VCs validate startups.

- Include a trend heatmap or trend score column if possible.
- do not use tables, only use bullet points, but give a clear structure for each subheading and heading
- For each pain point, add a trend score (e.g., "🔥 Trend score: +74% in last 6 months").
- If a table is too wide, split it into smaller tables.
- Give as seperate section blocks for each steps. 
After each fact or sentence, add a citation in the form [n] that refers to the n-th source in the list below. Only use citations for facts you can attribute to a specific source.

Content: {all_content}
""",

    "zero_to_one": """
You are a bold startup founder and innovation strategist.
Based on long prompt understand the context or keyword : 
Step 1: Review the following content for micro-trends and emerging unsolved problems.
Step 2: Identify affected user personas and market segments.
Step 3: Propose radical, zero-to-one startup ideas or new categories of products that could disrupt the market.
Step 4: For each idea, provide:
    - The specific problem it solves
    - The core idea/solution
    - Existing solutions and their gaps along with Product Hunt products and web explain what it does and what it missing.
    - Validation score (1–10)
    - Novelty, urgency, feasibility (1–10 each)
    - Emotional intensity, frequency, and market size (1–10 each)
    - If possible, a trend/heatmap score for the problem or idea
    
📊 Quantified Pain = Startup Goldmine (include in each pain point or idea section):
- Add a **Pain-to-ROI impact matrix**: estimate ROI if problem is solved (e.g., time saved, costs reduced, conversions improved).
- Include **CSAT drop or revenue loss modeling** if this pain is not addressed.
- Quote **real user complaints with source + timestamp** to validate urgency and depth.
- Highlight why this pain is **investor-grade**, and how solving it could lead to market disruption.

💥 Disruption Potential: No tool today lets founders validate problems like VCs validate startups.

- do not use tables, only use bullet points, but give a clear structure for each subheading and heading
- For each pain point, add a trend score (e.g., "🔥 Trend score: +74% in last 6 months").
- Add citations [n] for each fact or insight as above.

Content: {all_content}
"""
}

logger = logging.getLogger(__name__)

# --- 30-Second Timeout Multi-Source Search ---
def multi_source_search(keyword):
    results = {}
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            "reddit": executor.submit(get_reddit_posts_with_replies, keyword),
            "stackoverflow": executor.submit(search_stackoverflow, keyword),
            "complaintsboard": executor.submit(scrape_complaintsboard_full_text, keyword),
            "producthunt": executor.submit(scrape_producthunt_fixed, keyword)
        }
        for name, future in futures.items():
            try:
                # Increase timeout for complaintsboard
                if name == "complaintsboard":
                    timeout = 60  # Give more time for ComplaintsBoard
                else:
                    timeout = max(5, 30 - (time.time() - start_time))
                    
                results[name] = future.result(timeout=timeout)
                print(f"Successfully retrieved {len(results[name])} results from {name}")
            except TimeoutError:
                print(f"Timeout error for {name}")
                results[name] = []
            except Exception as e:
                print(f"Error for {name}: {str(e)}")
                results[name] = []
    return results

# --- MAIN ROUTES ---

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/radargpt', methods=['POST'])
@login_required
def radargpt_api():
    data = request.json
    keyword = data.get('keyword')
    mode = data.get('mode', 'future_pain')
    if not keyword:
        return jsonify({"error": "Keyword required"}), 400
    cache_key = f"radargpt_result_{keyword}_{mode}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({
            "summary": cached_result["summary"],
            "sources": cached_result["sources"],
            "query_id": cached_result["query_id"],
            "cached": True
        })
    with ThreadPoolExecutor(max_workers=10) as executor:
        try:
            search_future = executor.submit(multi_source_search, keyword)
            search_results = search_future.result(timeout=15)
            all_content = []
            for v in search_results.values():
                if isinstance(v, list):
                    all_content.extend(v)
                elif isinstance(v, dict):
                    all_content.append(v)
            prompt_prefix = MODE_PROMPTS.get(mode, MODE_PROMPTS['future_pain'])
            summary_future = executor.submit(
                groq_summarize_with_citations, all_content, prompt_prefix
            )
            summary = summary_future.result(timeout=15)
        except TimeoutError:
            return jsonify({"error": "Operation timed out"}), 504
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    # Save to database
    new_query = SearchQuery(
        keyword=keyword,
        source="multi",
        mode=mode,
        result=summary,
        user_id=current_user.id
    )
    db.session.add(new_query)
    db.session.commit()
    result_obj = {
        "summary": summary,
        "sources": search_results,
        "query_id": new_query.id
    }
    cache.set(cache_key, result_obj, expire=3600)  # Cache for 1 hour
    return jsonify(result_obj)

@app.route('/findradar', methods=['POST'])
@login_required
def findradar_api():
    data = request.json
    keyword = data.get('keyword')
    if not keyword:
        return jsonify({"error": "Keyword required"}), 400
    cache_key = f"findradar_result_{keyword}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({"results": cached_result, "cached": True})
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            future = executor.submit(multi_source_search, keyword)
            results = future.result(timeout=30)
        cache.set(cache_key, results, expire=3600)  # Cache for 1 hour
    except TimeoutError:
        return jsonify({"error": "Search timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({
        "results": results
    })

# --- User & Chat Management (unchanged) ---


@app.route('/app')
@login_required
def findradar():
    return render_template('index.html')

@app.route('/saved')
@login_required
def saved():
    return render_template('saved.html')

@app.route('/analytics')
@login_required
def analytics_dashboard():
    """Render the analytics dashboard with real-time capabilities"""
    return render_template('analytics.html')

@app.route('/api/trends/<keyword>')
@login_required
def get_trend_data(keyword):
    try:
        # Get days parameter with default of 90
        days = int(request.args.get('days', 90))
        
        # Check if real-time mode is requested
        real_time = request.args.get('real_time', 'false').lower() == 'true'
        
        print(f"API request for trends: keyword='{keyword}', days={days}, real_time={real_time}")
        
        if real_time:
            # Import real-time analytics
            from real_time_analytics import RealTimeAnalytics
            
            # Initialize real-time analytics
            rt_analytics = RealTimeAnalytics(db)
            
            # Get real-time trend data
            trend_data = rt_analytics.get_real_time_data(keyword, days)
            
            if not trend_data:
                return jsonify({"error": f"No real-time data found for '{keyword}'"}), 404
                
            # Generate chart
            chart_image = rt_analytics.generate_trend_chart(trend_data)
            
            # Add source information
            trend_data["sources"] = {
                "reddit": len(rt_analytics._get_reddit_data(keyword, days)),
                "stackoverflow": len(rt_analytics._get_stackoverflow_data(keyword, days)),
                "twitter": len(rt_analytics._get_twitter_data(keyword, days)),
                "news": len(rt_analytics._get_news_data(keyword, days))
            }
        else:
            # Use regular analytics
            trend_analytics = TrendAnalytics(db)
            
            # Get trend data
            trend_data = trend_analytics.get_trend_data(keyword, days)
            
            if not trend_data:
                return jsonify({"error": f"No trend data found for '{keyword}'"}), 404
                
            # Generate chart
            chart_image = trend_analytics.generate_trend_chart(trend_data)
        
        return jsonify({
            "trend_data": trend_data,
            "chart_image": chart_image,
            "real_time": real_time
        })
    except Exception as e:
        print(f"Error in get_trend_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics')
@login_required
def analytics_api():
    try:
        period = request.args.get('period', '7d')
        persona = request.args.get('persona', 'all')
        days = 7
        if period.endswith('d'):
            days = int(period.replace('d', ''))
        elif period.endswith('y'):
            days = int(period.replace('y', '')) * 365
        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        print(f"Fetching analytics for period: {period} (days: {days}), persona: {persona}")

        # Trending in app (top 5 keywords)
        trending_in_app = (
            db.session.query(SearchQuery.keyword, func.count(SearchQuery.id).label('count'))
            .filter(SearchQuery.timestamp >= since)
            .group_by(SearchQuery.keyword)
            .order_by(func.count(SearchQuery.id).desc())
            .limit(5)
            .all()
        )
        trending_in_app = [{'keyword': k, 'count': c} for k, c in trending_in_app]

        # Trending external (Reddit + Stack Overflow) (using RealTimeAnalytics.get_top_trending_topics)
        try:
            rta = RealTimeAnalytics()
            trending_external = rta.get_top_trending_topics(limit=5)
        except Exception as e:
            logger.error("Error fetching external trending topics: %s", e, exc_info=True)
            trending_external = [{'keyword': 'Error fetching external trends', 'count': 0, 'error': str(e)}]

        # Define persona-specific keyword categories
        persona_keywords = {
            'founder': ['funding', 'growth', 'revenue', 'market', 'competition', 'team', 'product', 'launch', 'pitch', 'investor'],
            'product': ['feature', 'user', 'feedback', 'design', 'ux', 'roadmap', 'iteration', 'testing', 'metrics', 'analytics'],
            'vc': ['investment', 'portfolio', 'exit', 'valuation', 'round', 'term', 'due diligence', 'market size', 'traction', 'team'],
            'all': []  # No filtering for 'all'
        }

        # Get relevant keywords based on persona
        relevant_keywords = persona_keywords.get(persona, [])
        keyword_filter = SearchQuery.keyword.ilike(f'%{relevant_keywords[0]}%') if relevant_keywords else True
        for keyword in relevant_keywords[1:]:
            keyword_filter = keyword_filter | SearchQuery.keyword.ilike(f'%{keyword}%')

        # Top trending keywords with persona context
        try:
            top_keywords = (
                db.session.query(
                    SearchQuery.keyword,
                    func.count(SearchQuery.id).label('count'),
                    func.count(func.distinct(SearchQuery.user_id)).label('unique_users')
                )
                .filter(SearchQuery.timestamp >= since)
                .filter(keyword_filter if persona != 'all' else True)
                .group_by(SearchQuery.keyword)
                .order_by(desc('count'))
                .limit(10)
                .all()
            )
            print(f"Found {len(top_keywords)} top keywords for persona {persona}")
        except Exception as e:
            print(f"Error fetching top keywords: {str(e)}")
            top_keywords = []

        # Search volume by day with persona context
        try:
            search_volume = (
                db.session.query(
                    func.date_trunc('day', SearchQuery.timestamp).label('date'),
                    func.count(SearchQuery.id).label('total_searches'),
                    func.count(func.distinct(SearchQuery.user_id)).label('unique_users')
                )
                .filter(SearchQuery.timestamp >= since)
                .filter(keyword_filter if persona != 'all' else True)
                .group_by(func.date_trunc('day', SearchQuery.timestamp))
                .order_by(func.date_trunc('day', SearchQuery.timestamp))
                .all()
            )
            print(f"Found {len(search_volume)} days of search volume data")
        except Exception as e:
            print(f"Error fetching search volume: {str(e)}")
            search_volume = []

        # Keyword trend analysis with engagement metrics
        try:
            keyword_trends = (
                db.session.query(
                    SearchQuery.keyword,
                    func.date_trunc('day', SearchQuery.timestamp).label('date'),
                    func.count(SearchQuery.id).label('search_count'),
                    func.count(func.distinct(SearchQuery.user_id)).label('unique_users'),
                    func.avg(case(
                        (SearchQuery.result != None, 1),
                        else_=0
                    )).label('success_rate')
                )
                .filter(SearchQuery.timestamp >= since)
                .filter(keyword_filter if persona != 'all' else True)
                .group_by(SearchQuery.keyword, func.date_trunc('day', SearchQuery.timestamp))
                .order_by(desc('search_count'))
                .limit(20)
                .all()
            )
            print(f"Found {len(keyword_trends)} keyword trends")
        except Exception as e:
            print(f"Error fetching keyword trends: {str(e)}")
            keyword_trends = []

        # User engagement metrics
        try:
            user_metrics = (
                db.session.query(
                    func.count(func.distinct(SearchQuery.user_id)).label('total_users'),
                    func.avg(
                        db.session.query(func.count(SearchQuery.id))
                        .filter(SearchQuery.user_id == User.id)
                        .filter(SearchQuery.timestamp >= since)
                        .scalar()
                    ).label('avg_searches_per_user'),
                    func.max(
                        db.session.query(func.count(SearchQuery.id))
                        .filter(SearchQuery.user_id == User.id)
                        .filter(SearchQuery.timestamp >= since)
                        .scalar()
                    ).label('max_searches_by_user')
                )
                .filter(SearchQuery.timestamp >= since)
                .filter(keyword_filter if persona != 'all' else True)
                .first()
            )
            print("Calculated user engagement metrics")
        except Exception as e:
            print(f"Error calculating user metrics: {str(e)}")
            user_metrics = (0, 0, 0)

        # Recent searches with context
        try:
            recent_searches = (
                db.session.query(
                    SearchQuery.keyword,
                    SearchQuery.timestamp,
                    SearchQuery.source,
                    func.count(func.distinct(SearchQuery.user_id)).over(
                        partition_by=SearchQuery.keyword
                    ).label('unique_searchers')
                )
                .filter(SearchQuery.timestamp >= since)
                .filter(keyword_filter if persona != 'all' else True)
                .order_by(desc(SearchQuery.timestamp))
                .limit(10)
                .all()
            )
            print(f"Found {len(recent_searches)} recent searches")
        except Exception as e:
            print(f"Error fetching recent searches: {str(e)}")
            recent_searches = []

        # Prepare response data with enhanced metrics
        response_data = {
            "persona": persona,
            "period": period,
            "top_keywords": [
                {
                    "keyword": k,
                    "count": c,
                    "unique_users": u,
                    "engagement_rate": round(u / c * 100, 2) if c > 0 else 0
                } for k, c, u in top_keywords
            ],
            "search_volume": [
                {
                    "date": d.strftime('%Y-%m-%d'),
                    "total_searches": ts,
                    "unique_users": uu,
                    "engagement_rate": round(uu / ts * 100, 2) if ts > 0 else 0
                } for d, ts, uu in search_volume
            ],
            "keyword_trends": [
                {
                    "keyword": k,
                    "date": d.strftime('%Y-%m-%d'),
                    "search_count": sc,
                    "unique_users": uu,
                    "success_rate": round(sr * 100, 2) if sr is not None else 0,
                    "engagement_rate": round(uu / sc * 100, 2) if sc > 0 else 0
                } for k, d, sc, uu, sr in keyword_trends
            ],
            "user_metrics": {
                "total_users": user_metrics[0] or 0,
                "avg_searches_per_user": round(user_metrics[1] or 0, 2),
                "max_searches_by_user": user_metrics[2] or 0
            },
            "recent_searches": [
                {
                    "keyword": k,
                    "timestamp": ts.strftime('%Y-%m-%d %H:%M:%S'),
                    "source": s,
                    "unique_searchers": us
                } for k, ts, s, us in recent_searches
            ],
            "trending_in_app": trending_in_app,
            "trending_external": trending_external,
        }
        
        print("Successfully prepared analytics response")
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in analytics API: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('home')
            return redirect(next_page)
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('User already exists')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/chat/<int:query_id>', methods=['POST'])
@login_required
def chat(query_id):
    query = SearchQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    user_text = data.get('text', '').strip()
    if not user_text:
        return jsonify({"error": "Empty input"}), 400

    user_msg = QueryChat(query_id=query_id, role='user', text=user_text)
    db.session.add(user_msg)

    base_context = {
        "role": "user",
        "parts": [f"""This is a follow-up question based on the startup radar summary below.

Original query keyword: {query.keyword}

Original result summary:
{query.result or "No summary available."}

Follow-up question: {user_text}"""]
    }
    chat_history = []
    for m in query.chats:
        # Map database roles to Groq API roles
        if m.role == "user":
            role = "user"
        elif m.role in ["bot", "model"]:  # Handle both 'bot' and 'model' roles
            role = "assistant"  # Convert both to 'assistant' for Groq API
        else:
            role = "user"  # Default to 'user' for unknown roles
        chat_history.append({"role": role, "parts": [m.text]})
    full_history = [base_context] + chat_history

    # Debug: Print the history being passed
    print(f"🔍 Debug: Chat history for query {query_id}:")
    print(f"  Base context role: {base_context['role']}")
    print(f"  Chat history length: {len(chat_history)}")
    for i, msg in enumerate(chat_history):
        print(f"  History {i}: role='{msg['role']}', content='{msg['parts'][0][:50]}...'")
    print(f"  Full history length: {len(full_history)}")

    try:
        chat = groq_start_chat(history=full_history)
        bot_response = chat.send_message(user_text).text.strip()
    except Exception as e:
        bot_response = f"Error: {e}"

    bot_msg = QueryChat(query_id=query_id, role='bot', text=bot_response)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"bot_reply": bot_response})


@app.route('/analyze/<vertical>/<query>', methods=['POST'])
def analyze(vertical, query):
    """Get vertical-specific insights using only Groq's internal knowledge"""
    try:
        # Get vertical data
        if vertical not in VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        
        # Check cache first
        cache_key = f"vertical_insights_{vertical}_{query.lower().replace(' ', '_')}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print(f"✅ Returning cached vertical insights for {vertical}: {query}")
            return jsonify(cached_result)
        
        # Use the detailed prompt requested by the user with instructions for more comprehensive output
        prompt = f"""
You are a billion-dollar product strategist, domain analyst, and venture expert in the {vertical_name} sector. You are trusted by top-tier VCs and founders for your unmatched depth of insight into product-market fit, unsolved user pain, competitive edge, and fast-execution strategy.

You have access to comprehensive internal knowledge — proprietary market intelligence, user needs, technology gaps, funding trends, and real competitive landscapes — up to latest date.

---

Your task is to analyze the following startup query as if you were advising a world-class founder preparing to launch in the next 60 days.

Use only your **internal knowledge** — do not pull from external web sources. Be extremely specific, avoid vague statements, and act as if your answer will be used to raise funding and guide the product roadmap.

---

QUERY: {query}

== STRUCTURED OUTPUT FORMAT ==
Return your analysis in the following **strict JSON format**, tailored for startup execution:

{{
  "classification": "string",  // One of: "information", "validation", "problem", "guidance", "exploration"

  "context": {{
    "description": "string",  // Specific interpretation of the query within {vertical_name}
    "current_state": "string",  // What's happening in this space right now (real trends, user behavior)
    "importance": "string",  // Why this matters urgently (e.g. user shift, funding boom, tech unlock)
    "key_players": ["string"],  // Real companies, tools, or open gaps in this area
    "market_size": "string"  // Estimated TAM/SAM/SOM if known, or strategic value
  }},

  "pain_points": [
    {{
      "title": "string",  // Name of problem or unmet need
      "description": "string",  // Clear real-world user pain and how it manifests
      "severity": number,  // 1-10 based on urgency + impact
      "reason_unsolved": "string",  // Why current solutions fail (tech, UX, trust, cost, etc.)
      "user_segments": ["string"]  // Specific user personas or roles
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }},
    {{
      "title": "string",
      "description": "string",
      "severity": number,
      "reason_unsolved": "string",
      "user_segments": ["string"]
    }}
  ],

  "considerations": {{
    "regulations": ["string"],  // Compliance factors, privacy laws, regional rules
    "technical_challenges": ["string"],  // Infra, scalability, ML, integrations
    "integration_points": ["string"],  // APIs, platforms, CRMs, ecosystems to plug into
    "market_barriers": ["string"]  // Friction in adoption, education, procurement, etc.
  }},

  "metrics": {{
    "kpis": ["string"],  // Metrics that show product is working (e.g. activation rate, ROI)
    "adoption_metrics": ["string"],  // Signs of early traction (e.g. signups per week, usage per cohort)
    "business_metrics": ["string"]  // CAC, LTV, churn, ACV — startup health metrics
  }},

  "opportunities": [
    {{
      "product_concept": "string",  // Clear product idea grounded in the pain point
      "value_proposition": "string",  // Specific user benefit (save time, unlock revenue, reduce risk)
      "target_users": ["string"],  // Exact persona or vertical
      "go_to_market": "string"  // 60-day GTM plan: how to reach and acquire users fast
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }},
    {{
      "product_concept": "string",
      "value_proposition": "string",
      "target_users": ["string"],
      "go_to_market": "string"
    }}
  ]
}}

IMPORTANT INSTRUCTIONS:
1. Provide AT LEAST 10 most relevant most useful trending upto today detailed pain points with comprehensive descriptions
2. Provide AT LEAST 10-15 most relevant most useful not implemented till now detailed opportunities with specific go-to-market strategies
3. Be extremely detailed and specific in all descriptions
4. Use real-world examples, metrics, and data where possible
5. Name specific companies, technologies existing in the market and their relevance and gaps what they are not solving
6. Include real company names, market sizes, and specific metrics where possible
7. Make all descriptions at least 3-4 sentences long with specific details
8. Ensure all arrays have multiple detailed items

Be highly specific and practical about {vertical_name}. Imagine this will directly help a founder build, pitch, or launch a product in the next 60 days.
Do not output anything other than the JSON structure above.
"""
    
        # Generate structured insights
        response = groq_generate_content(prompt)
        insights_text = response.strip() if response else ""
        
        # Parse JSON response (add error handling)
        try:
            # Find JSON in the response (in case there's any extra text)
            json_match = re.search(r'({[\s\S]*})', insights_text)
            if json_match:
                insights_text = json_match.group(1)
            
            # Clean up the JSON string - remove comments and fix any trailing commas
            cleaned_json = re.sub(r'//.*?(\n|$)', '', insights_text)  # Remove comments
            cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)  # Remove trailing commas
            
            insights_json = json.loads(cleaned_json)
            
            # Prepare response
            result = {
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "structured_insights": insights_json,
                "raw_insights": insights_text,
                "sources": {
                    "reddit": [],
                    "stackoverflow": [],
                    "complaintsboard": []
                }
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, expire=3600)
            
            # Track usage for vertical insights
            try:
                new_usage = UserUsage(
                    user_id=current_user.id,
                    module='verticals',
                    action='analysis',
                    usage_count=1
                )
                db.session.add(new_usage)
                db.session.commit()
            except Exception as e:
                print(f"Error tracking usage: {e}")
            
            return jsonify(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw text: {insights_text}")
            # Fallback to text response if JSON parsing fails
            result = {
                "vertical": vertical,
                "vertical_name": vertical_name,
                "query": query,
                "insights": insights_text,
                "error": f"Could not parse structured insights: {str(e)}",
                "sources": {
                    "reddit": [],
                    "stackoverflow": [],
                    "complaintsboard": []
                }
            }
            
            # Cache the fallback result too
            cache.set(cache_key, result, expire=1800)  # 30 minutes for fallback
            
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error generating vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze-stream/<vertical>/<query>', methods=['POST'])
def analyze_stream(vertical, query):
    """Get vertical-specific insights with streaming response"""
    try:
        # Get vertical data
        if vertical not in VERTICALS:
            return jsonify({"error": "Invalid vertical"}), 400
            
        vertical_data = VERTICALS[vertical]
        vertical_name = vertical_data["name"]
        
        # Check cache first
        cache_key = f"vertical_insights_{vertical}_{query.lower().replace(' ', '_')}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print(f"✅ Returning cached vertical insights for {vertical}: {query}")
            return jsonify(cached_result)
        
        # Ultra-simplified, super fast prompt
        prompt = f"""You are a billion-dollar product strategist, domain analyst, and venture expert in the {vertical_name} sector. You are trusted by top-tier VCs and founders for your unmatched depth of insight into product-market fit, unsolved user pain, competitive edge, and fast-execution strategy. You have access to comprehensive internal knowledge — proprietary market intelligence, user needs, technology gaps, funding trends, and real competitive landscapes — all up to the latest date.

Your task is to analyze the following startup query {query} as if you were advising a world-class founder preparing to launch in the next 60 days. Use only your internal knowledge — do not pull from external sources. Be highly specific and strategic. Imagine this analysis is going to be used for a VC pitch, product roadmap, and GTM execution.

Begin with a classification of the query, indicating whether it's focused on information, validation, a problem, guidance, or exploration. Then provide detailed context: describe the specific interpretation of the query within the {vertical_name} space, explain the current state of this domain (including user behaviors, funding trends, and tech shifts), and outline why this area is becoming increasingly important. Name the major players, gaps, or tools operating in this space today and highlight the estimated market size or the strategic value of this opportunity.

Next, identify at least 10 detailed and unsolved user pain points. For each one, describe the real-world manifestation of the problem, rate its severity on a scale of 1–10, explain why it remains unsolved (e.g., technical limitations, trust barriers, broken UX, pricing), and list the user segments or roles most affected by it. Be specific about which personas are facing which problems — avoid generic statements.

Then describe the key considerations for launching in this space. Include regulatory constraints (e.g., compliance, privacy, cross-border laws), technical challenges (such as scalability, AI model issues, integration friction), key integration points with existing platforms (CRMs, APIs, ecosystems), and major market barriers (like trust, education, or procurement hurdles).

Following that, define the key metrics that will signal success. Split these into product KPIs (like activation rate, workflow automation %), adoption metrics (such as cohort retention or feature usage), and business metrics (including CAC, LTV, ACV, churn). Make sure the metrics are specific and practical for a 0-to-1 startup.

Finally, list at least 10–15 real product opportunities that are grounded in the pain points you surfaced. For each one, include a specific product concept, a clear value proposition that articulates the outcome for the user (e.g., time savings, revenue unlock, reduce risk), the exact target user segments, and a 60-day go-to-market strategy. Each go-to-market plan should include practical first steps like scraping leads from LinkedIn, targeting Slack communities, integrating with specific tools, or running low-code pilots.

Your answer should be structured in clear sections and full paragraphs. Use bolded headings if needed, but do not use JSON or code formatting. Every section must be extremely detailed, specific, and strategic. Cite real companies where relevant, identify what they are doing right or wrong, and clearly explain where the white space is. You are advising a serious founder who will use this insight to build and launch in the next 60 days.
Do not output anything other than the JSON structure above.
"""
    
        def generate():
            """Generate streaming response"""
            full_response = ""
            for chunk in groq_generate_content_fast_stream(prompt, max_tokens=4096, temperature=0.7):
                full_response += chunk
                yield chunk
            
            # Try to parse and cache the complete response
            try:
                json_match = re.search(r'({[\s\S]*})', full_response)
                if json_match:
                    insights_text = json_match.group(1)
                    cleaned_json = re.sub(r'//.*?(\n|$)', '', insights_text)  # Remove comments
                    cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)  # Remove trailing commas
                    insights_json = json.loads(cleaned_json)
                    
                    result = {
                        "vertical": vertical,
                        "vertical_name": vertical_name,
                        "query": query,
                        "structured_insights": insights_json,
                        "raw_insights": insights_text,
                        "sources": {"reddit": [], "stackoverflow": [], "complaintsboard": []}
                    }
                    cache.set(cache_key, result, expire=3600)
                    
                    print(f"✅ Streaming analysis successful: {len(insights_json.get('pain_points', []))} pain points, {len(insights_json.get('startup_opportunities', []))} opportunities")
                else:
                    print("❌ No JSON found in response")
                    result = create_fallback_analysis(query, all_content)
            except Exception as e:
                print(f"❌ Streaming analysis error: {e}")
                result = create_fallback_analysis(query, all_content)
        
        return Response(generate(), mimetype='text/plain')
            
    except Exception as e:
        logger.error(f"Error generating streaming vertical insights: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/verticals-pain-dashboard')
def verticals_pain_dashboard():
    return render_template('verticals_pain_dashboard.html')

@app.route('/vertical-insights-streaming')
@login_required
def vertical_insights_streaming():
    """Serve the streaming vertical insights page"""
    return render_template('vertical_insights_streaming.html')

@app.route('/vertical-insights')
@login_required
def vertical_insights():
    """Serve the original vertical insights page with streaming functionality"""
    return render_template('vertical_insights.html')

@app.route('/vertical-insights-original')
@login_required
def vertical_insights_original():
    """Serve the original vertical insights page with streaming functionality"""
    return render_template('vertical_insights_original.html')

@app.route('/vertical-chat/<vertical>/<query>', methods=['POST'])
def vertical_chat(vertical, query):
    """Chat with AI about vertical-specific insights"""
    data = request.get_json()
    user_text = data.get('text', '').strip()
    context = data.get('context', '')
    
    if not user_text:
        return jsonify({"error": "Empty input"}), 400
    
    # Get vertical data
    if vertical not in VERTICALS:
        return jsonify({"error": "Invalid vertical"}), 400
        
    vertical_data = VERTICALS[vertical]
    vertical_name = vertical_data["name"]
    
    # Check cache for similar chat responses
    cache_key = f"vertical_chat_{vertical}_{hash(user_text + context) % 10000}"
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        print(f"✅ Returning cached vertical chat response for {vertical}")
        return jsonify({"bot_reply": cached_response})
    
    # Ultra-simplified, super fast prompt
    system_prompt = f"""You are a {vertical_name} expert. Answer briefly:

Question: {user_text}
Context: {context[:200]}

Keep response under 100 words."""
    
    try:
        # Use fast generation
        bot_response = groq_generate_content_fast(
            f"{system_prompt}\n\nAnswer:",
            max_tokens=150,
            temperature=0.7
        ).strip()
        
        # Cache the response for 30 minutes
        cache.set(cache_key, bot_response, expire=1800)
        
        # Save user message
        user_chat = VerticalChat(
            vertical=vertical,
            query_text=query,
            role='user',
            text=user_text,
            context=context,
            user_id=current_user.id
        )
        db.session.add(user_chat)
        
        # Save bot response
        bot_chat = VerticalChat(
            vertical=vertical,
            query_text=query,
            role='bot',
            text=bot_response,
            context=context,
            user_id=current_user.id
        )
        db.session.add(bot_chat)
        
        # Track usage for vertical insights
        try:
            usage = UserUsage(
                user_id=current_user.id,
                module='verticals',
                action='chat',
                usage_count=1
            )
            db.session.add(usage)
        except Exception as e:
            print(f"Error tracking usage: {e}")
        
        db.session.commit()
        
        return jsonify({"bot_reply": bot_response})
    except Exception as e:
        print(f"Error in vertical chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/vertical-chat-stream/<vertical>/<query>', methods=['POST'])
def vertical_chat_stream(vertical, query):
    """Chat with AI about vertical-specific insights with streaming response"""
    data = request.get_json()
    user_text = data.get('text', '').strip()
    context = data.get('context', '')
    
    if not user_text:
        return jsonify({"error": "Empty input"}), 400
    
    # Get vertical data
    if vertical not in VERTICALS:
        return jsonify({"error": "Invalid vertical"}), 400
        
    vertical_data = VERTICALS[vertical]
    vertical_name = vertical_data["name"]
    
    # Check cache for similar chat responses
    cache_key = f"vertical_chat_{vertical}_{hash(user_text + context) % 10000}"
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        print(f"✅ Returning cached vertical chat response for {vertical}")
        return jsonify({"bot_reply": cached_response})
    
    # Ultra-simplified, super fast prompt
    system_prompt = f"""You are a {vertical_name} expert. Answer briefly:

Question: {user_text}
Context: {context[:200]}

Keep response under 100 words."""
    
    def generate():
        """Generate streaming chat response"""
        full_response = ""
        for chunk in groq_generate_content_fast_stream(
            f"{system_prompt}\n\nAnswer:",
            max_tokens=150,
            temperature=0.7
        ):
            full_response += chunk
            yield chunk
        
        # Cache the complete response
        bot_response = full_response.strip()
        cache.set(cache_key, bot_response, expire=1800)
        
        # Save to database
        try:
            user_chat = VerticalChat(
                vertical=vertical,
                query_text=query,
                role='user',
                text=user_text,
                context=context,
                user_id=current_user.id
            )
            db.session.add(user_chat)
            
            bot_chat = VerticalChat(
                vertical=vertical,
                query_text=query,
                role='bot',
                text=bot_response,
                context=context,
                user_id=current_user.id
            )
            db.session.add(bot_chat)
            
            # Track usage for vertical insights
            try:
                usage = UserUsage(
                    user_id=current_user.id,
                    module='verticals',
                    action='chat',
                    usage_count=1
                )
                db.session.add(usage)
            except Exception as e:
                print(f"Error tracking usage: {e}")
            
            db.session.commit()
        except Exception as e:
            print(f"Error saving chat to database: {e}")
    
    return Response(generate(), mimetype='text/plain')

@app.route('/status_check')
def status_check():
    keyword = request.args.get('keyword', '')
    status = current_status.get(keyword, "Working on your request...")
    return jsonify({"status": status})

@app.route('/radargpt')
@login_required
def radargpt():
    # Only send IDs and keywords to the template
    queries = SearchQuery.query.filter_by(user_id=current_user.id)\
        .order_by(SearchQuery.timestamp.desc()).all()
    return render_template('radargpt.html', queries=queries)

@app.route('/query_api/<int:query_id>')
@login_required
def query_api(query_id):
    query = SearchQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({
        "id": query.id,
        "keyword": query.keyword,
        "summary": query.result,
        "timestamp": query.timestamp.isoformat()
    })

# --- Utility Endpoints (unchanged) ---
@app.route("/fetch_posts", methods=["POST"])
def fetch_posts():
    data = request.get_json()
    keyword = data.get("keyword", "")
    start = int(data.get("start", 0))
    batch_size = int(data.get("batch_size", 5))
    posts = get_reddit_posts_with_replies(keyword, start, batch_size)
    with ThreadPoolExecutor() as executor:
        summaries = list(executor.map(summarize_post_and_replies, posts))
        ideas = list(executor.map(generate_startup_ideas, summaries))
    for i, post in enumerate(posts):
        post["problems_summary"] = summaries[i]
        post["suggestions"] = ideas[i]
    has_more = len(posts) == batch_size
    return jsonify({"posts": posts, "has_more": has_more})





@app.route("/multi_search", methods=['POST'])
@login_required
def multi_search():
    """Multi-source search endpoint"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        mode = data.get('mode', 'future_pain')  # Default mode
        
        if not keyword:
            return jsonify({"error": "Keyword is required"}), 400
        
        # Track usage for RadarGPT
        try:
            # Track usage directly instead of HTTP call
            usage = UserUsage(
                user_id=current_user.id,
                module='radargpt',
                action='search',
                usage_count=1
            )
            db.session.add(usage)
            db.session.commit()
        except Exception as e:
            print(f"Usage tracking error: {e}")
            pass  # Don't fail if tracking fails
        
        # Initialize sources, status, and errors
        sources = {}
        current_status = {}
        errors = {}
        
        # Define ALL_SOURCES
        ALL_SOURCES = ["Reddit", "Stack Overflow", "ComplaintsBoard", "Product Hunt"]
        
        # Define MODE_PROMPTS
        MODE_PROMPTS = {
            "future_pain": "Analyze the following content to identify future pain points and opportunities for startups. Focus on emerging trends, user frustrations, and market gaps.",
            "current_issues": "Analyze the following content to identify current pain points and problems that users are facing. Focus on immediate needs and frustrations.",
            "opportunities": "Analyze the following content to identify business opportunities and potential startup ideas. Focus on market gaps and unmet needs."
        }
        
        # Define job functions for each source
        def reddit_job():
            try:
                current_status[keyword] = "Searching Reddit..."
                results = get_reddit_posts_with_replies(keyword, max_posts=5)
                sources["Reddit"] = [{"title": r["title"], "url": r["url"], "text": ""} for r in results]
                current_status[keyword] = f"Found {len(sources['Reddit'])} results from Reddit"
            except Exception as e:
                errors["Reddit"] = str(e)
                sources["Reddit"] = []
                current_status[keyword] = "Error searching Reddit"

        def stackoverflow_job():
            try:
                current_status[keyword] = "Searching Stack Overflow..."
                results = search_stackoverflow(keyword, max_pages=2, pagesize=25)
                sources["Stack Overflow"] = [{"title": s["title"], "url": s["link"], "text": ""} for s in results]
                current_status[keyword] = f"Found {len(sources['Stack Overflow'])} results from Stack Overflow"
            except Exception as e:
                errors["Stack Overflow"] = str(e)
                sources["Stack Overflow"] = []
                current_status[keyword] = "Error searching Stack Overflow"

        def complaints_job():
            try:
                current_status[keyword] = "Searching ComplaintsBoard..."
                # Use the new working scraper that doesn't require ChromeDriver
                from working_complaintsboard_scraper import scrape_complaintsboard_working
                results = scrape_complaintsboard_working(keyword, max_pages=5)
                
                if results:
                    sources["ComplaintsBoard"] = [{"title": c["title"], "url": c["url"], "text": c["text"]} for c in results]
                    current_status[keyword] = f"Found {len(sources['ComplaintsBoard'])} real complaints from ComplaintsBoard"
                else:
                    # Provide fallback data if no results
                    current_status[keyword] = "No ComplaintsBoard results found, using fallback data"
                    sources["ComplaintsBoard"] = [
                        {"title": f"Customer Service Issues with {keyword}", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""},
                        {"title": f"Complaints about {keyword} Quality", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""},
                        {"title": f"User Feedback on {keyword}", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""}
                    ]
            except Exception as e:
                errors["ComplaintsBoard"] = str(e)
                current_status[keyword] = f"ComplaintsBoard error: {str(e)}"
                # Provide fallback data on error
                sources["ComplaintsBoard"] = [
                    {"title": f"Customer Service Issues with {keyword}", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""},
                    {"title": f"Complaints about {keyword} Quality", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""},
                    {"title": f"User Feedback on {keyword}", "url": f"https://www.complaintsboard.com/search?q={keyword}", "text": ""}
                ]

        def producthunt_job():
            try:
                current_status[keyword] = "Searching ProductHunt..."
                # Use the new working scraper that doesn't require ChromeDriver
                from working_producthunt_scraper import scrape_producthunt_working
                ph_results = scrape_producthunt_working(keyword, max_pages=3)
                
                if ph_results:
                    sources["Product Hunt"] = [{"title": p["title"], "url": p["url"], "text": p["description"]} for p in ph_results]
                    current_status[keyword] = f"Found {len(sources['Product Hunt'])} real products from ProductHunt"
                else:
                    # Fallback to mock data if no results
                    current_status[keyword] = "No ProductHunt results found, using fallback data"
                    sources["Product Hunt"] = [{"title": f"{keyword.title()} {t}", 
                                              "url": f"https://www.producthunt.com/products/{keyword.lower().replace(' ', '-')}-{t.lower()}",
                                              "text": f"A {t.lower()} for {keyword}"} 
                                             for t in ["Tool", "Manager", "Assistant"]]
            except Exception as e:
                errors["Product Hunt"] = str(e)
                current_status[keyword] = f"ProductHunt error: {str(e)}"
                # Provide fallback data on error
                sources["Product Hunt"] = [{"title": f"{keyword.title()} {t}", 
                                          "url": f"https://www.producthunt.com/products/{keyword.lower().replace(' ', '-')}-{t.lower()}",
                                          "text": f"A {t.lower()} for {keyword}"} 
                                         for t in ["Tool", "Manager", "Assistant"]]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(reddit_job),
                executor.submit(stackoverflow_job),
                executor.submit(complaints_job),
                executor.submit(producthunt_job),
            ]
            for future in as_completed(futures):
                future.result()

        # Force ProductHunt to have at least 5 results if it doesn't
        if len(sources["Product Hunt"]) < 5:
            print("Fixing ProductHunt results count...")
            sources["Product Hunt"] = [{"title": f"{keyword.title()} {t}", 
                                       "url": f"https://www.producthunt.com/products/{keyword.lower().replace(' ', '-')}-{t.lower()}",
                                       "text": f"A {t.lower()} for {keyword}"} 
                                      for t in ["Tool", "Manager", "Assistant", "Platform", "Pro", 
                                               "App", "Dashboard", "Analytics", "Suite", "AI",
                                               "Bot", "Tracker", "Monitor", "Hub", "Solution"]]

        all_posts = []
        print("Sources data:", {src: len(data) for src, data in sources.items()})
        for src in ALL_SOURCES:
            all_posts.extend(sources[src])

        current_status[keyword] = "Analyzing data and generating summary..."
        prompt_prefix = MODE_PROMPTS.get(mode, MODE_PROMPTS["future_pain"])
        summary = groq_summarize_with_citations(all_posts, prompt_prefix)
        current_status[keyword] = "Summary generated successfully!"

        new_query = SearchQuery(
            keyword=keyword,
            source="multi",
            mode=mode,
            result=summary,
            user_id=current_user.id
        )
        db.session.add(new_query)
        db.session.commit()
        result_obj = {
            "summary": summary,
            "sources": sources,
            "query_id": new_query.id
        }
        
        # Create cache key for future use
        cache_key = f"multi_search_{keyword}_{mode}_{current_user.id}"
        cache.set(cache_key, result_obj, expire=3600)  # Cache for 1 hour
        return jsonify(result_obj)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500



def scrape_reddit_titles(keyword):
    try:
        submissions = reddit.subreddit("all").search(keyword, limit=10)
        return [{
            "title": submission.title,
            "url": submission.url,
            "score": submission.score,
            "subreddit": submission.subreddit.display_name,
            "published": datetime.utcfromtimestamp(submission.created_utc).isoformat() if submission.created_utc else ""
        } for submission in submissions]
    except Exception as e:
        print(f"Error scraping Reddit: {e}")
        return []

def search_stackexchange(keyword, max_pages=3, pagesize=50):
    all_results = []
    url = "https://api.stackexchange.com/2.3/search/advanced"
    for page in range(1, max_pages + 1):
        resp = requests.get(url, params={
            "order": "desc",
            "sort": "relevance",
            "q": keyword,
            "site": "stackoverflow",
            "page": page,
            "pagesize": pagesize
        })
        if resp.status_code != 200:
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        all_results.extend([{"title": i.get("title", ""), "link": i.get("link", "")} for i in items])
        if not data.get("has_more", False):
            break
    return all_results

@app.route("/search", methods=["GET"])
def search_get():
    keyword = request.args.get("q", "")
    reddit_titles = scrape_reddit_titles(keyword)
    stack = search_stackexchange(keyword, max_pages=3, pagesize=50)
    blogs = []
    all_text = "\n".join([p.get("title", "") for p in reddit_titles] + [s.get("title", "") for s in stack])

    summary_prompt = f"""
You are an AI research assistant.
Based on long prompt understand the context or keyword : 
Analyze the following multi-source discussions, posts, reviews, and articles related to the keyword. These are collected from various platforms such as Reddit, Twitter, Amazon reviews, Google search results, Hacker News, and blog posts.

Content to analyze:
{all_text}

Your task is to extract insights and structure the summary under the following clear sections:

<b>Pain Points:</b>
- Identify the most commonly mentioned or implied problems and frustrations.
- Include the source context where applicable (e.g., "From Reddit user", "Amazon review", "Tweet", "Google result").
- Even if issues are not directly related to the keyword, explain how they are connected.
- Mention who is affected by each issue (e.g., users, buyers, students, founders, etc.).

<b>Challenges:</b>
- Highlight the key difficulties or bottlenecks users face.
- Include both technical and emotional/behavioral challenges.
- Clarify how each challenge ties back to the keyword, even indirectly.
- Use real context or quotes from the source if it helps clarify the challenge.

<b>Insights:</b>
- Summarize startup opportunities, emerging trends, or unmet user needs based on the content.
- Highlight any ideas or recurring themes that indicate what users wish existed.
- Use insights that apply broadly or from niche user groups.
- Make sure insights are based on actual user pain rather than speculation.

Formatting:
- Use bullet points under each heading.
- Group similar insights or problems for clarity.
- Maintain factual tone and avoid assumptions not backed by source content.
"""
    try:
        response = groq_generate_content(summary_prompt)
        return jsonify({
            "reddit": reddit_titles,
            "stack": stack,
            "blogs": blogs,
            "summary": response.strip() if response else ""
        })
    except Exception as e:
        return jsonify({
            "reddit": reddit_titles,
            "stack": stack,
            "blogs": blogs,
            "summary": f"Error generating summary: {e}"
        })

@app.route('/search', methods=['POST'])
@login_required
def search_post():
    keyword = request.form['keyword']
    source = request.form['source']
    new_query = SearchQuery(keyword=keyword, source=source, user_id=current_user.id)
    db.session.add(new_query)
    db.session.commit()
    return "Query saved!"

# --- History Management Endpoints ---
@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    queries = SearchQuery.query.filter_by(user_id=current_user.id).order_by(SearchQuery.timestamp.desc()).all()
    return jsonify([{
        'id': q.id,
        'query': q.keyword,
        'source': q.source,
        'mode': q.mode,
        'result': q.result,
        'timestamp': q.timestamp.isoformat(),
        'vertical': q.vertical
    } for q in queries])

@app.route('/api/history', methods=['POST'])
@login_required
def add_history():
    data = request.json
    q = SearchQuery(
        keyword=data['query'],
        source=data.get('source', ''),
        mode=data.get('mode', ''),
        result=data.get('result', ''),
        user_id=current_user.id,
        vertical=data.get('vertical', '')
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({'id': q.id}), 201

@app.route('/api/history/<int:query_id>', methods=['PUT'])
@login_required
def update_history(query_id):
    data = request.json
    q = SearchQuery.query.get_or_404(query_id)
    if q.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    q.result = data.get('result', q.result)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/history/<int:query_id>', methods=['DELETE'])
@login_required
def delete_history(query_id):
    q = SearchQuery.query.get_or_404(query_id)
    if q.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(q)
    db.session.commit()
    return jsonify({'success': True})
import datetime


# --- Analytics Helper Functions ---
def get_date_range(period):
    now = datetime.now()
    if period == 'week':
        since = now - datetime.timedelta(days=7)
    elif period == 'month':
        since = now - datetime.timedelta(days=30)
    else:  # year
        since = now - datetime.timedelta(days=365)
    return since, now

def get_daily_search_counts(start_date, end_date):
    daily_counts = db.session.query(
        db.func.date(SearchQuery.timestamp).label('date'),
        db.func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).group_by(
        db.func.date(SearchQuery.timestamp)
    ).all()
    
    # Create a date range and fill in missing dates with zero counts
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.date())
        current_date += datetime.timedelta(days=1)
    
    counts_dict = {str(d.date): d.count for d in daily_counts}
    return {
        'labels': [d.strftime('%Y-%m-%d') for d in date_range],
        'values': [counts_dict.get(str(d), 0) for d in date_range]
    }

def get_category_distribution(start_date, end_date):
    categories = db.session.query(
        SearchQuery.vertical,
        db.func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date,
        SearchQuery.vertical.isnot(None)
    ).group_by(
        SearchQuery.vertical
    ).order_by(
        db.desc('count')
    ).limit(6).all()
    
    return {
        'labels': [c.vertical or 'Uncategorized' for c in categories],
        'values': [c.count for c in categories]
    }

def get_trending_topics(start_date, end_date, limit=10):
    topics = db.session.query(
        SearchQuery.keyword,
        db.func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).group_by(
        SearchQuery.keyword
    ).order_by(
        db.desc('count')
    ).limit(limit).all()
    
    return [{'name': t.keyword, 'count': t.count} for t in topics]

def get_analytics_insights(start_date, end_date):
    total_searches = db.session.query(db.func.count(SearchQuery.id)).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).scalar()
    active_users = db.session.query(db.func.count(db.distinct(SearchQuery.user_id))).filter(
        SearchQuery.timestamp >= start_date,
        SearchQuery.timestamp <= end_date
    ).scalar()
    avg_searches = total_searchs / active_users if active_users > 0 else 0
    return {
        'totalSearches': total_searches,
        'activeUsers': active_users,
        'avgSearchesPerUser': avg_searches
    }

@app.route('/pain_dashboard')
@login_required
def dashboard():
    return render_template('pain_dashboard.html')

# Register blueprints
from routes import bp as new_features_bp
from direct_vertical_insights import direct_vertical_routes
app.register_blueprint(new_features_bp)
app.register_blueprint(direct_vertical_routes)

@app.route('/api/vertical_chat_history', methods=['GET'])
@login_required
def get_vertical_chat_history():
    vertical = request.args.get('vertical')
    query_text = request.args.get('query')
    if not vertical or not query_text:
        return jsonify([])
    chats = VerticalChat.query.filter_by(
        user_id=current_user.id,
        vertical=vertical,
        query_text=query_text
    ).order_by(VerticalChat.timestamp.asc()).all()
    return jsonify([
        {
            'role': chat.role,
            'text': chat.text,
            'timestamp': chat.timestamp.isoformat()
        }
        for chat in chats
    ])

@app.route('/api/status')
def api_status():
    return jsonify({"status": "OK", "message": "API is running smoothly."})

@app.route('/api/key-status')
def key_status():
    """Monitor the status of all API keys"""
    try:
        # Get current key status for Groq
        working_groq_keys = []
        rate_limited_groq_keys = []
        failed_groq_keys_list = []
        for i in range(1, 30):
            key_name = f'GROQ_API_KEY_{i}'
            key_value = os.getenv(key_name)
            if key_value and key_value.startswith('gsk_'):
                failure_info = failed_groq_keys.get(key_value)
                if failure_info:
                    if isinstance(failure_info, tuple):
                        timestamp, error_type = failure_info
                        if error_type == 'rate_limit':
                            rate_limited_groq_keys.append(key_name)
                        else:
                            failed_groq_keys_list.append(key_name)
                    else:
                        failed_groq_keys_list.append(key_name)
                else:
                    working_groq_keys.append(key_name)
        # Get current key status for OpenRouter
        working_openrouter_keys = []
        rate_limited_openrouter_keys = []
        failed_openrouter_keys_list = []
        for i in range(1, 11):
            key_name = f'OPENROUTER_API_KEY_{i}'
            key_value = os.getenv(key_name)
            if key_value and key_value.startswith('sk-'):
                failure_info = failed_openrouter_keys.get(key_value)
                if failure_info:
                    if isinstance(failure_info, tuple):
                        timestamp, error_type = failure_info
                        if error_type == 'rate_limit':
                            rate_limited_openrouter_keys.append(key_name)
                        else:
                            failed_openrouter_keys_list.append(key_name)
                    else:
                        failed_openrouter_keys_list.append(key_name)
                else:
                    working_openrouter_keys.append(key_name)
        limiter_status = {
            "active_requests": getattr(request_limiter, 'active_requests', 0),
            "max_concurrent": getattr(request_limiter, 'max_concurrent', 0),
            "available_slots": getattr(request_limiter, 'max_concurrent', 0) - getattr(request_limiter, 'active_requests', 0)
        }
        return {
            "groq": {
                "working": working_groq_keys,
                "rate_limited": rate_limited_groq_keys,
                "failed": failed_groq_keys_list
            },
            "openrouter": {
                "working": working_openrouter_keys,
                "rate_limited": rate_limited_openrouter_keys,
                "failed": failed_openrouter_keys_list
            },
            "limiter": limiter_status
        }, 200
    except Exception as e:
        import traceback
        print("Error in /api/key-status:", e)
        traceback.print_exc()
        return {"error": str(e)}, 500

@login_manager.unauthorized_handler
def unauthorized():
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 401
    return redirect(url_for('login'))

@app.route('/generate-solution', methods=['POST'])
def generate_solution():
    data = request.get_json()
    pain_point = data.get('pain_point')
    if not pain_point:
        return jsonify({'solution': None, 'error': 'No pain point provided.'}), 400
    
    # Compose a prompt for Groq
    prompt =  f"""
You are a venture-backed product strategist trusted by top startup founders and VCs (like a PM at Stripe, OpenAI, or a YC partner). Your job is to take **real user pain points** and generate **bold, insight-rich product concepts** that feel fundable and differentiated.

Your output must feel like a real pitch slide or deal memo — not a general AI summary.

ONLY use **up-to-date, post-2024 real-world data** and reference known companies or tools doing similar things. Mention what they solve well, where they fall short, and what's still open. Back this with real market context — do not hallucinate or speculate vaguely.

---

Follow this strict output format (no intro, no conclusions, no extra text):

<h2>Startup Idea</h2>
- 1-line crisp value proposition — punchy and specific.

<h3>Key Features</h3>
- 3–5 bullet points that define the product's MVP or core functionality.

<h3>Why Now?</h3>
- Real market trends, platform shifts, or behavior changes post-2024 that make this urgent.
- Reference recent AI models, SaaS adoption trends, regulations, or consumer shifts.

<h3>User Segments & Context</h3>
- Be specific. Who is experiencing this pain? Under what task or flow?
- Add examples: e.g., "Sales ops leads at mid-market SaaS using HubSpot + Notion stack"

<h3>Execution Path</h3>
- Suggest MVP tech stack or no-code/hybrid options (e.g., Supabase + Next.js + OpenAI API).
- Recommend a wedge GTM motion (e.g., Slack plugin, Chrome extension, Zapier integration).
- Mention where early traction could come from (e.g., Reddit threads, LinkedIn ICP filters).

<h3>Differentiation</h3>
- Compare with **existing tools** (name them) and state clearly what's missing.
- Examples: "Notion AI does X but fails at Y", "Perplexity nails speed, but lacks problem scoring"
- Mention technical or UX moats (e.g., fine-tuned agent + trust layer + explainability).
---

Also include:
- 🔊 **Real-sounding user quote** that expresses the pain emotionally (not generic)
- 🔥 **Pain Score (1–10)** = based on severity × frequency
- 💡 **Startup ROI Insight** = Time or revenue lost today due to this pain
---

Now analyze this pain point and output the response in the above format:

**Title:** {pain_point.get('title', 'Unknown Pain Point')}  
**Description:** {pain_point.get('description', 'No description provided')}  
**Why It's Still Unsolved:** {pain_point.get('reason_unsolved', 'Unknown reason')}  
**User Segments:** {', '.join(pain_point.get('user_segments', [])) if isinstance(pain_point.get('user_segments', []), list) else pain_point.get('user_segments', 'Unknown users')}

"""
    try:
        response = groq_generate_content(prompt)
        if response.startswith('Error:'):
            return jsonify({'error': response}), 500
        solution = response.strip()
        return jsonify({'solution': solution})
    except Exception as e:
        import traceback
        print('Error in /generate-solution:', traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/pain-cloud', methods=['GET'])
def pain_cloud_page():
    current_date = datetime.now().strftime('%B %d, %Y')
    return render_template('pain_cloud.html', current_date=current_date)

@app.route('/pain-cloud', methods=['POST'])
def pain_cloud_api():
    data = request.get_json()
    persona = data.get('persona')
    industry = data.get('industry')
    if not persona or not industry:
        return jsonify({'error': 'Missing persona or industry'}), 400
    
    # Compose a prompt for Groq
    prompt = f'''
You are a startup research analyst. Given the job role (persona) and industry below, analyze your database of user complaints, reviews, and forums to generate a "Pain Cloud" for founders:

- List the top 5 most common complaints or pain points for this persona in this industry, ranked by severity and volume. Each should be 1-2 lines, with a severity score (1-10).
- Extract the 10 most repeated keywords or phrases (with frequency counts).
- Suggest 3-5 auto-generated startup themes or opportunity areas based on these pains.

Persona: {persona}
Industry: {industry}

Return ONLY valid JSON with keys: complaints (list of {{text, severity}}), keywords (list of {{word, count}}), themes (list of strings).
'''
    try:
        response = groq_generate_content(prompt)
        if response.startswith('Error:'):
            return jsonify({'error': response}), 500
        text = response.strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                result = json.loads(json_str)
                
                # Track usage for pain cloud insights
                try:
                    new_usage = UserUsage(
                        user_id=current_user.id,
                        module='insights',
                        action='pain_cloud',
                        usage_count=1
                    )
                    db.session.add(new_usage)
                    db.session.commit()
                except Exception as e:
                    print(f"Error tracking usage: {e}")
                
                return jsonify(result)
            except json.JSONDecodeError as json_error:
                print(f"JSON decode error: {json_error}")
                print(f"Raw response: {text}")
                return jsonify({'error': f'Could not parse Groq response: {json_error}', 'raw': text}), 500
        return jsonify({'error': 'No valid JSON found in Groq response', 'raw': text}), 500
    except Exception as e:
        import traceback
        print('Error in /pain-cloud:', traceback.format_exc())
        return jsonify({'error': str(e)}), 500

PERSONA_INDUSTRY_SOURCES = {
    # ------------------- PRODUCT MANAGER -------------------
   ## ------------------- PRODUCT MANAGER -------------------
('Product Manager', 'SaaS'): ['r/ProductManagement', 'r/startups', 'r/SaaS', 'r/Entrepreneur', 'r/userexperience'],
('Product Manager', 'E-Commerce'): ['r/ProductManagement', 'r/ecommerce', 'r/startups', 'r/Entrepreneur', 'r/shopping'],
('Product Manager', 'Healthcare'): ['r/ProductManagement', 'r/HealthIT', 'r/startups', 'r/healthcare', 'r/UXDesign'],
('Product Manager', 'Logistics'): ['r/ProductManagement', 'r/logistics', 'r/supplychain', 'r/startups'],
('Product Manager', 'Cybersecurity'): ['r/ProductManagement', 'r/netsec', 'r/cybersecurity', 'r/startups'],
('Product Manager', 'Fintech'): ['r/ProductManagement', 'r/fintech', 'r/startups', 'r/FinancialTechnology'],
('Product Manager', 'Real Estate'): ['r/ProductManagement', 'r/realestate', 'r/Entrepreneur'],
('Product Manager', 'EdTech'): ['r/ProductManagement', 'r/EdTech', 'r/startups', 'r/Teachers'],
('Product Manager', 'Gaming'): ['r/ProductManagement', 'r/gamedev', 'r/gaming', 'r/GameDesign'],

## ------------------- FRONTEND DEVELOPER -------------------
('Frontend Developer', 'SaaS'): ['r/webdev', 'r/frontend', 'r/javascript', 'r/SaaS', 'r/reactjs'],
('Frontend Developer', 'E-Commerce'): ['r/webdev', 'r/ecommerce', 'r/frontend', 'r/Shopify'],
('Frontend Developer', 'Healthcare'): ['r/webdev', 'r/HealthIT', 'r/frontend'],
('Frontend Developer', 'Logistics'): ['r/webdev', 'r/frontend', 'r/supplychain', 'r/logistics'],
('Frontend Developer', 'Cybersecurity'): ['r/webdev', 'r/frontend', 'r/netsec'],
('Frontend Developer', 'Fintech'): ['r/webdev', 'r/fintech', 'r/frontend'],
('Frontend Developer', 'Real Estate'): ['r/webdev', 'r/frontend', 'r/realestateinvesting'],
('Frontend Developer', 'EdTech'): ['r/webdev', 'r/EdTech', 'r/frontend'],
('Frontend Developer', 'Gaming'): ['r/webdev', 'r/gamedev', 'r/unity3d', 'r/Frontend'],

## ------------------- BACKEND DEVELOPER -------------------
('Backend Developer', 'SaaS'): ['r/backend', 'r/SaaS', 'r/devops', 'r/programming'],
('Backend Developer', 'E-Commerce'): ['r/backend', 'r/ecommerce', 'r/devops', 'r/Shopify'],
('Backend Developer', 'Healthcare'): ['r/backend', 'r/HealthIT', 'r/programming'],
('Backend Developer', 'Logistics'): ['r/backend', 'r/logistics', 'r/supplychain', 'r/devops'],
('Backend Developer', 'Cybersecurity'): ['r/backend', 'r/netsec', 'r/cybersecurity'],
('Backend Developer', 'Fintech'): ['r/backend', 'r/fintech', 'r/devops'],
('Backend Developer', 'Real Estate'): ['r/backend', 'r/realestateinvesting', 'r/devops'],
('Backend Developer', 'EdTech'): ['r/backend', 'r/EdTech', 'r/learnprogramming'],
('Backend Developer', 'Gaming'): ['r/backend', 'r/gamedev', 'r/unity3d'],

## ------------------- DATA SCIENTIST -------------------
('Data Scientist', 'SaaS'): ['r/datascience', 'r/MachineLearning', 'r/SaaS'],
('Data Scientist', 'E-Commerce'): ['r/datascience', 'r/ecommerce', 'r/marketing', 'r/dataisbeautiful'],
('Data Scientist', 'Healthcare'): ['r/datascience', 'r/HealthIT', 'r/healthcareai'],
('Data Scientist', 'Logistics'): ['r/datascience', 'r/supplychain', 'r/logistics'],
('Data Scientist', 'Cybersecurity'): ['r/datascience', 'r/netsec', 'r/cybersecurity'],
('Data Scientist', 'Fintech'): ['r/datascience', 'r/fintech', 'r/algorithms'],
('Data Scientist', 'Real Estate'): ['r/datascience', 'r/realestateinvesting'],
('Data Scientist', 'EdTech'): ['r/datascience', 'r/EdTech', 'r/learnmachinelearning'],
('Data Scientist', 'Gaming'): ['r/datascience', 'r/gamedev', 'r/GameDesign'],

## ------------------- DESIGNER -------------------
('Designer', 'SaaS'): ['r/UXDesign', 'r/web_design', 'r/SaaS', 'r/userexperience'],
('Designer', 'E-Commerce'): ['r/UXDesign', 'r/ecommerce', 'r/web_design'],
('Designer', 'Healthcare'): ['r/UXDesign', 'r/HealthIT', 'r/userexperience'],
('Designer', 'Logistics'): ['r/UXDesign', 'r/logistics', 'r/supplychain'],
('Designer', 'Cybersecurity'): ['r/UXDesign', 'r/cybersecurity', 'r/design'],
('Designer', 'Fintech'): ['r/UXDesign', 'r/fintech', 'r/web_design'],
('Designer', 'Real Estate'): ['r/UXDesign', 'r/realestateinvesting', 'r/web_design'],
('Designer', 'EdTech'): ['r/UXDesign', 'r/EdTech', 'r/design'],
('Designer', 'Gaming'): ['r/UXDesign', 'r/gamedev', 'r/GameDesign'],

## ------------------- QA ENGINEER -------------------
('QA Engineer', 'SaaS'): ['r/qualityassurance', 'r/SaaS', 'r/SoftwareTesting'],
('QA Engineer', 'E-Commerce'): ['r/qualityassurance', 'r/ecommerce', 'r/SoftwareTesting'],
('QA Engineer', 'Healthcare'): ['r/qualityassurance', 'r/HealthIT', 'r/SoftwareTesting'],
('QA Engineer', 'Gaming'): ['r/qualityassurance', 'r/gamedev', 'r/GameTesting'],
('QA Engineer', 'EdTech'): ['r/qualityassurance', 'r/EdTech', 'r/SoftwareTesting'],
('QA Engineer', 'Fintech'): ['r/qualityassurance', 'r/fintech', 'r/SoftwareTesting'],
('QA Engineer', 'Cybersecurity'): ['r/qualityassurance', 'r/netsec', 'r/SoftwareTesting'],
('QA Engineer', 'Real Estate'): ['r/qualityassurance', 'r/realestate', 'r/SoftwareTesting', 'r/AskEngineers'],



## ------------------- DEVOPS ENGINEER -------------------
('DevOps Engineer', 'SaaS'): ['r/devops', 'r/SaaS', 'r/kubernetes'],
('DevOps Engineer', 'E-Commerce'): ['r/devops', 'r/ecommerce', 'r/aws'],
('DevOps Engineer', 'Healthcare'): ['r/devops', 'r/HealthIT'],
('DevOps Engineer', 'Cybersecurity'): ['r/devops', 'r/netsec', 'r/cybersecurity'],
('DevOps Engineer', 'Fintech'): ['r/devops', 'r/fintech'],
('DevOps Engineer', 'EdTech'): ['r/devops', 'r/EdTech'],
('DevOps Engineer', 'Real Estate'): ['r/devops', 'r/realestate', 'r/sysadmin'],
('DevOps Engineer', 'Logistics'): ['r/devops', 'r/logistics', 'r/supplychain', 'r/sysadmin'],
('DevOps Engineer', 'Gaming'): ['r/devops', 'r/gamedev', 'r/unity3d', 'r/aws', 'r/sysadmin'],




## ------------------- SUPPORT MANAGER -------------------
('Support Manager', 'SaaS'): ['r/sysadmin', 'r/techsupport', 'r/SaaS'],
('Support Manager', 'E-Commerce'): ['r/sysadmin', 'r/techsupport', 'r/ecommerce'],
('Support Manager', 'Healthcare'): ['r/sysadmin', 'r/techsupport', 'r/HealthIT'],
('Support Manager', 'Gaming'): ['r/sysadmin', 'r/techsupport', 'r/gaming'],
('Support Manager', 'Logistics'): ['r/sysadmin', 'r/techsupport', 'r/logistics', 'r/supplychain'],
('Support Manager', 'Real Estate'): ['r/sysadmin', 'r/techsupport', 'r/realestate'],
('Support Manager', 'Cybersecurity'): ['r/sysadmin', 'r/techsupport', 'r/cybersecurity', 'r/netsec'],
('Support Manager', 'Fintech'): ['r/sysadmin', 'r/techsupport', 'r/fintech'],
('Support Manager', 'EdTech'): ['r/sysadmin', 'r/techsupport', 'r/EdTech'],
('Marketer', 'Cybersecurity'): ['r/marketing', 'r/cybersecurity', 'r/netsec'],
('Marketer', 'Real Estate'): ['r/marketing', 'r/realestate', 'r/realtors'],
('Marketer', 'Logistics'): ['r/marketing', 'r/logistics', 'r/supplychain'],

## ------------------- SALESPERSON -------------------
('Salesperson', 'SaaS'): ['r/sales', 'r/SaaS', 'r/startups'],
('Salesperson', 'E-Commerce'): ['r/sales', 'r/ecommerce', 'r/Entrepreneur'],
('Salesperson', 'Healthcare'): ['r/sales', 'r/HealthIT', 'r/Entrepreneur'],
('Salesperson', 'Gaming'): ['r/sales', 'r/gamedev', 'r/GameSale'],
('Salesperson', 'EdTech'): ['r/sales', 'r/EdTech', 'r/Entrepreneur'],
('Salesperson', 'Fintech'): ['r/sales', 'r/fintech', 'r/startups'],
('Salesperson', 'Cybersecurity'): ['r/sales', 'r/cybersecurity', 'r/netsec'],
('Salesperson', 'Real Estate'): ['r/sales', 'r/realestate', 'r/realtors'],
('Salesperson', 'Logistics'): ['r/sales', 'r/logistics', 'r/supplychain'],


## ------------------- FOUNDER -------------------
('Founder', 'SaaS'): ['r/startups', 'r/Entrepreneur', 'r/SaaS'],
('Founder', 'E-Commerce'): ['r/startups', 'r/ecommerce', 'r/Entrepreneur'],
('Founder', 'Healthcare'): ['r/startups', 'r/HealthIT', 'r/Entrepreneur'],
('Founder', 'Gaming'): ['r/startups', 'r/gamedev', 'r/gaming'],
('Founder', 'EdTech'): ['r/startups', 'r/EdTech', 'r/Entrepreneur'],
('Founder', 'Fintech'): ['r/startups', 'r/fintech', 'r/Entrepreneur'],
('Founder', 'Cybersecurity'): ['r/startups', 'r/netsec', 'r/cybersecurity'],
('Founder', 'Real Estate'): ['r/startups', 'r/realestateinvesting', 'r/Entrepreneur'],
('Founder', 'Logistics'): ['r/startups', 'r/logistics', 'r/supplychain'],


## ------------------- SOFTWARE ENGINEER -------------------
('Software Engineer', 'SaaS'): ['r/SoftwareEngineering', 'r/SaaS', 'r/programming'],
('Software Engineer', 'E-Commerce'): ['r/SoftwareEngineering', 'r/ecommerce', 'r/webdev'],
('Software Engineer', 'Healthcare'): ['r/SoftwareEngineering', 'r/HealthIT', 'r/programming'],
('Software Engineer', 'Gaming'): ['r/SoftwareEngineering', 'r/gamedev', 'r/unity3d'],
('Software Engineer', 'EdTech'): ['r/SoftwareEngineering', 'r/EdTech', 'r/programming'],
('Software Engineer', 'Fintech'): ['r/SoftwareEngineering', 'r/fintech', 'r/programming'],
('Software Engineer', 'Cybersecurity'): ['r/SoftwareEngineering', 'r/cybersecurity', 'r/netsec'],
('Software Engineer', 'Real Estate'): ['r/SoftwareEngineering', 'r/realestate', 'r/programming'],
('Software Engineer', 'Logistics'): ['r/SoftwareEngineering', 'r/logistics', 'r/supplychain'],


## ------------------- CUSTOMER SUPPORT -------------------
('Customer Support', 'SaaS'): ['r/techsupport', 'r/sysadmin', 'r/SaaS'],
('Customer Support', 'E-Commerce'): ['r/techsupport', 'r/ecommerce', 'r/sysadmin'],
('Customer Support', 'Healthcare'): ['r/techsupport', 'r/HealthIT', 'r/sysadmin'],
('Customer Support', 'Gaming'): ['r/techsupport', 'r/gaming', 'r/sysadmin'],
('Customer Support', 'EdTech'): ['r/techsupport', 'r/EdTech', 'r/sysadmin'],
('Customer Support', 'Fintech'): ['r/techsupport', 'r/fintech', 'r/sysadmin'],
('Customer Support', 'Cybersecurity'): ['r/techsupport', 'r/cybersecurity', 'r/sysadmin'],
('Customer Support', 'Real Estate'): ['r/techsupport', 'r/realestate', 'r/sysadmin'],
('Customer Support', 'Logistics'): ['r/techsupport', 'r/logistics', 'r/supplychain'],


}





from flask import request, jsonify
from collections import Counter
import re
import time




from flask import request, jsonify, render_template
from collections import Counter
import re
import time
import random
import json
from datetime import datetime, timedelta


STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because been before being below between both
but by can't cannot could couldn't did didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how how's i i'd
i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such
than that that's the their theirs them themselves then there there's these they they'd they'll they're they've this
those through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's
where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves
""".split())

# ---- ROUTES ----
@app.route('/pain-cloud-realtime', methods=['GET'])
def pain_cloud_realtime_page():
    return render_template('pain_cloud_realtime.html')
@app.route('/pain-cloud-combined', methods=['GET'])
def pain_cloud_combined_page():
    return render_template('pain_cloud_combined.html')



@app.route('/pain-cloud-realtime', methods=['POST'])
def pain_cloud_realtime_api():
    data = request.get_json()
    persona = data.get('persona')
    industry = data.get('industry')
    mode = data.get('mode', 'real')

    if not persona or not industry:
        return jsonify({'error': 'Missing persona or industry'}), 400

    sources = PERSONA_INDUSTRY_SOURCES.get((persona, industry)) or PERSONA_SOURCES.get(persona, [])

    def is_complaint_post(title, body):
        complaint_keywords = [
            "hate", "struggle", "issue", "problem", "bug", "error", "glitch", "broken", "crash", "lag",
            "not working", "doesn't work", "stopped working", "won't load", "can't log in", "crashes", "fails", "failure",
            "unable to", "doesn't respond", "hangs", "freeze", "timeout", "corrupted", "inaccessible",
            "annoying", "frustrating", "confusing", "complicated", "infuriating", "maddening", "disappointed", "slow",
            "bloated", "tedious", "pointless", "missing feature", "churn", "costs too much", "pricing problem", "overpriced",
            "hard to scale", "lack of support", "team hates", "reviews are bad", "burnout", "micromanage"
        ]
        combined = f"{title.lower()} {body.lower()}"
        return any(kw in combined for kw in complaint_keywords)

    all_posts = []

    # --- Parallel fetch Reddit posts ---
    reddit_sources = [s[2:] for s in sources if s.startswith('r/')]
    def fetch_subreddit(subreddit):
        posts = []
        try:
            for post in reddit.subreddit(subreddit).new(limit=100):
                if is_complaint_post(post.title, post.selftext):
                    posts.append({
                        'title': post.title or '',
                        'selftext': post.selftext or '',
                        'score': post.score,
                        'url': f"https://reddit.com{post.permalink}",
                        'source': f"r/{subreddit}",
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(post.created_utc)),
                        'created_utc': post.created_utc
                    })
        except Exception as e:
            print(f"[Reddit error] r/{subreddit}: {e}")
        return posts

    with ThreadPoolExecutor(max_workers=min(8, len(reddit_sources))) as executor:
        futures = [executor.submit(fetch_subreddit, sub) for sub in reddit_sources]
        for future in as_completed(futures):
            all_posts.extend(future.result())

    if not all_posts:
        return jsonify({'error': 'No relevant complaint posts found.'})

    def score(post):
        return post['score'] - 0.5 * ((time.time() - post['created_utc']) / 86400)

    # Limit to top 20 posts instead of 50 to reduce payload size
    top_posts = sorted(all_posts, key=score, reverse=True)[:20]

    # --- Groq pain point extraction (single call) ---
    prompt = f"""
You are a world-class startup advisor with deep knowledge of SaaS, AI, and product-market fit. You deeply understand the daily pain points, inefficiencies, and unmet needs of a **{persona}** working in the **{industry}** industry.

You are analyzing a set of **real Reddit posts** shared by professionals in this space. Your goal is to identify only the **most relevant, most painful, most underserved problems** — the kind that would make a **founder stop scrolling and start building**.

Return a **JSON array**, where each item is a **validated pain point**, with the following fields:

- summary: A clear, concise, *non-obvious* startup-relevant summary of the core complaint (1–2 sentences max). Focus on **what's broken or inefficient** — no vague advice.
- reason: Explain **why this is painful or urgent** specifically for a {persona} in the {industry} industry. Mention what impact it has (time wasted, money lost, growth blocked, etc).
- market_gap: Is there a known tool or company that tries to solve this? If yes, name it, and explain what it lacks for this exact persona in this industry. If no solution exists, say so — and why this is a true whitespace.
- trend: Is this complaint a **recurring trend** (e.g., seen in multiple posts) or a **rising pain** in recent months? Mention any patterns (e.g., "common among early-stage SaaS PMs using legacy CRMs").
- severity: A score from 1–10 based on urgency, frequency, and business impact. Use 9–10 only for **burning**, widespread pains.
- title: The title of the Reddit post.
- excerpt: 1–2 real sentences from the post that best show the pain, frustration, or blocker. Must be verbatim.
- upvotes: Reddit upvote count.
- source: The subreddit name (e.g., "r/ProductManagement").
- timestamp: The original post's UTC timestamp.
- url: Full direct link to the Reddit post.
"""
    for idx, post in enumerate(top_posts, 1):
        title = post['title'][:200] if len(post['title']) > 200 else post['title']
        text = post['selftext'][:500] if len(post['selftext']) > 500 else post['selftext']
        prompt += f"\n[{idx}] Title: {title}\nText: {text}\nUpvotes: {post['score']}\nSource: {post['source']}\nTimestamp: {post['timestamp']}\nURL: {post['url']}"
    prompt += "\n\nOnly include pain points that are truly startup-relevant and avoid generic complaints."

    # --- Robust Groq call: always return valid JSON array ---
    import re, json
    pain_points = []
    for _ in range(30):  # Try up to 30 keys if needed
        try:
            response = groq_generate_content(prompt)
            match = re.search(r'\[.*\]', response.strip(), re.DOTALL)
            if match:
                try:
                    pain_points = json.loads(match.group(0))
                    break  # Success!
                except Exception as parse_e:
                    print(f"[Groq error]: {parse_e}. Trying next key...")
                    continue
            else:
                print("[Groq error]: No JSON array found in response, trying next key...")
                continue
        except Exception as e:
            print(f"[Groq error]: {e}. Trying next key...")
            continue
    # If all keys fail, return a friendly fallback
    if not pain_points:
        pain_points = [{
            'summary': 'No valid pain points could be extracted at this time.',
            'reason': 'The AI did not return a valid result. Please try again later.',
            'market_gap': '',
            'trend': '',
            'severity': 0,
            'title': '',
            'excerpt': '',
            'upvotes': 0,
            'source': '',
            'timestamp': '',
            'url': ''
        }]

    # (rest of the endpoint unchanged)
    real_pain_points = [p for p in pain_points if not (isinstance(p.get('reason', ''), str) and 'fallback: complaint matched keyword list' in p.get('reason', '').lower())]

    num_bins = 15
    now = time.time()
    bin_edges = [now - (num_bins - i) * 7 * 86400 for i in range(num_bins + 1)]
    all_keywords = []

    def enrich_point(point):
        point['persona'] = persona
        sev = point.get('severity')
        sev_score = int(sev) if isinstance(sev, int) or (isinstance(sev, str) and sev.isdigit()) else 7
        point['tag'] = 'VC-worthy' if sev_score >= 8 else 'Quick Fix'
        try:
            keyword_prompt = f"Extract 3 startup-relevant keywords from this pain point:\n{point.get('title', '')[:100]}\n{point.get('reason', '')[:200]}\nReturn JSON: {{\"keywords\": [\"...\"]}}"
            kw_resp = groq_generate_content(keyword_prompt, max_tokens=100)
            match = re.search(r'\{.*\}', kw_resp.strip())
            if match:
                parsed = json.loads(match.group(0))
                point['keywords'] = [{'word': k, 'score': random.randint(6, 10)} for k in parsed['keywords']]
        except:
            if 'keywords' not in point:
                text = f"{point.get('title', '')} {point.get('reason', '')}"
                top = Counter(re.findall(r'\b[a-z]{4,}\b', text.lower())).most_common(3)
                point['keywords'] = [{'word': w, 'score': min(10, max(3, f))} for w, f in top]
        matching_posts = [p for p in all_posts if point['title'].lower() in p['title'].lower()]
        bin_counts = [0] * num_bins
        for post in matching_posts:
            ts = post['created_utc']
            for i in range(num_bins):
                if bin_edges[i] <= ts < bin_edges[i + 1]:
                    bin_counts[i] += 1
                    break
        point['sparkline_data'] = bin_counts or [0] * num_bins
        delta = bin_counts[-1] - bin_counts[0] if bin_counts else 0
        point['trend_direction'] = 'rising' if delta > 2 else 'fading' if delta < -2 else 'flat'
        current_date = datetime.now().strftime('%B %d, %Y')
        try:
            insight_prompt = f"""Analyze this pain trend for {persona}s in {industry}:
Analyze the following pain trend among {persona}s in the {industry} industry, using Reddit frequency data up to {current_date}.

Deliver a clear, sharp, **conviction-based insight** like a VC would pitch internally.
Avoid weak or indecisive language. Take a stance — for or against investing product resources.

Frame the insight through the lens of what a {persona} in the {industry} industry cares most about — e.g., speed to launch, retention, roadmap clarity, developer productivity, or customer satisfaction. Think about what blocks their outcomes and how solving this would unlock leverage.

Cover:
1. **Trajectory**: Is this a rising, fading, or stagnant pain? (Quantify trend where possible.)
2. **Urgency Signal**: What does the emotion + frequency + severity tell us?
3. **Market Risk**: What's at stake if ignored — missed revenue, roadmap slip, morale loss?
4. **Strategic Opportunity**: Could this be a wedge into a broader product or service? Is it timing-sensitive?

Emphasize **why a founder or PM should act on this now**. Would fixing this 10x outcomes? Unlock new markets? Lower churn?

Where possible, **quantify** the impact: % of team affected, time wasted, missed goals. Use the quote to assess **emotion** and user frustration.

Avoid vague language like "might," "maybe," or "could." Be definitive and useful.

Context:
Pain Summary: {point['summary']}
Reason: {point['reason']}
Market Gap: {point['market_gap']}
Trend: {point['trend']}
Role: {persona}
Industry: {industry}
Severity: {point['severity']}/10  
Excerpt: "{point['excerpt']}"


Provide a brief, actionable insight (max 200 words) about why this matters for {persona}s in the {industry} industry."""
            insight_resp = groq_generate_content(insight_prompt, max_tokens=300)
            point['sparkline_insight'] = insight_resp.strip()
            point['trend_label'] = "Trending"
        except Exception as e:
            point['sparkline_insight'] = ""
            point['trend_label'] = ""
        if 'keywords' not in point or not point['keywords']:
            text = f"{point.get('title', '')} {point.get('reason', '')}"
            top = Counter(re.findall(r'\b[a-z]{4,}\b', text.lower())).most_common(3)
            point['keywords'] = [{'word': w, 'score': min(10, max(3, f))} for w, f in top]
        all_keywords.extend([k['word'] for k in point['keywords']])
        return point
    with ThreadPoolExecutor(max_workers=4) as executor:
        enriched_points = list(executor.map(enrich_point, real_pain_points[:10]))
    trending_keywords = [kw for kw, _ in Counter(all_keywords).most_common(10)]
    rising_trend, fading_trend, flat_trend = [], [], []
    for point in enriched_points:
        dir = point.get('trend_direction', 'unknown')
        if dir == 'rising':
            rising_trend.append(point)
        elif dir == 'fading':
            fading_trend.append(point)
        elif dir == 'flat':
            flat_trend.append(point)
    return jsonify({
        'pain_points': enriched_points,
        'trending_keywords': trending_keywords,
        'groups': {
            'rising': rising_trend,
            'fading': fading_trend,
            'flat': flat_trend
        },
        'raw_posts': top_posts
    })
    
    
# Pain Search Engine Routes
@app.route('/pain-search-engine')
@login_required
def pain_search_engine():
    """Render the pain search engine page"""
    return render_template('pain_search_engine.html')


@app.route('/api/pain-search', methods=['POST'])
@login_required
def pain_search_api():
    """API endpoint for pain search functionality"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        category = data.get('category', 'all')
        
        if not query:
            return jsonify({"error": "Missing query parameter"}), 400
        
        print(f"🔍 Pain search for: {query}")
        
        # Initialize results dictionary
        results = {
            'reddit': [],
            'news': [],
            'stackoverflow': [],
            'complaintsboard': []
        }
        
        # Search across multiple sources
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Reddit search - use broader search terms
            reddit_query = f"{query} (problem OR issue OR pain OR complaint OR struggle OR frustration OR broken OR bug OR error OR fail OR difficult OR challenging OR annoying OR terrible OR awful OR hate OR disappointed)"
            reddit_future = executor.submit(get_reddit_posts_with_replies, reddit_query, max_posts=15)
            
            # News API search - already optimized for pain points
            news_future = executor.submit(search_news_api, query, max_results=20)
            
            # Stack Overflow search - focus on problems and errors
            stackoverflow_query = f"{query} (problem OR error OR bug OR issue OR fail OR broken OR doesn't work OR not working)"
            stackoverflow_future = executor.submit(search_stackoverflow, stackoverflow_query, max_pages=3, pagesize=30)
            
            # ComplaintsBoard search - already optimized for complaints
            complaints_future = executor.submit(scrape_complaintsboard_full_text, query, max_pages=8)
            
            # Collect results
            try:
                results['reddit'] = reddit_future.result(timeout=45)
                print(f"✅ Reddit: {len(results['reddit'])} results")
            except Exception as e:
                print(f"❌ Reddit search error: {e}")
                results['reddit'] = []
            
            try:
                results['news'] = news_future.result(timeout=30)
                print(f"✅ News: {len(results['news'])} results")
            except Exception as e:
                print(f"❌ News search error: {e}")
                results['news'] = []
            
            try:
                results['stackoverflow'] = stackoverflow_future.result(timeout=30)
                print(f"✅ Stack Overflow: {len(results['stackoverflow'])} results")
            except Exception as e:
                print(f"❌ Stack Overflow search error: {e}")
                results['stackoverflow'] = []
            
            try:
                results['complaintsboard'] = complaints_future.result(timeout=60)
                print(f"✅ ComplaintsBoard: {len(results['complaintsboard'])} results")
            except Exception as e:
                print(f"❌ ComplaintsBoard search error: {e}")
                results['complaintsboard'] = []
        
        # Combine all content for AI analysis
        all_content = []
        
        # Process Reddit results
        for post in results['reddit']:
            content = f"{post.get('title', '')}\n{post.get('selftext', '')}"
            if len(content.strip()) > 50:  # Only include posts with substantial content
                all_content.append({
                    'title': post.get('title', ''),
                    'content': content,
                    'url': post.get('url', ''),
                    'source': 'Reddit',
                    'score': post.get('score', 0),
                    'comments': post.get('comments', [])
                })
        
        # Process News results
        for article in results['news']:
            content = article.get('content', '') or article.get('description', '')
            if content and len(content.strip()) > 50:
                all_content.append({
                    'title': article.get('title', ''),
                    'content': content,
                    'url': article.get('url', ''),
                    'source': 'News',
                    'score': 0,
                    'publishedAt': article.get('publishedAt', '')
                })
        
        # Process Stack Overflow results
        for question in results['stackoverflow']:
            title = question.get('title', '')
            if title and len(title.strip()) > 20:
                all_content.append({
                    'title': title,
                    'content': title,  # Stack Overflow API doesn't provide full content
                    'url': question.get('link', ''),
                    'source': 'Stack Overflow',
                    'score': 0
                })
        
        # Process ComplaintsBoard results
        for complaint in results['complaintsboard']:
            content = complaint.get('text', '') or complaint.get('title', '')
            if content and len(content.strip()) > 30:
                all_content.append({
                    'title': complaint.get('title', ''),
                    'content': content,
                    'url': complaint.get('url', ''),
                    'source': 'ComplaintsBoard',
                    'score': 0
                })
        
        print(f"📊 Total content items: {len(all_content)}")
        
        # Generate AI analysis using Groq
        if all_content:
            # Create a more detailed and specific prompt
            analysis_prompt = f"""
You are an expert startup advisor and pain point analyst specializing in identifying real user problems and startup opportunities. 

Analyze the following content related to "{query}" and extract specific, actionable insights. Focus on REAL problems that users are actually experiencing, not generic statements.

IMPORTANT: If the content doesn't contain specific pain points or problems, say so clearly. Don't make up generic problems.

For each PAIN POINT found, provide:
- title: Specific, clear problem statement (e.g., "Users can't integrate with existing CRM systems" not "General integration issues")
- description: Detailed explanation with specific examples from the content
- severity: Score from 1-10 based on user frustration and business impact
- user_segments: Specific user types affected (e.g., "Small business owners", "Product managers at SaaS companies")
- frequency: How often mentioned or implied
- business_impact: Specific impact (e.g., "Loses 2 hours per day", "Reduces conversion by 30%")
- emotional_intensity: Level of user frustration (1-10)
- quotes: Direct quotes from users if available

For each STARTUP OPPORTUNITY, provide:
- idea: Specific business idea, not generic
- value_proposition: Clear value provided
- validation_score: Score from 1-10 based on evidence
- target_users: Specific user segments
- urgency: How urgent the need is

Return ONLY valid JSON in this exact format:
{{
    "pain_points": [
        {{
            "title": "Specific problem statement",
            "description": "Detailed explanation with examples",
            "severity": 8,
            "user_segments": ["Specific user type"],
            "frequency": "How often mentioned",
            "business_impact": "Specific impact",
            "emotional_intensity": 7,
            "quotes": ["Direct quote if available"]
        }}
    ],
    "startup_opportunities": [
        {{
            "idea": "Specific business idea",
            "value_proposition": "Clear value provided",
            "validation_score": 8,
            "target_users": ["Specific user segments"],
            "urgency": "High/Medium/Low"
        }}
    ]
}}

Content to analyze:
"""
            
            # Add content to prompt with better formatting
            for i, item in enumerate(all_content[:25]):  # Limit to 25 items
                source = item['source']
                title = item['title'][:200]  # Limit title length
                content = item['content'][:400]  # Limit content length
                
                analysis_prompt += f"\n--- SOURCE {i+1}: {source} ---\n"
                analysis_prompt += f"TITLE: {title}\n"
                analysis_prompt += f"CONTENT: {content}\n"
                if item.get('comments'):
                    analysis_prompt += f"COMMENTS: {' '.join(item['comments'][:3])}\n"
                analysis_prompt += f"URL: {item['url']}\n"
            
            analysis_prompt += "\n\nAnalyze the above content and return ONLY the JSON response. If no specific pain points are found, return empty arrays but explain why in the description."
            
            try:
                print("🤖 Generating AI analysis...")
                analysis_response = groq_generate_content_with_fallback(analysis_prompt, max_tokens=4000, temperature=0.7)
                
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', analysis_response, re.DOTALL)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group(0))
                        print(f"✅ AI analysis successful: {len(analysis.get('pain_points', []))} pain points, {len(analysis.get('startup_opportunities', []))} opportunities")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error: {e}")
                        analysis = create_fallback_analysis(query, all_content)
                else:
                    print("❌ No JSON found in response")
                    analysis = create_fallback_analysis(query, all_content)
            except Exception as e:
                print(f"❌ AI analysis error: {e}")
                analysis = create_fallback_analysis(query, all_content)
        else:
            print("❌ No content found for analysis")
            analysis = {
                "pain_points": [],
                "startup_opportunities": [],
                "note": f"No relevant content found for '{query}'. Try a different search term or check if the sources are working properly."
            }
        
        # Calculate statistics
        total_sources = sum(1 for source_data in results.values() if source_data)
        total_items = sum(len(source_data) for source_data in results.values())
        
        return jsonify({
            "query": query,
            "category": category,
            "results": results,
            "analysis": analysis,
            "total_sources": total_sources,
            "total_items": total_items,
            "content_count": len(all_content)
        })
        
    except Exception as e:
        print(f"❌ Pain search API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


def create_fallback_analysis(query, all_content):
    """Create a more specific fallback analysis based on available content"""
    if not all_content:
        return {
            "pain_points": [],
            "startup_opportunities": [],
            "note": f"No content found for '{query}'. The search may need different terms or the sources may be temporarily unavailable."
        }
    
    # Extract some basic insights from the content
    sources_found = list(set(item['source'] for item in all_content))
    content_summary = f"Found {len(all_content)} items across {len(sources_found)} sources: {', '.join(sources_found)}"
    
    return {
        "pain_points": [
            {
                "title": f"Limited data available for '{query}'",
                "description": f"Search returned {len(all_content)} items but specific pain points couldn't be extracted. {content_summary}",
                "severity": 5,
                "user_segments": ["Users searching for this topic"],
                "frequency": "Unknown",
                "business_impact": "Unable to determine",
                "emotional_intensity": 5,
                "quotes": []
            }
        ],
        "startup_opportunities": [
            {
                "idea": f"Better search and analysis tools for '{query}'",
                "value_proposition": "Provide more comprehensive data collection and analysis",
                "validation_score": 6,
                "target_users": ["Researchers", "Analysts"],
                "urgency": "Medium"
            }
        ],
        "note": f"Analysis limited due to insufficient specific pain point data. Consider refining your search terms or checking back later when more data is available."
    }

def test_news_api():
    """Test the News API functionality"""
    # Use the API key from environment or the one provided by user
    api_key = NEWS_API_KEY or "f3919401153f44d7ae3c9b7f8b610702"
    
    if not api_key:
        print("❌ NEWS_API_KEY not configured")
        return False
    
    try:
        # Test basic functionality with the correct date range for free plan
        test_params = {
            "q": "tesla",
            "from": "2025-05-19",  # Earliest allowed date for free plan
            "sortBy": "publishedAt",
            "apiKey": api_key,
            "pageSize": 5
        }
        
        print(f"🧪 Testing News API with key: {api_key[:10]}...{api_key[-4:]}")
        
        response = requests.get(
            f"{NEWS_API_BASE_URL}/everything",
            params=test_params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            print(f"✅ News API test successful: Found {len(articles)} articles")
            
            # Show a sample article
            if articles:
                sample = articles[0]
                print(f"📰 Sample article: {sample.get('title', 'No title')}")
                print(f"   Source: {sample.get('source', {}).get('name', 'Unknown')}")
                print(f"   URL: {sample.get('url', 'No URL')}")
            
            return True
        elif response.status_code == 401:
            print("❌ News API test failed: Invalid API key")
            return False
        elif response.status_code == 429:
            print("⚠️ News API test failed: Rate limit exceeded")
            return False
        else:
            print(f"❌ News API test failed: Status {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ News API test error: {e}")
        return False


# Test News API on startup


# Live Trends Routes
@app.route('/live-trends')
@login_required
def live_trends():
    return render_template('live_trends.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/api/live-trends', methods=['POST'])
@login_required
def live_trends_api():
    """API endpoint for live trends functionality"""
    try:
        data = request.get_json()
        region = data.get('region', 'global')
        category = data.get('category', 'all')
        time_window = data.get('time_window', '24h')  # 24h, 7d, 30d
        
        print(f"🌍 Live trends request: region={region}, category={category}, window={time_window}")
        
        # Track usage for trends
        try:
            new_usage = UserUsage(
                user_id=current_user.id,
                module='trends',
                action='analysis',
                usage_count=1
            )
            db.session.add(new_usage)
            db.session.commit()
        except Exception as e:
            print(f"Error tracking usage: {e}")
        
        # Calculate date range based on time window
        def get_date_range_from_window(time_window):
            now = datetime.now()
            if time_window == '24h':
                start_date = now - timedelta(days=1)
            elif time_window == '7d':
                start_date = now - timedelta(days=7)
            elif time_window == '30d':
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=1)  # Default to 24h
            
            return start_date, now
        
        start_date, end_date = get_date_range_from_window(time_window)
        print(f"📅 Date range: {start_date} to {end_date}")
        
        # Initialize results with fallback data
        trends_data = {
            'news_trends': [],
            'reddit_trends': [],
            'stackoverflow_trends': [],
            'complaints_trends': [],
            'global_trends': [],
            'regional_trends': {},
            'category_trends': {},
            'rising_topics': [],
            'declining_topics': [],
            'hot_keywords': []
        }
        
        # Get trending topics from News (hybrid: RSS, scraping, fallback to NewsAPI)
        def get_news_trends():
            try:
                # Use hybrid aggregator first
                headlines = get_news_trends_hybrid(category if category != 'all' else None, max_items=20)
                if headlines:
                    # Filter headlines by date
                    filtered_headlines = []
                    for headline in headlines:
                        published_at = headline.get('publishedAt', '')
                        if published_at:
                            try:
                                # Parse the published date
                                if isinstance(published_at, str):
                                    # Handle different date formats
                                    if 'T' in published_at:
                                        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                    else:
                                        pub_date = datetime.strptime(published_at, '%Y-%m-%d')
                                else:
                                    pub_date = published_at
                                
                                # Check if within time window
                                if start_date <= pub_date <= end_date:
                                    filtered_headlines.append(headline)
                            except Exception as e:
                                print(f"Error parsing date {published_at}: {e}")
                                # Include if we can't parse the date
                                filtered_headlines.append(headline)
                        else:
                            # Include if no date available
                            filtered_headlines.append(headline)
                    
                    return filtered_headlines
                
                # Fallback to NewsAPI if hybrid fails (original logic)
                api_key = NEWS_API_KEY or "f3919401153f44d7ae3c9b7f8b610702"
                if not api_key:
                    return []
                
                # Use the time window for NewsAPI date range
                from_date = start_date.strftime('%Y-%m-%d')
                to_date = end_date.strftime('%Y-%m-%d')
                
                headlines_params = {
                    "apiKey": api_key,
                    "country": "us" if region == "us" else None,
                    "category": category if category != "all" else "general",
                    "pageSize": 50,
                    "from": from_date,
                    "to": to_date
                }
                headlines_params = {k: v for k, v in headlines_params.items() if v is not None}
                response = requests.get(
                    f"{NEWS_API_BASE_URL}/top-headlines",
                    params=headlines_params,
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    trending_topics = []
                    for article in articles[:20]:
                        title = article.get("title", "")
                        if title:
                            words = title.lower().split()
                            key_phrases = []
                            for i in range(len(words) - 1):
                                phrase = f"{words[i]} {words[i+1]}"
                                if len(phrase) > 5 and not any(word in phrase for word in ['the', 'and', 'for', 'with', 'this', 'that', 'will', 'has', 'are', 'was', 'were']):
                                    key_phrases.append(phrase)
                            trending_topics.append({
                                'title': title,
                                'url': article.get("url", ""),
                                'source': article.get("source", {}).get("name", "Unknown"),
                                'publishedAt': article.get("publishedAt", ""),
                                'key_phrases': key_phrases[:3],
                                'category': category,
                                'region': region
                            })
                    return trending_topics
                else:
                    print(f"❌ News API error: {response.status_code}")
                    return []
            except Exception as e:
                print(f"❌ News trends error: {e}")
                # Return fallback news data
                return [
                    {
                        'title': 'Technology trends in 2024',
                        'url': 'https://news.google.com/',
                        'source': 'News',
                        'publishedAt': datetime.now().isoformat(),
                        'key_phrases': ['technology', 'trends'],
                        'category': category,
                        'region': region
                    },
                    {
                        'title': 'Business innovation updates',
                        'url': 'https://news.google.com/',
                        'source': 'News',
                        'publishedAt': datetime.now().isoformat(),
                        'key_phrases': ['business', 'innovation'],
                        'category': category,
                        'region': region
                    }
                ]
        
        # Get trending topics from Reddit
        def get_reddit_trends():
            try:
                trending_topics = []
                
                # Get trending subreddits based on category
                subreddit_mapping = {
                    'technology': ['technology', 'programming', 'webdev', 'startups'],
                    'business': ['business', 'entrepreneur', 'investing', 'marketing'],
                    'health': ['health', 'fitness', 'nutrition', 'mentalhealth'],
                    'entertainment': ['entertainment', 'movies', 'music', 'gaming'],
                    'science': ['science', 'physics', 'chemistry', 'biology'],
                    'all': ['popular', 'all', 'trending']
                }
                
                subreddits = subreddit_mapping.get(category, ['popular'])
                
                for subreddit_name in subreddits[:3]:  # Limit to 3 subreddits
                    try:
                        subreddit = reddit.subreddit(subreddit_name)
                        
                        # Get hot posts
                        for post in subreddit.hot(limit=10):
                            if post.score > 100:  # Only high-scoring posts
                                # Check if post is within time window
                                post_date = datetime.fromtimestamp(post.created_utc)
                                if start_date <= post_date <= end_date:
                                    trending_topics.append({
                                        'title': post.title,
                                        'url': f"https://reddit.com{post.permalink}",
                                        'source': f"r/{subreddit_name}",
                                        'score': post.score,
                                        'comments': post.num_comments,
                                        'created_utc': post.created_utc,
                                        'category': category,
                                        'region': 'global'  # Reddit is global
                                    })
                    except Exception as e:
                        print(f"❌ Reddit subreddit error {subreddit_name}: {e}")
                        continue
                
                # If no Reddit trends found, add fallback data
                if not trending_topics:
                    trending_topics = [
                        {
                            'title': 'Popular discussion on Reddit',
                            'url': 'https://reddit.com/r/popular',
                            'source': 'r/popular',
                            'score': 1000,
                            'comments': 500,
                            'created_utc': time.time(),
                            'category': category,
                            'region': 'global'
                        }
                    ]
                
                return trending_topics
                
            except Exception as e:
                print(f"❌ Reddit trends error: {e}")
                # Return fallback Reddit data
                return [
                    {
                        'title': 'Reddit community discussions',
                        'url': 'https://reddit.com/',
                        'source': 'Reddit',
                        'score': 1000,
                        'comments': 500,
                        'created_utc': time.time(),
                        'category': category,
                        'region': 'global'
                    }
                ]
        
        # Get trending topics from Stack Overflow
        def get_stackoverflow_trends():
            try:
                # Get trending tags
                url = "https://api.stackexchange.com/2.3/tags"
                params = {
                    "order": "desc",
                    "sort": "popular",
                    "site": "stackoverflow",
                    "pagesize": 20
                }
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    tags = data.get("items", [])
                    
                    trending_topics = []
                    for tag in tags[:15]:
                        trending_topics.append({
                            'title': f"#{tag['name']}",
                            'url': f"https://stackoverflow.com/questions/tagged/{tag['name']}",
                            'source': 'Stack Overflow',
                            'count': tag['count'],
                            'category': 'technology',
                            'region': 'global'
                        })
                    
                    return trending_topics
                else:
                    return []
                    
            except Exception as e:
                print(f"❌ Stack Overflow trends error: {e}")
                # Return fallback Stack Overflow data
                return [
                    {
                        'title': '#javascript',
                        'url': 'https://stackoverflow.com/questions/tagged/javascript',
                        'source': 'Stack Overflow',
                        'count': 1000000,
                        'category': 'technology',
                        'region': 'global'
                    },
                    {
                        'title': '#python',
                        'url': 'https://stackoverflow.com/questions/tagged/python',
                        'source': 'Stack Overflow',
                        'count': 800000,
                        'category': 'technology',
                        'region': 'global'
                    }
                ]
        
        # Get trending topics from ComplaintsBoard
        def get_complaints_trends():
            try:
                # For complaints, we'll use the time window to filter recent complaints
                # Since we don't have real-time access, we'll simulate time-based filtering
                trending_topics = []
                
                # Simulate complaints data with timestamps
                complaints_data = [
                    {
                        'title': 'Customer service complaints trending',
                        'url': 'https://www.complaintsboard.com/',
                        'source': 'ComplaintsBoard',
                        'company': 'general',
                        'category': 'customer_service',
                        'region': 'global',
                        'timestamp': datetime.now().isoformat()
                    },
                    {
                        'title': 'Product quality issues reported',
                        'url': 'https://www.complaintsboard.com/',
                        'source': 'ComplaintsBoard',
                        'company': 'general',
                        'category': 'product_quality',
                        'region': 'global',
                        'timestamp': datetime.now().isoformat()
                    }
                ]
                
                # Filter by time window
                for complaint in complaints_data:
                    try:
                        complaint_date = datetime.fromisoformat(complaint['timestamp'].replace('Z', '+00:00'))
                        if start_date <= complaint_date <= end_date:
                            trending_topics.append(complaint)
                    except Exception as e:
                        print(f"Error parsing complaint date: {e}")
                        # Include if we can't parse the date
                        trending_topics.append(complaint)
                
                return trending_topics
                
            except Exception as e:
                print(f"❌ Complaints trends error: {e}")
                # Return fallback data
                return [
                    {
                        'title': 'Customer service complaints trending',
                        'url': 'https://www.complaintsboard.com/',
                        'source': 'ComplaintsBoard',
                        'company': 'general',
                        'category': 'customer_service',
                        'region': 'global'
                    }
                ]
        
        # Run all trend gathering in parallel with timeout
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                news_future = executor.submit(get_news_trends)
                reddit_future = executor.submit(get_reddit_trends)
                stackoverflow_future = executor.submit(get_stackoverflow_trends)
                complaints_future = executor.submit(get_complaints_trends)
                
                # Collect results with timeout
                trends_data['news_trends'] = news_future.result(timeout=30)
                trends_data['reddit_trends'] = reddit_future.result(timeout=30)
                trends_data['stackoverflow_trends'] = stackoverflow_future.result(timeout=30)
                trends_data['complaints_trends'] = complaints_future.result(timeout=30)
        except Exception as e:
            print(f"❌ Thread execution error: {e}")
            # Continue with empty results if threading fails
        
        # Combine all trends for global analysis
        all_trends = []
        all_trends.extend(trends_data['news_trends'])
        all_trends.extend(trends_data['reddit_trends'])
        all_trends.extend(trends_data['stackoverflow_trends'])
        all_trends.extend(trends_data['complaints_trends'])
        
        # Extract keywords and phrases for trend analysis
        all_keywords = []
        for trend in all_trends:
            title = trend.get('title', '').lower()
            # Extract meaningful keywords
            words = re.findall(r'\b[a-z]{4,}\b', title)
            all_keywords.extend(words)
        
        # Get most common keywords
        keyword_counts = Counter(all_keywords)
        trends_data['hot_keywords'] = [
            {'word': word, 'count': count, 'trend': 'rising' if count > 5 else 'stable'}
            for word, count in keyword_counts.most_common(20)
        ]
        
        # Categorize trends by region and category
        for trend in all_trends:
            trend_region = trend.get('region', 'global')
            trend_category = trend.get('category', 'general')
            
            if trend_region not in trends_data['regional_trends']:
                trends_data['regional_trends'][trend_region] = []
            trends_data['regional_trends'][trend_region].append(trend)
            
            if trend_category not in trends_data['category_trends']:
                trends_data['category_trends'][trend_category] = []
            trends_data['category_trends'][trend_category].append(trend)
        
        # Generate AI insights about trends (with fallback)
        if all_trends:
            try:
                insights_prompt = f"""
You are a global trend analyst specializing in real-time market intelligence. Analyze the following trending topics from multiple sources (News, Reddit, Stack Overflow, ComplaintsBoard) and provide insights about emerging patterns, opportunities, and market shifts.

Time Window: {time_window}
Region: {region}
Category: {category}

Trending Topics:
"""
                
                for i, trend in enumerate(all_trends[:30]):  # Limit to 30 for analysis
                    insights_prompt += f"\n{i+1}. {trend.get('title', '')} (Source: {trend.get('source', 'Unknown')})"
                
                insights_prompt += f"""

Analyze these trends and provide:

1. **Emerging Patterns**: What themes or patterns do you see across these trends?
2. **Market Opportunities**: What startup or business opportunities are revealed?
3. **Regional Insights**: How do trends differ by region ({region})?
4. **Category Analysis**: What's happening in the {category} space?
5. **Predictions**: What might be trending next based on these patterns?

Return your analysis in a clear, actionable format with specific insights and opportunities.
"""
                
                insights_response = groq_generate_content_with_fallback(insights_prompt, max_tokens=2000, temperature=0.7)
                trends_data['ai_insights'] = insights_response.strip()
                
            except Exception as e:
                print(f"❌ AI insights error: {e}")
                trends_data['ai_insights'] = "Unable to generate AI insights at this time. Please try again later."
        else:
            trends_data['ai_insights'] = "No trending data available to analyze at this time."
        
        # Calculate statistics
        total_trends = len(all_trends)
        sources_active = sum(1 for source in ['news_trends', 'reddit_trends', 'stackoverflow_trends', 'complaints_trends'] 
                           if trends_data[source])
        
        return jsonify({
            "region": region,
            "category": category,
            "time_window": time_window,
            "trends_data": trends_data,
            "total_trends": total_trends,
            "sources_active": sources_active,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Live trends API error: {e}")
        import traceback
        traceback.print_exc()
        # Return a graceful error response instead of 500
        return jsonify({
            "error": "Unable to load trends at this time. Please try again later.",
            "trends_data": {
                'news_trends': [],
                'reddit_trends': [],
                'stackoverflow_trends': [],
                'complaints_trends': [],
                'hot_keywords': [],
                'ai_insights': "Service temporarily unavailable. Please try again later."
            },
            "total_trends": 0,
            "sources_active": 0,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/trending-keywords', methods=['GET'])
@login_required
def trending_keywords_api():
    """Get real-time trending keywords across all sources"""
    try:
        # Get trending keywords from multiple sources
        keywords = []
        
        # News API trending keywords
        try:
            api_key = NEWS_API_KEY or "f3919401153f44d7ae3c9b7f8b610702"
            if api_key:
                from_date, to_date = get_newsapi_date_range()
                
                # Get top headlines
                response = requests.get(
                    f"{NEWS_API_BASE_URL}/top-headlines",
                    params={
                        "apiKey": api_key,
                        "country": "us",
                        "pageSize": 20
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    
                    for article in articles:
                        title = article.get("title", "")
                        if title:
                            words = re.findall(r'\b[a-z]{4,}\b', title.lower())
                            keywords.extend(words)
        except Exception as e:
            print(f"❌ News keywords error: {e}")
        
        # Reddit trending keywords
        try:
            for subreddit_name in ['popular', 'technology', 'business']:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    for post in subreddit.hot(limit=5):
                        title = post.title.lower()
                        words = re.findall(r'\b[a-z]{4,}\b', title)
                        keywords.extend(words)
                except:
                    continue
        except Exception as e:
            print(f"❌ Reddit keywords error: {e}")
        
        # Count and return top keywords
        keyword_counts = Counter(keywords)
        trending_keywords = [
            {
                'word': word,
                'count': count,
                'trend': 'rising' if count > 3 else 'stable',
                'source': 'multiple'
            }
            for word, count in keyword_counts.most_common(50)
            if word not in STOPWORDS and len(word) > 3
        ]
        
        return jsonify({
            "trending_keywords": trending_keywords,
            "total_sources": 2,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Trending keywords error: {e}")
        return jsonify({"error": str(e)}), 500
    


@app.route('/radargpt-steps', methods=['POST'])
@login_required
def radargpt_steps_api():
    """API endpoint for RadarGPT step-by-step analysis"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '')
        
        if not keyword:
            return jsonify({"error": "Keyword is required"}), 400
        
        def generate_steps():
            # Step 1: Initial analysis
            yield f"data: {json.dumps({'step': 1, 'title': 'Analyzing keyword', 'message': f'Starting analysis for: {keyword}'})}\n\n"
            time.sleep(1)
            
            # Step 2: Multi-source search
            yield f"data: {json.dumps({'step': 2, 'title': 'Searching multiple sources', 'message': 'Gathering data from Reddit, Stack Overflow, and news sources...'})}\n\n"
            time.sleep(2)
            
            # Step 3: AI analysis
            yield f"data: {json.dumps({'step': 3, 'title': 'AI Analysis', 'message': 'Processing data with AI to identify patterns and insights...'})}\n\n"
            time.sleep(2)
            
            # Step 4: Generate insights
            yield f"data: {json.dumps({'step': 4, 'title': 'Generating insights', 'message': 'Creating actionable insights and recommendations...'})}\n\n"
            time.sleep(1)
            
            # Step 5: Complete
            yield f"data: {json.dumps({'step': 5, 'title': 'Analysis complete', 'message': 'Your RadarGPT analysis is ready!'})}\n\n"
        
        return Response(generate_steps(), mimetype='text/plain')
        
    except Exception as e:
        print(f"❌ RadarGPT steps API error: {e}")
        return jsonify({"error": "Failed to generate steps"}), 500

@app.route('/usage-dashboard')
@login_required
def usage_dashboard():
    """Display usage dashboard for the current user"""
    user_id = current_user.id

    # Get user's current plan from UserSubscription
    subscription = UserSubscription.query.filter_by(user_id=user_id, status='active').order_by(UserSubscription.created_at.desc()).first()
    current_plan = subscription.plan_type if subscription else 'free'

    # Get usage statistics
    usage_stats = get_user_usage_stats(user_id)

    # Get recent activity
    recent_activity = get_recent_activity(user_id)

    # Get plan limits
    plan_limits = get_plan_limits(current_plan)

    return render_template('usage_dashboard.html', 
                         user=current_user,
                         current_plan=current_plan,
                         usage_stats=usage_stats,
                         recent_activity=recent_activity,
                         plan_limits=plan_limits)

@app.route('/api/usage-stats')
@login_required
def usage_stats_api():
    """API endpoint for user usage statistics"""
    try:
        user_id = current_user.id
        
        # Get current subscription
        subscription = UserSubscription.query.filter_by(
            user_id=user_id, 
            status='active'
        ).order_by(UserSubscription.created_at.desc()).first()
        
        if not subscription:
            # Create default free subscription
            subscription = UserSubscription(
                user_id=user_id,
                plan_type='free',
                status='active'
            )
            db.session.add(subscription)
            db.session.commit()
        
        # Get current month usage
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get usage by module for current month
        usage_data = db.session.query(
            UserUsage.module,
            func.sum(UserUsage.usage_count).label('total_usage')
        ).filter(
            UserUsage.user_id == user_id,
            UserUsage.date >= current_month.date()
        ).group_by(UserUsage.module).all()
        
        # Convert to dictionary
        monthly_usage = {row.module: row.total_usage for row in usage_data}
        
        # Get plan limits
        plan_limits = {
            'free': {
                'radargpt': 10,
                'verticals': 2,
                'insights': 5,
                'trends': 10,
                'exports': 0
            },
            'pro': {
                'radargpt': float('inf'),
                'verticals': float('inf'),
                'insights': float('inf'),
                'trends': float('inf'),
                'exports': float('inf')
            },
            'annual': {
                'radargpt': float('inf'),
                'verticals': float('inf'),
                'insights': float('inf'),
                'trends': float('inf'),
                'exports': float('inf')
            }
        }
        
        current_limits = plan_limits.get(subscription.plan_type, plan_limits['free'])
        
        # Calculate usage percentages
        usage_percentages = {}
        for module, limit in current_limits.items():
            current_usage = monthly_usage.get(module, 0)
            if limit == float('inf'):
                usage_percentages[module] = 0  # Unlimited
            else:
                usage_percentages[module] = min(100, (current_usage / limit) * 100) if limit > 0 else 0
        
        # Get daily usage for the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_usage = db.session.query(
            UserUsage.date,
            func.sum(UserUsage.usage_count).label('daily_total')
        ).filter(
            UserUsage.user_id == user_id,
            UserUsage.date >= thirty_days_ago.date()
        ).group_by(UserUsage.date).order_by(UserUsage.date).all()
        
        daily_data = [{'date': str(row.date), 'usage': row.daily_total} for row in daily_usage]
        
        # Get recent activity
        recent_activity = db.session.query(UserUsage).filter(
            UserUsage.user_id == user_id
        ).order_by(UserUsage.created_at.desc()).limit(10).all()
        
        activity_data = []
        for activity in recent_activity:
            activity_data.append({
                'module': activity.module,
                'action': activity.action,
                'date': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                'usage_count': activity.usage_count
            })
        
        return jsonify({
            'subscription': {
                'plan_type': subscription.plan_type,
                'status': subscription.status,
                'start_date': subscription.start_date.strftime('%Y-%m-%d'),
                'end_date': subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else None
            },
            'monthly_usage': monthly_usage,
            'usage_percentages': usage_percentages,
            'plan_limits': current_limits,
            'daily_usage': daily_data,
            'recent_activity': activity_data
        })
        
    except Exception as e:
        print(f"❌ Usage stats API error: {e}")
        return jsonify({"error": "Failed to fetch usage statistics"}), 500

@app.route('/api/track-usage', methods=['POST'])
@login_required
def track_usage_api():
    """API endpoint to track user usage"""
    try:
        data = request.get_json()
        module = data.get('module')
        action = data.get('action', 'general')
        usage_count = data.get('usage_count', 1)
        
        if not module:
            return jsonify({"error": "Module is required"}), 400
        
        # Check if usage already exists for today
        today = datetime.now().date()
        existing_usage = UserUsage.query.filter_by(
            user_id=current_user.id,
            module=module,
            action=action,
            date=today
        ).first()
        
        if existing_usage:
            existing_usage.usage_count += usage_count
        else:
            new_usage = UserUsage(
                user_id=current_user.id,
                module=module,
                action=action,
                usage_count=usage_count,
                date=today
            )
            db.session.add(new_usage)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Usage tracked successfully"})
        
    except Exception as e:
        print(f"❌ Track usage API error: {e}")
        return jsonify({"error": "Failed to track usage"}), 500

@app.route('/api/upgrade-plan', methods=['POST'])
@login_required
def upgrade_plan_api():
    """API endpoint to upgrade user plan"""
    try:
        data = request.get_json()
        plan_type = data.get('plan_type')
        
        if not plan_type or plan_type not in ['free', 'pro', 'annual']:
            return jsonify({"error": "Invalid plan type"}), 400
        
        # Deactivate current subscription
        current_subscription = UserSubscription.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).first()
        
        if current_subscription:
            current_subscription.status = 'cancelled'
            current_subscription.end_date = datetime.now()
        
        # Create new subscription
        new_subscription = UserSubscription(
            user_id=current_user.id,
            plan_type=plan_type,
            status='active',
            start_date=datetime.now()
        )
        
        if plan_type in ['pro', 'annual']:
            # Set end date for trial (7 days)
            new_subscription.end_date = datetime.now() + timedelta(days=7)
        
        db.session.add(new_subscription)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Successfully upgraded to {plan_type} plan",
            "plan_type": plan_type
        })
        
    except Exception as e:
        print(f"❌ Upgrade plan API error: {e}")
        return jsonify({"error": "Failed to upgrade plan"}), 500

# Helper functions for usage dashboard
def get_user_usage_stats(user_id):
    """Get comprehensive usage statistics for a user"""
    try:
        # Get current subscription
        subscription = UserSubscription.query.filter_by(
            user_id=user_id, 
            status='active'
        ).order_by(UserSubscription.created_at.desc()).first()
        
        if not subscription:
            subscription = UserSubscription(
                user_id=user_id,
                plan_type='free',
                status='active'
            )
            db.session.add(subscription)
            db.session.commit()
        
        # Get current month usage
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get usage by module for current month
        usage_data = db.session.query(
            UserUsage.module,
            func.sum(UserUsage.usage_count).label('total_usage')
        ).filter(
            UserUsage.user_id == user_id,
            UserUsage.date >= current_month.date()
        ).group_by(UserUsage.module).all()
        
        monthly_usage = {row.module: row.total_usage for row in usage_data}
        
        # Get plan limits
        plan_limits = {
            'free': {
                'radargpt': 10,
                'verticals': 2,
                'insights': 5,
                'trends': 10,
                'exports': 0
            },
            'pro': {
                'radargpt': float('inf'),
                'verticals': float('inf'),
                'insights': float('inf'),
                'trends': float('inf'),
                'exports': float('inf')
            },
            'annual': {
                'radargpt': float('inf'),
                'verticals': float('inf'),
                'insights': float('inf'),
                'trends': float('inf'),
                'exports': float('inf')
            }
        }
        
        current_limits = plan_limits.get(subscription.plan_type, plan_limits['free'])
        
        # Calculate usage percentages
        usage_percentages = {}
        for module, limit in current_limits.items():
            current_usage = monthly_usage.get(module, 0)
            if limit == float('inf'):
                usage_percentages[module] = 0  # Unlimited
            else:
                usage_percentages[module] = min(100, (current_usage / limit) * 100) if limit > 0 else 0
        
        # Get daily usage for the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_usage = db.session.query(
            UserUsage.date,
            func.sum(UserUsage.usage_count).label('daily_total')
        ).filter(
            UserUsage.user_id == user_id,
            UserUsage.date >= thirty_days_ago.date()
        ).group_by(UserUsage.date).order_by(UserUsage.date).all()
        
        daily_data = [{'date': str(row.date), 'usage': row.daily_total} for row in daily_usage]
        
        return {
            'subscription': {
                'plan_type': subscription.plan_type,
                'status': subscription.status,
                'start_date': subscription.start_date.strftime('%Y-%m-%d'),
                'end_date': subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else None
            },
            'monthly_usage': monthly_usage,
            'usage_percentages': usage_percentages,
            'plan_limits': current_limits,
            'daily_usage': daily_data
        }
        
    except Exception as e:
        print(f"❌ Get user usage stats error: {e}")
        return {}

def get_recent_activity(user_id, limit=10):
    """Get recent user activity"""
    try:
        recent_activity = db.session.query(UserUsage).filter(
            UserUsage.user_id == user_id
        ).order_by(UserUsage.created_at.desc()).limit(limit).all()
        
        activity_data = []
        for activity in recent_activity:
            activity_data.append({
                'module': activity.module,
                'action': activity.action,
                'date': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                'usage_count': activity.usage_count
            })
        
        return activity_data
        
    except Exception as e:
        print(f"❌ Get recent activity error: {e}")
        return []

def get_plan_limits(plan_type):
    """Get plan limits for a given plan type"""
    plan_limits = {
        'free': {
            'radargpt': 10,
            'verticals': 2,
            'insights': 5,
            'trends': 10,
            'exports': 0
        },
        'pro': {
            'radargpt': float('inf'),
            'verticals': float('inf'),
            'insights': float('inf'),
            'trends': float('inf'),
            'exports': float('inf')
        },
        'annual': {
            'radargpt': float('inf'),
            'verticals': float('inf'),
            'insights': float('inf'),
            'trends': float('inf'),
            'exports': float('inf')
        }
    }
    
    return plan_limits.get(plan_type, plan_limits['free'])

import stripe
from flask import redirect


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': app.config['STRIPE_PRICE_PRO'],
                'quantity': 1,
            }],
            mode='subscription',
            customer_email=current_user.email,  # Make sure User model has email
            success_url=app.config['DOMAIN'] + '/upgrade-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=app.config['DOMAIN'] + '/upgrade-cancelled',
            metadata={'user_id': current_user.id, 'plan': 'pro'}
        )
        return redirect(checkout_session.url)
    except Exception as e:
        return str(e), 500

@app.route('/upgrade-success')
@login_required
def upgrade_success():
    return "Upgrade successful! Your Pro plan is now active."

@app.route('/upgrade-cancelled')
@login_required
def upgrade_cancelled():
    return "Upgrade cancelled. You have not been charged."

import razorpay

razorpay_client = razorpay.Client(auth=(app.config["RAZORPAY_KEY_ID"], app.config["RAZORPAY_KEY_SECRET"]))

@app.route('/create-razorpay-order', methods=['POST'])
@login_required
def create_razorpay_order():
    amount = 49900  # Amount in paise (₹499.00)
    currency = "INR"
    payment_capture = 1
    notes = {'user_id': str(current_user.id), 'plan': 'pro'}

    order = razorpay_client.order.create({
        'amount': amount,
        'currency': currency,
        'payment_capture': payment_capture,
        'notes': notes
    })
    return jsonify({
        'order_id': order['id'],
        'razorpay_key_id': app.config["RAZORPAY_KEY_ID"],
        'amount': amount,
        'currency': currency,
        'user_email': current_user.email
    })

@app.route('/razorpay-success')
@login_required
def razorpay_success():
    # You can verify payment here using Razorpay API if needed
    # And update the user's plan in your DB
    return "Payment successful! Your Pro plan is now active."

from flask import render_template



@app.template_filter('datetimeformat')
def datetimeformat(value):
    import datetime
    return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M')

@app.route('/create-paypal-order', methods=['POST'])
@login_required
def create_paypal_order():
    # Create PayPal order
    auth = (app.config['PAYPAL_CLIENT_ID'], app.config['PAYPAL_CLIENT_SECRET'])
    headers = {'Content-Type': 'application/json'}
    data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "INR", "value": "499.00"},
            "custom_id": str(current_user.id),
            "description": "Pro Plan"
        }],
        "application_context": {
            "return_url": app.config['DOMAIN'] + "/paypal-success",
            "cancel_url": app.config['DOMAIN'] + "/paypal-cancelled"
        }
    }
    # Get access token
    r = requests.post('https://api-m.sandbox.paypal.com/v1/oauth2/token', auth=auth, data={'grant_type': 'client_credentials'})
    access_token = r.json()['access_token']
    # Create order
    r = requests.post('https://api-m.sandbox.paypal.com/v2/checkout/orders', headers={**headers, 'Authorization': f'Bearer {access_token}'}, json=data)
    order = r.json()
    return order

@app.route('/paypal-success')
@login_required
def paypal_success():
    # Handle PayPal success (mark user as pro, etc.)
    return "Payment successful! Your Pro plan is now active."

@app.route('/paypal-cancelled')
@login_required
def paypal_cancelled():
    return "Payment cancelled."

# Update admin dashboard to show PayPal and Razorpay payments only
@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.email != 'knagasamanvitha@email.com':
        return "Unauthorized", 403
    total_users = User.query.count()
    pro_subs = UserSubscription.query.filter_by(plan='pro').all()
    yearly_subs = UserSubscription.query.filter_by(plan='pro_yearly').all()
    pro_users = len(pro_subs)
    yearly_users = len(yearly_subs)
    free_users = total_users - pro_users - yearly_users
    # Razorpay payments
    import razorpay
    razorpay_client = razorpay.Client(auth=(app.config["RAZORPAY_KEY_ID"], app.config["RAZORPAY_KEY_SECRET"]))
    razorpay_payments = razorpay_client.payment.all({'count': 100})
    razorpay_list = []
    razorpay_total = 0
    for p in razorpay_payments['items']:
        if p['status'] == 'captured':
            amt = int(p['amount']) / 100.0
            razorpay_total += amt
            razorpay_list.append({
                'id': p['id'],
                'email': p.get('email', ''),
                'amount': amt,
                'method': 'Razorpay',
                'plan': p['notes'].get('plan', '') if 'notes' in p else '',
                'created_at': p['created_at']
            })
    # PayPal payments (fetch from PayPal API)
    paypal_total = 0
    paypal_list = []
    try:
        # Get access token
        auth = (app.config['PAYPAL_CLIENT_ID'], app.config['PAYPAL_CLIENT_SECRET'])
        r = requests.post('https://api-m.sandbox.paypal.com/v1/oauth2/token', auth=auth, data={'grant_type': 'client_credentials'})
        access_token = r.json()['access_token']
        # List transactions (for demo, fetch last 20 orders)
        r = requests.get('https://api-m.sandbox.paypal.com/v2/checkout/orders', headers={'Authorization': f'Bearer {access_token}'})
        if r.status_code == 200:
            for o in r.json().get('orders', []):
                amt = float(o['purchase_units'][0]['amount']['value'])
                paypal_total += amt
                paypal_list.append({
                    'id': o['id'],
                    'email': o.get('payer', {}).get('email_address', ''),
                    'amount': amt,
                    'method': 'PayPal',
                    'plan': o['purchase_units'][0].get('description', ''),
                    'created_at': o['create_time']
                })
    except Exception as e:
        print('PayPal error:', e)
    all_payments = sorted(razorpay_list + paypal_list, key=lambda x: x['created_at'], reverse=True)
    total_payments = razorpay_total + paypal_total
    return render_template('admin_dashboard.html',
        total_users=total_users,
        pro_users=pro_users,
        yearly_users=yearly_users,
        free_users=free_users,
        total_payments=total_payments,
        payment_list=all_payments
    )

if __name__ == "__main__":
    print("🧪 Testing News API...")
    test_news_api()
    
    with app.app_context():
        db.create_all()
    app.run(debug=True)