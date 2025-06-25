import requests
import json
from datetime import datetime

def test_usage_dashboard():
    """Test the usage dashboard functionality"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Usage Dashboard Functionality")
    print("=" * 50)
    
    # Test 1: Check if usage dashboard page loads
    print("\n1. Testing Usage Dashboard Page...")
    try:
        response = requests.get(f"{base_url}/usage-dashboard")
        if response.status_code == 200:
            print("✅ Usage dashboard page loads successfully")
        else:
            print(f"❌ Usage dashboard page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing usage dashboard: {e}")
    
    # Test 2: Test usage stats API (requires authentication)
    print("\n2. Testing Usage Stats API...")
    try:
        response = requests.get(f"{base_url}/api/usage-stats")
        if response.status_code == 200:
            data = response.json()
            print("✅ Usage stats API works")
            print(f"   - Plan: {data.get('subscription', {}).get('plan_type', 'N/A')}")
            print(f"   - Monthly usage: {data.get('monthly_usage', {})}")
        elif response.status_code == 401:
            print("⚠️  Usage stats API requires authentication (expected)")
        else:
            print(f"❌ Usage stats API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing usage stats API: {e}")
    
    # Test 3: Test track usage API (requires authentication)
    print("\n3. Testing Track Usage API...")
    try:
        response = requests.post(
            f"{base_url}/api/track-usage",
            json={
                'module': 'test',
                'action': 'test_action',
                'usage_count': 1
            }
        )
        if response.status_code == 200:
            print("✅ Track usage API works")
        elif response.status_code == 401:
            print("⚠️  Track usage API requires authentication (expected)")
        else:
            print(f"❌ Track usage API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing track usage API: {e}")
    
    # Test 4: Test upgrade plan API (requires authentication)
    print("\n4. Testing Upgrade Plan API...")
    try:
        response = requests.post(
            f"{base_url}/api/upgrade-plan",
            json={
                'plan_type': 'pro'
            }
        )
        if response.status_code == 200:
            print("✅ Upgrade plan API works")
        elif response.status_code == 401:
            print("⚠️  Upgrade plan API requires authentication (expected)")
        else:
            print(f"❌ Upgrade plan API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing upgrade plan API: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Usage Dashboard Testing Complete!")
    print("\nTo test with authentication:")
    print("1. Register/login at http://localhost:5000")
    print("2. Visit http://localhost:5000/usage-dashboard")
    print("3. Use the different modules to see usage tracking in action")

if __name__ == "__main__":
    test_usage_dashboard() 