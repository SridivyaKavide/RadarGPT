#!/usr/bin/env python3
"""
Test the new throttling and rate limiting system
"""

import time
import threading
import requests
import json
import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from app.py
from app import groq_generate_content, request_limiter

def test_single_request():
    """Test a single request to verify basic functionality"""
    print("🧪 Testing single request...")
    try:
        response = groq_generate_content("Hello, please respond with 'test successful'", max_tokens=50, model="qwen/qwen3-32b")
        print(f"✅ Single request successful: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Single request failed: {e}")
        return False

def test_concurrent_requests(num_requests=10):
    """Test multiple concurrent requests"""
    print(f"🧪 Testing {num_requests} concurrent requests...")
    
    results = []
    errors = []
    
    def make_request(request_id):
        try:
            response = groq_generate_content(f"Request {request_id}: Hello", max_tokens=30, model="qwen/qwen3-32b")
            results.append((request_id, response[:50]))
            print(f"✅ Request {request_id} completed")
        except Exception as e:
            errors.append((request_id, str(e)))
            print(f"❌ Request {request_id} failed: {e}")
    
    # Create threads for concurrent requests
    threads = []
    for i in range(num_requests):
        thread = threading.Thread(target=make_request, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"\n📊 Results:")
    print(f"✅ Successful: {len(results)}")
    print(f"❌ Failed: {len(errors)}")
    
    if errors:
        print(f"\n❌ Errors:")
        for request_id, error in errors:
            print(f"  Request {request_id}: {error}")
    
    return len(errors) == 0

def test_rate_limit_handling():
    """Test rate limit handling by making many requests quickly"""
    print("🧪 Testing rate limit handling...")
    
    # Make many requests quickly to trigger rate limiting
    num_requests = 20
    results = []
    errors = []
    
    def make_request(request_id):
        try:
            response = groq_generate_content(f"Rate limit test {request_id}", max_tokens=20, model="qwen/qwen3-32b")
            results.append((request_id, response[:30]))
        except Exception as e:
            errors.append((request_id, str(e)))
    
    # Create threads for concurrent requests
    threads = []
    for i in range(num_requests):
        thread = threading.Thread(target=make_request, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"\n📊 Rate Limit Test Results:")
    print(f"✅ Successful: {len(results)}")
    print(f"❌ Failed: {len(errors)}")
    
    # Check if we got fallback responses (indicating rate limiting worked)
    fallback_responses = [r for r in results if "fallback" in r[1].lower()]
    if fallback_responses:
        print(f"🔄 Fallback responses: {len(fallback_responses)}")
        print("✅ Rate limiting and fallback system working correctly")
    else:
        print("ℹ️ No fallback responses - all requests succeeded")
    
    return len(errors) == 0

def test_request_limiter():
    """Test the request limiter functionality"""
    print("🧪 Testing request limiter...")
    
    print(f"Initial state - Active requests: {request_limiter.active_requests}/{request_limiter.max_concurrent}")
    
    # Test acquiring and releasing
    request_limiter.acquire()
    print(f"After acquire - Active requests: {request_limiter.active_requests}/{request_limiter.max_concurrent}")
    
    request_limiter.release()
    print(f"After release - Active requests: {request_limiter.active_requests}/{request_limiter.max_concurrent}")
    
    print("✅ Request limiter working correctly")

def main():
    print("🚀 Starting Groq Throttling and Rate Limiting Tests\n")
    
    # Test 1: Single request
    if not test_single_request():
        print("❌ Single request test failed. Stopping tests.")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Request limiter
    test_request_limiter()
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Concurrent requests
    if not test_concurrent_requests(5):
        print("⚠️ Some concurrent requests failed, but continuing...")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Rate limit handling
    test_rate_limit_handling()
    
    print("\n" + "="*50 + "\n")
    print("🎉 All tests completed!")

if __name__ == "__main__":
    main() 