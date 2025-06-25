#!/usr/bin/env python3
"""
Test both direct HTTP and Groq client approaches
"""

import requests
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_direct_http():
    """Test direct HTTP API approach"""
    print("🌐 Testing Direct HTTP API Approach")
    print("=" * 40)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    # Test 1: List models
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        print("📡 Testing models endpoint...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Success! Found {len(models.get('data', []))} models")
            for model in models.get('data', [])[:3]:  # Show first 3
                print(f"   - {model.get('id', 'Unknown')}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_groq_client():
    """Test Groq client approach"""
    print("\n🐍 Testing Groq Client Approach")
    print("=" * 40)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Create client
        client = Groq(api_key=api_key)
        
        # Test chat completion
        print("📡 Testing chat completion...")
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'Both methods work!'"
                }
            ],
            temperature=0,
            max_tokens=50,
            top_p=1,
            stream=False,
        )
        
        response = completion.choices[0].message.content
        print(f"✅ Success! Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_models_comparison():
    """Compare models from both approaches"""
    print("\n📊 Comparing Models from Both Approaches")
    print("=" * 50)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ No GROQ_API_KEY found in environment")
        return
    
    # Direct HTTP approach
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            http_models = response.json()
            http_model_ids = [model.get('id') for model in http_models.get('data', [])]
            print(f"🌐 HTTP API found {len(http_model_ids)} models")
        else:
            print(f"❌ HTTP API error: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ HTTP API exception: {e}")
        return
    
    # Groq client approach
    try:
        client = Groq(api_key=api_key)
        client_models = client.models.list()
        client_model_ids = [model.id for model in client_models.data]
        print(f"🐍 Groq Client found {len(client_model_ids)} models")
    except Exception as e:
        print(f"❌ Groq Client exception: {e}")
        return
    
    # Compare
    print("\n🔍 Model Comparison:")
    print("HTTP API Models:", http_model_ids[:5])  # Show first 5
    print("Groq Client Models:", client_model_ids[:5])  # Show first 5
    
    # Check if qwen/qwen3-32b is available
    target_model = "qwen/qwen3-32b"
    http_has_model = target_model in http_model_ids
    client_has_model = target_model in client_model_ids
    
    print(f"\n🎯 Target model '{target_model}':")
    print(f"   HTTP API: {'✅' if http_has_model else '❌'}")
    print(f"   Groq Client: {'✅' if client_has_model else '❌'}")

if __name__ == "__main__":
    print("🧪 Testing Both Groq API Approaches")
    print("=" * 50)
    
    # Test both methods
    http_success = test_direct_http()
    client_success = test_groq_client()
    
    # Compare models
    test_models_comparison()
    
    print("\n📋 Summary:")
    print(f"   Direct HTTP: {'✅ Working' if http_success else '❌ Failed'}")
    print(f"   Groq Client: {'✅ Working' if client_success else '❌ Failed'}")
    
    if http_success and client_success:
        print("\n🎉 Both methods work! Your API key is valid.")
        print("💡 The Flask app uses the Groq Client approach for better reliability.")
    elif client_success:
        print("\n✅ Groq Client works! Your Flask app should work fine.")
    else:
        print("\n❌ Both methods failed. Check your API key configuration.") 