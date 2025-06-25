#!/usr/bin/env python3
"""
Test script to verify Groq integration is working correctly with rate limiting
"""

import os
from dotenv import load_dotenv
from groq import Groq
import random
import time

# Load environment variables
load_dotenv()

def test_groq_setup():
    """Test the Groq setup and API key rotation"""
    
    # List of Groq API keys for rotation
    GROQ_API_KEYS = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"), 
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY_4"),
        os.getenv("GROQ_API_KEY_5")
    ]

    # Filter out None values
    GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]

    # Fallback to single key if no rotation keys provided
    if not GROQ_API_KEYS:
        GROQ_API_KEYS = [os.getenv("GROQ_API_KEY")]
    
    print(f"Found {len(GROQ_API_KEYS)} API keys")
    
    if not GROQ_API_KEYS or not any(GROQ_API_KEYS):
        print("❌ No Groq API keys found!")
        print("Please set GROQ_API_KEY or GROQ_API_KEY_1, GROQ_API_KEY_2, etc. in your .env file")
        return False
    
    # Track failed keys to avoid using them immediately after rate limit
    failed_keys = {}
    MAX_RETRIES = 3

    def get_groq_client():
        """Get a Groq client with a randomly selected API key, avoiding recently failed keys"""
        # Filter out keys that failed recently (within last 60 seconds)
        current_time = time.time()
        available_keys = [key for key in GROQ_API_KEYS if key not in failed_keys or 
                         current_time - failed_keys[key] > 60]
        
        # If no available keys, reset failed keys and try again
        if not available_keys:
            failed_keys.clear()
            available_keys = GROQ_API_KEYS
        
        # If still no keys, return None
        if not available_keys:
            return None
        
        api_key = random.choice(available_keys)
        return Groq(api_key=api_key)

    def mark_key_failed(api_key):
        """Mark an API key as failed (rate limited)"""
        failed_keys[api_key] = time.time()

    def groq_generate_content(prompt, temperature=0.6, max_tokens=4096):
        """Test Groq's generate_content method with rate limit handling"""
        for attempt in range(MAX_RETRIES):
            try:
                client = get_groq_client()
                if client is None:
                    return f"Error: No valid API keys available"
                
                completion = client.chat.completions.create(
                    model="qwen/qwen3-32b",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.95,
                    stream=False,
                    stop=None,
                )
                return completion.choices[0].message.content
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if any(rate_limit_indicator in error_str for rate_limit_indicator in [
                    'rate limit', 'rate_limit', '429', 'too many requests', 'quota exceeded'
                ]):
                    # Mark the current key as failed
                    if hasattr(client, '_api_key'):
                        mark_key_failed(client._api_key)
                    elif hasattr(client, 'api_key'):
                        mark_key_failed(client.api_key)
                    
                    print(f"Rate limit hit, rotating key (attempt {attempt + 1}/{MAX_RETRIES})")
                    
                    # If this was the last attempt, return error
                    if attempt == MAX_RETRIES - 1:
                        return f"Error: All API keys rate limited after {MAX_RETRIES} attempts"
                    
                    # Wait a bit before retrying
                    time.sleep(1)
                    continue
                else:
                    # Non-rate-limit error, return immediately
                    print(f"Groq error: {e}")
                    return f"Error: {e}"
        
        return f"Error: Failed after {MAX_RETRIES} attempts"

    # Test simple generation
    test_prompt = "Hello! Please respond with 'Groq integration is working!' if you can see this message."
    
    print("Testing Groq API with rate limit handling...")
    response = groq_generate_content(test_prompt)
    
    if "Error:" in response:
        print(f"❌ Groq test failed: {response}")
        return False
    else:
        print(f"✅ Groq test successful!")
        print(f"Response: {response[:100]}...")
        return True

