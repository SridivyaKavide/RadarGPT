#!/usr/bin/env python3
"""
Simple script to test a single Groq API key
"""

import os
from groq import Groq

def test_single_key(api_key):
    """Test a single Groq API key"""
    print(f"🔑 Testing API key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 50)
    
    try:
        # Create client with explicit API key
        client = Groq(api_key=api_key)
        
        # Test with a simple request
        print("📡 Making test request...")
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": "Explain the importance of low latency LLMs"}],
            temperature=0,
            max_tokens=50,
            stream=False,
        )
        
        response = completion.choices[0].message.content
        print(f"✅ SUCCESS! Response: {response}")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        print(f"❌ ERROR: {e}")
        
        if '401' in error_str or 'unauthorized' in error_str:
            print("🔍 This looks like an authentication error")
            print("   - Check if the API key is correct")
            print("   - Make sure the key is active in your Groq dashboard")
        elif 'rate limit' in error_str or '429' in error_str:
            print("🔍 This looks like a rate limit error")
            print("   - The key might be rate limited")
        elif 'invalid' in error_str:
            print("🔍 This looks like an invalid key error")
            print("   - Check the key format (should start with 'gsk_')")
        else:
            print("🔍 Unknown error type")
        
        return False

if __name__ == "__main__":
    print("🧪 Groq API Key Tester")
    print("=" * 50)
    
    # Get API key from user
    api_key = input("Enter your Groq API key (starts with 'gsk_'): ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        exit(1)
    
    if not api_key.startswith('gsk_'):
        print("❌ Invalid API key format. Should start with 'gsk_'")
        exit(1)
    
    # Test the key
    success = test_single_key(api_key)
    
    if success:
        print("\n🎉 Your API key is working correctly!")
        print("💡 You can now use it in your Flask app")
    else:
        print("\n💡 Troubleshooting tips:")
        print("1. Check your Groq dashboard to ensure the key is active")
        print("2. Make sure you copied the full key correctly")
        print("3. Try creating a new API key if this one doesn't work")
        print("4. Check if there are any usage limits on your account") 