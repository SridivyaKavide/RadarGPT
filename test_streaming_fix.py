#!/usr/bin/env python3
"""
Test script to verify streaming functionality is working
"""

import requests
import json
import time

def test_streaming_endpoint():
    """Test the streaming endpoint"""
    print("Testing streaming endpoint...")
    
    url = "http://localhost:5000/analyze-stream/fintech/test"
    
    try:
        response = requests.post(url, json={}, stream=True)
        
        if response.status_code == 200:
            print("✅ Streaming endpoint is working!")
            print("Response chunks:")
            
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    print(f"Chunk: {chunk[:100]}...")
                    break  # Just show first chunk
        else:
            print(f"❌ Streaming endpoint failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing streaming: {e}")

def test_regular_endpoint():
    """Test the regular endpoint"""
    print("\nTesting regular endpoint...")
    
    url = "http://localhost:5000/analyze/fintech/test"
    
    try:
        response = requests.post(url, json={})
        
        if response.status_code == 200:
            print("✅ Regular endpoint is working!")
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
        else:
            print(f"❌ Regular endpoint failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing regular endpoint: {e}")

def test_vertical_insights_page():
    """Test if the vertical insights page loads"""
    print("\nTesting vertical insights page...")
    
    url = "http://localhost:5000/vertical-insights"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            print("✅ Vertical insights page loads successfully!")
            if "streaming" in response.text.lower():
                print("✅ Page contains streaming functionality")
            else:
                print("⚠️ Page might not have streaming functionality")
        else:
            print(f"❌ Vertical insights page failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing vertical insights page: {e}")

if __name__ == "__main__":
    print("Testing streaming functionality...")
    print("Make sure the Flask app is running on http://localhost:5000")
    print("=" * 50)
    
    test_vertical_insights_page()
    test_regular_endpoint()
    test_streaming_endpoint()
    
    print("\n" + "=" * 50)
    print("Test completed!") 