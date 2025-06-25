#!/usr/bin/env python3
"""
Simple test script using the exact Groq format specified by the user
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def test_groq_simple():
    """Test Groq with the exact format specified by the user"""
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment variables")
        return False
    
    try:
        # Create client exactly as specified
        client = Groq(api_key=api_key)
        
        # Test with different parameters
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {
                    "role": "user",
                    "content": "What is 2+2?"
                }
            ],
            temperature=0,
            max_tokens=50,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        # Get the response
        response = completion.choices[0].message.content
        print(f"✅ Groq API is working!")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Groq API: {e}")
        return False

def test_groq_streaming():
    """Test Groq with streaming as specified"""
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment variables")
        return False
    
    try:
        # Create client
        client = Groq(api_key=api_key)
        
        # Test with streaming
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {
                    "role": "user",
                    "content": "Count from 1 to 5"
                }
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        
        print("✅ Groq streaming is working!")
        print("Response (streaming):")
        
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")
        
        print("\n")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Groq streaming: {e}")
        return False

def test_api_key_rotation():
    """Test API key rotation functionality"""
    
    # Test multiple API keys
    api_keys = []
    for i in range(1, 30):
        key = os.getenv(f"GROQ_API_KEY_{i}")
        if key:
            api_keys.append(key)
    
    # Fallback to single key
    if not api_keys:
        single_key = os.getenv("GROQ_API_KEY")
        if single_key:
            api_keys = [single_key]
    
    print(f"Found {len(api_keys)} API keys for rotation")
    
    if not api_keys:
        print("❌ No API keys found")
        return False
    
    # Test each key
    working_keys = 0
    for i, key in enumerate(api_keys[:5]):  # Test first 5 keys
        try:
            client = Groq(api_key=key)
            completion = client.chat.completions.create(
                model="qwen-qwq-32b",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
                temperature=0,
            )
            working_keys += 1
            print(f"✅ API key {i+1} is working")
        except Exception as e:
            print(f"❌ API key {i+1} failed: {str(e)[:100]}...")
    
    print(f"Working keys: {working_keys}/{min(5, len(api_keys))}")
    return working_keys > 0

if __name__ == "__main__":
    print("🧪 Testing Groq Integration")
    print("=" * 50)
    
    # Test simple API call
    print("\n1. Testing simple API call...")
    test_groq_simple()
    
    # Test streaming
    print("\n2. Testing streaming...")
    test_groq_streaming()
    
    # Test API key rotation
    print("\n3. Testing API key rotation...")
    test_api_key_rotation()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!") 