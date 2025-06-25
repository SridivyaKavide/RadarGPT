#!/usr/bin/env python3
"""
Test script for live-trends API functionality
"""

import requests
import json
import time

def login_and_get_session():
    """Login and get a session for testing"""
    
    print("🔐 Logging in...")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # First, try to register a test user if it doesn't exist
        register_data = {
            "username": "testuser_live_trends",
            "password": "testpass123"
        }
        
        register_response = session.post(
            "http://localhost:5000/register",
            data=register_data,
            timeout=10
        )
        
        # Now try to login
        login_data = {
            "username": "testuser_live_trends",
            "password": "testpass123"
        }
        
        login_response = session.post(
            "http://localhost:5000/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code == 200 or login_response.status_code == 302:
            print("✅ Login successful!")
            return session
        else:
            print(f"❌ Login failed with status {login_response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_live_trends_api(session):
    """Test the live-trends API endpoint"""
    
    # Test data
    test_data = {
        "region": "global",
        "category": "all",
        "time_window": "24h"
    }
    
    print("🧪 Testing live-trends API...")
    print(f"Request data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Make request to the API using the session
        response = session.post(
            "http://localhost:5000/api/live-trends",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API call successful!")
            print(f"Total trends: {data.get('total_trends', 0)}")
            print(f"Sources active: {data.get('sources_active', 0)}")
            print(f"Timestamp: {data.get('timestamp', 'N/A')}")
            
            # Check each source
            trends_data = data.get('trends_data', {})
            for source, trends in trends_data.items():
                if isinstance(trends, list):
                    print(f"  {source}: {len(trends)} items")
                else:
                    print(f"  {source}: {type(trends)}")
            
            return True
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_live_trends_page(session):
    """Test the live-trends page loads"""
    
    print("\n🌐 Testing live-trends page...")
    
    try:
        response = session.get("http://localhost:5000/live-trends", timeout=10)
        
        print(f"Page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Live-trends page loads successfully!")
            return True
        else:
            print(f"❌ Page failed to load with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_without_auth():
    """Test what happens without authentication"""
    
    print("\n🚫 Testing without authentication...")
    
    try:
        response = requests.get("http://localhost:5000/live-trends", timeout=10)
        print(f"Unauthenticated page status: {response.status_code}")
        
        if response.status_code == 302:
            print("✅ Correctly redirecting to login page")
            return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting live-trends tests...")
    
    # Test without authentication first
    auth_test = test_without_auth()
    
    # Login and get session
    session = login_and_get_session()
    
    if session:
        # Test page loading with authentication
        page_success = test_live_trends_page(session)
        
        # Test API functionality with authentication
        api_success = test_live_trends_api(session)
        
        print("\n📊 Test Results:")
        print(f"Authentication redirect: {'✅ PASS' if auth_test else '❌ FAIL'}")
        print(f"Page loading: {'✅ PASS' if page_success else '❌ FAIL'}")
        print(f"API functionality: {'✅ PASS' if api_success else '❌ FAIL'}")
        
        if auth_test and page_success and api_success:
            print("\n🎉 All tests passed! Live-trends is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
    else:
        print("\n❌ Could not authenticate. Cannot test protected endpoints.")
        print("📊 Test Results:")
        print(f"Authentication redirect: {'✅ PASS' if auth_test else '❌ FAIL'}")
        print("Page loading: ❌ SKIP (no auth)")
        print("API functionality: ❌ SKIP (no auth)") 