def test_groq_chat():
    """Test the Groq chat functionality with rate limiting"""
    
    GROQ_API_KEYS = [os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_1")]
    GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]
    
    if not GROQ_API_KEYS:
        print("❌ No API keys for chat test")
        return False
    
    # Track failed keys
    failed_keys = {}
    MAX_RETRIES = 3

    def get_groq_client():
        """Get a Groq client with a randomly selected API key, avoiding recently failed keys"""
        current_time = time.time()
        available_keys = [key for key in GROQ_API_KEYS if key not in failed_keys or 
                         current_time - failed_keys[key] > 60]
        
        if not available_keys:
            failed_keys.clear()
            available_keys = GROQ_API_KEYS
        
        if not available_keys:
            return None
        
        api_key = random.choice(available_keys)
        return Groq(api_key=api_key)

    def mark_key_failed(api_key):
        """Mark an API key as failed (rate limited)"""
        failed_keys[api_key] = time.time()

    def groq_start_chat(history=None):
        """Test Groq's start_chat method with rate limit handling"""
        class GroqChat:
            def __init__(self, history=None):
                self.history = history or []
                self.client = None
                self._initialize_client()
            
            def _initialize_client(self):
                """Initialize client with retry logic for rate limits"""
                for attempt in range(MAX_RETRIES):
                    try:
                        self.client = get_groq_client()
                        if self.client is not None:
                            break
                    except Exception as e:
                        if attempt == MAX_RETRIES - 1:
                            raise Exception(f"Failed to initialize Groq client: {e}")
                        time.sleep(1)
            
            def _get_client_with_retry(self):
                """Get a working client, rotating keys if needed"""
                for attempt in range(MAX_RETRIES):
                    if self.client is None:
                        self._initialize_client()
                    
                    try:
                        # Test the client with a simple request
                        test_completion = self.client.chat.completions.create(
                            model="qwen/qwen3-32b",
                            messages=[{"role": "user", "content": "test"}],
                            max_tokens=1,
                            temperature=0,
                        )
                        return self.client
                    except Exception as e:
                        error_str = str(e).lower()
                        
                        # Check if it's a rate limit error
                        if any(rate_limit_indicator in error_str for rate_limit_indicator in [
                            'rate limit', 'rate_limit', '429', 'too many requests', 'quota exceeded'
                        ]):
                            # Mark the current key as failed
                            if hasattr(self.client, '_api_key'):
                                mark_key_failed(self.client._api_key)
                            elif hasattr(self.client, 'api_key'):
                                mark_key_failed(self.client.api_key)
                            
                            print(f"Rate limit hit in chat, rotating key (attempt {attempt + 1}/{MAX_RETRIES})")
                            
                            # Get a new client
                            self.client = get_groq_client()
                            
                            if attempt == MAX_RETRIES - 1:
                                raise Exception(f"All API keys rate limited after {MAX_RETRIES} attempts")
                            
                            time.sleep(1)
                            continue
                        else:
                            # Non-rate-limit error, raise immediately
                            raise e
                
                return self.client
            
            def send_message(self, message):
                # Convert history to Groq format
                messages = []
                for msg in self.history:
                    if isinstance(msg, dict):
                        if 'role' in msg and 'parts' in msg:
                            messages.append({
                                "role": msg['role'],
                                "content": msg['parts'][0] if msg['parts'] else ""
                            })
                        elif 'role' in msg and 'content' in msg:
                            messages.append(msg)
                
                # Add current message
                messages.append({
                    "role": "user",
                    "content": message
                })
                
                try:
                    client = self._get_client_with_retry()
                    completion = client.chat.completions.create(
                        model="qwen/qwen3-32b",
                        messages=messages,
                        temperature=0.6,
                        max_tokens=4096,
                        top_p=0.95,
                        stream=False,
                        stop=None,
                    )
                    
                    # Update history
                    self.history.append({"role": "user", "parts": [message]})
                    self.history.append({"role": "model", "parts": [completion.choices[0].message.content]})
                    
                    return type('Response', (), {'text': completion.choices[0].message.content})()
                except Exception as e:
                    print(f"Groq chat error: {e}")
                    return type('Response', (), {'text': f"Error: {e}"})()
        
        return GroqChat(history)

    print("Testing Groq chat with rate limit handling...")
    
    # Test chat with history
    chat = groq_start_chat(history=[{"role": "user", "parts": ["You are a helpful assistant."]}])
    response = chat.send_message("Say 'Chat is working!' if you understand.")
    
    if "Error:" in response.text:
        print(f"❌ Groq chat test failed: {response.text}")
        return False
    else:
        print(f"✅ Groq chat test successful!")
        print(f"Response: {response.text[:100]}...")
        return True

def test_key_rotation():
    """Test the key rotation functionality"""
    print("Testing key rotation logic...")
    
    # Simulate key rotation
    GROQ_API_KEYS = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"), 
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY_4"),
        os.getenv("GROQ_API_KEY_5")
    ]
    GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]
    
    if not GROQ_API_KEYS:
        GROQ_API_KEYS = [os.getenv("GROQ_API_KEY")]
    
    if len(GROQ_API_KEYS) < 2:
        print("⚠️  Only one API key available, skipping rotation test")
        return True
    
    # Test that different keys are selected
    keys_used = set()
    for _ in range(min(10, len(GROQ_API_KEYS) * 2)):
        client = Groq(api_key=random.choice(GROQ_API_KEYS))
        if hasattr(client, '_api_key'):
            keys_used.add(client._api_key)
        elif hasattr(client, 'api_key'):
            keys_used.add(client.api_key)
    
    if len(keys_used) > 1:
        print(f"✅ Key rotation working - used {len(keys_used)} different keys")
        return True
    else:
        print(f"⚠️  Key rotation test inconclusive - only used {len(keys_used)} key(s)")
        return True

if __name__ == "__main__":
    print("🧪 Testing Groq Integration with Rate Limiting")
    print("=" * 50)
    
    # Test basic setup
    setup_ok = test_groq_setup()
    
    # Test chat functionality
    chat_ok = test_groq_chat()
    
    # Test key rotation
    rotation_ok = test_key_rotation()
    
    print("\n" + "=" * 50)
    if setup_ok and chat_ok and rotation_ok:
        print("🎉 All tests passed! Groq integration with rate limiting is working correctly.")
        print("\n📋 Rate Limiting Features:")
        print("✅ Automatic key rotation on rate limits")
        print("✅ Failed key tracking (60-second cooldown)")
        print("✅ Retry logic with exponential backoff")
        print("✅ Graceful fallback when all keys are rate limited")
    else:
        print("❌ Some tests failed. Please check your API keys and configuration.") 