#!/usr/bin/env python3
"""
Quick test script to verify Groq API connection
"""

from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_connection():
    """Test the API connection with the first available key"""
    
    print("🧪 Testing Groq API Connection")
    print("=" * 40)
    
    # Get all available API keys
    api_keys = []
    
    # Try single key first
    single_key = os.getenv('GROQ_API_KEY')
    if single_key and single_key.startswith('gsk_'):
        api_keys.append(single_key)
    
    # Try rotation keys
    for i in range(1, 30):
        key = os.getenv(f'GROQ_API_KEY_{i}')
        if key and key.startswith('gsk_'):
            api_keys.append(key)
    
    if not api_keys:
        print("❌ No valid API keys found in .env file")
        print("💡 Make sure your .env file contains actual API keys (not placeholders)")
        return False
    
    print(f"✅ Found {len(api_keys)} API keys")
    print(f"🔑 Testing first key: {api_keys[0][:10]}...{api_keys[0][-4:]}")
    
    try:
        # Create client
        client = Groq(api_key=api_keys[0])
        
        # Test request
        print("📡 Making test request...")
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'API connection successful!'"
                }
            ],
            temperature=0,
            max_tokens=50,
            top_p=1,
            stream=False,
        )
        
        response = completion.choices[0].message.content
        print(f"✅ SUCCESS! Response: {response}")
        print("\n🎉 Your Groq API is working correctly!")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        print(f"❌ ERROR: {e}")
        
        if '401' in error_str or 'unauthorized' in error_str:
            print("\n🔍 Authentication Error - Possible causes:")
            print("   - API key is incorrect or inactive")
            print("   - Key format is wrong")
            print("   - Account has no credits/usage")
        elif 'rate limit' in error_str or '429' in error_str:
            print("\n🔍 Rate Limit Error - Possible causes:")
            print("   - Too many requests")
            print("   - Account limits exceeded")
        else:
            print(f"\n🔍 Unknown error: {e}")
        
        return False

if __name__ == "__main__":
    test_api_connection() 