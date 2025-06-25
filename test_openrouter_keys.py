#!/usr/bin/env python3
"""
OpenRouter API Key Testing Script
Tests all OpenRouter API keys and reports their status
"""

import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openrouter_key(api_key, key_name):
    """Test a single OpenRouter API key"""
    if not api_key:
        return {
            "key_name": key_name,
            "status": "NOT_SET",
            "error": "API key not set in environment",
            "response_time": None
        }
    
    if not api_key.startswith('sk-'):
        return {
            "key_name": key_name,
            "status": "INVALID_FORMAT",
            "error": "API key doesn't start with 'sk-'",
            "response_time": None
        }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "RadarGPT"
    }
    
    data = {
        "model": "deepseek-ai/deepseek-coder-33b-instruct",
        "messages": [
            {
                "role": "user",
                "content": "Respond with 'Hello from OpenRouter' and nothing else."
            }
        ],
        "temperature": 0.7,
        "max_tokens": 50,
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
        
        if response.status_code == 200:
            try:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return {
                    "key_name": key_name,
                    "status": "WORKING",
                    "response_time": f"{response_time}ms",
                    "content": content.strip(),
                    "model_used": result.get("model", "unknown"),
                    "usage": result.get("usage", {})
                }
            except (KeyError, json.JSONDecodeError) as e:
                return {
                    "key_name": key_name,
                    "status": "INVALID_RESPONSE",
                    "error": f"Could not parse response: {str(e)}",
                    "response_time": f"{response_time}ms",
                    "raw_response": response.text[:200]
                }
        
        elif response.status_code == 401:
            return {
                "key_name": key_name,
                "status": "INVALID_KEY",
                "error": "401 Unauthorized - Invalid API key",
                "response_time": f"{response_time}ms"
            }
        
        elif response.status_code == 429:
            return {
                "key_name": key_name,
                "status": "RATE_LIMITED",
                "error": "429 Too Many Requests - Rate limited",
                "response_time": f"{response_time}ms"
            }
        
        elif response.status_code == 400:
            print(response.text)
            return {
                "key_name": key_name,
                "status": "BAD_REQUEST",
                "error": f"400 Bad Request: {response.text[:200]}",
                "response_time": f"{response_time}ms"
            }
        
        else:
            return {
                "key_name": key_name,
                "status": "ERROR",
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "response_time": f"{response_time}ms"
            }
    
    except requests.exceptions.Timeout:
        return {
            "key_name": key_name,
            "status": "TIMEOUT",
            "error": "Request timed out after 30 seconds",
            "response_time": None
        }
    
    except requests.exceptions.ConnectionError:
        return {
            "key_name": key_name,
            "status": "CONNECTION_ERROR",
            "error": "Connection error - check your internet",
            "response_time": None
        }
    
    except Exception as e:
        return {
            "key_name": key_name,
            "status": "EXCEPTION",
            "error": f"Unexpected error: {str(e)}",
            "response_time": None
        }

def test_all_openrouter_keys():
    """Test all OpenRouter API keys"""
    print("🔍 Testing OpenRouter API Keys")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test keys from OPENROUTER_API_KEY_1 to OPENROUTER_API_KEY_10
    results = []
    working_keys = 0
    total_keys = 0
    
    for i in range(1, 11):
        key_name = f"OPENROUTER_API_KEY_{i}"
        api_key = os.getenv(key_name)
        
        print(f"Testing {key_name}...", end=" ")
        result = test_openrouter_key(api_key, key_name)
        results.append(result)
        
        if result["status"] == "WORKING":
            print("✅ WORKING")
            working_keys += 1
        elif result["status"] == "NOT_SET":
            print("❌ NOT SET")
        else:
            print(f"❌ {result['status']}")
        
        total_keys += 1
        
        # Small delay between requests to be nice to the API
        time.sleep(0.5)
    
    print()
    print("=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Total keys tested: {total_keys}")
    print(f"Working keys: {working_keys}")
    print(f"Success rate: {(working_keys/total_keys)*100:.1f}%")
    print()
    
    print("📋 DETAILED RESULTS")
    print("=" * 50)
    
    for result in results:
        print(f"\n🔑 {result['key_name']}")
        print(f"   Status: {result['status']}")
        
        if result['status'] == "WORKING":
            print(f"   Response Time: {result['response_time']}")
            print(f"   Model: {result['model_used']}")
            print(f"   Content: {result['content']}")
            if 'usage' in result and result['usage']:
                usage = result['usage']
                print(f"   Usage: {usage.get('prompt_tokens', 0)} prompt + {usage.get('completion_tokens', 0)} completion = {usage.get('total_tokens', 0)} total")
        else:
            print(f"   Error: {result['error']}")
            if 'response_time' in result and result['response_time']:
                print(f"   Response Time: {result['response_time']}")
    
    print()
    print("=" * 50)
    print("💡 RECOMMENDATIONS")
    print("=" * 50)
    
    if working_keys == 0:
        print("❌ No working OpenRouter keys found!")
        print("   - Check your .env file for OPENROUTER_API_KEY_* variables")
        print("   - Verify your API keys are valid")
        print("   - Make sure keys start with 'sk-'")
    elif working_keys < 3:
        print("⚠️  Only a few working keys found")
        print("   - Consider adding more OpenRouter API keys for better reliability")
        print("   - Monitor key usage to avoid rate limits")
    else:
        print("✅ Good number of working keys")
        print("   - Your OpenRouter fallback system should work well")
    
    print()
    print("🔧 NEXT STEPS")
    print("=" * 50)
    print("1. If keys are working, your app will automatically use OpenRouter as fallback")
    print("2. Monitor usage at: https://openrouter.ai/keys")
    print("3. Check app status at: http://localhost:5000/api/key-status")
    print("4. Test fallback by temporarily disabling Groq keys")
    
    return results

def test_streaming():
    """Test OpenRouter streaming functionality"""
    print("\n" + "=" * 50)
    print("🌊 TESTING STREAMING FUNCTIONALITY")
    print("=" * 50)
    
    # Find first working key
    working_key = None
    for i in range(1, 11):
        key_name = f"OPENROUTER_API_KEY_{i}"
        api_key = os.getenv(key_name)
        if api_key and api_key.startswith('sk-'):
            working_key = api_key
            break
    
    if not working_key:
        print("❌ No working OpenRouter key found for streaming test")
        return
    
    headers = {
        "Authorization": f"Bearer {working_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "RadarGPT"
    }
    
    data = {
        "model": "deepseek-coder-33b-instruct",
        "messages": [
            {
                "role": "user",
                "content": "Count from 1 to 5, one number per line."
            }
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False
    }
    
    try:
        print("Testing streaming response...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            print("✅ Streaming test successful!")
            print("Received chunks:")
            full_response = ""
            chunk_count = 0
            
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
                                    content = delta['content']
                                    full_response += content
                                    chunk_count += 1
                                    print(f"   Chunk {chunk_count}: '{content}'")
                        except json.JSONDecodeError:
                            continue
            
            print(f"\nTotal chunks received: {chunk_count}")
            print(f"Full response: {full_response.strip()}")
        else:
            print(f"❌ Streaming test failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ Streaming test error: {str(e)}")

if __name__ == "__main__":
    # Test all keys
    results = test_all_openrouter_keys()
    
    # Test streaming if any keys are working
    working_count = sum(1 for r in results if r['status'] == 'WORKING')
    if working_count > 0:
        test_streaming()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
    print("=" * 50) 