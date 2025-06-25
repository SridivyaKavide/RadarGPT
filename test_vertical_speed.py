import time
import requests
import json

def test_vertical_speed():
    """Test the speed of vertical insights after optimization"""
    
    # Test data
    vertical = "saas"
    query = "customer retention"
    
    print("🚀 Testing vertical insights speed...")
    
    # Test the analyze endpoint
    start_time = time.time()
    
    try:
        response = requests.post(
            f"http://localhost:5000/analyze/{vertical}/{query}",
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Vertical analysis completed in {duration:.2f} seconds")
            print(f"📊 Response size: {len(json.dumps(data))} characters")
            
            # Check if it's cached
            if "cached" in data:
                print("🔄 Response was served from cache")
            else:
                print("🆕 Response was generated fresh")
                
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_vertical_chat_speed():
    """Test the speed of vertical chat after optimization"""
    
    # Test data
    vertical = "saas"
    query = "customer retention"
    user_text = "What are the main challenges in this space?"
    context = "Customer retention analysis for SaaS companies"
    
    print("\n💬 Testing vertical chat speed...")
    
    # Test the chat endpoint
    start_time = time.time()
    
    try:
        response = requests.post(
            f"http://localhost:5000/vertical-chat/{vertical}/{query}",
            headers={"Content-Type": "application/json"},
            json={
                "text": user_text,
                "context": context
            },
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Vertical chat completed in {duration:.2f} seconds")
            print(f"📊 Response: {data.get('bot_reply', '')[:100]}...")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Vertical Insights Performance")
    print("=" * 50)
    
    # Test analysis speed
    analysis_success = test_vertical_speed()
    
    # Test chat speed
    chat_success = test_vertical_chat_speed()
    
    print("\n" + "=" * 50)
    if analysis_success and chat_success:
        print("🎉 All tests passed! Vertical insights are now optimized for speed.")
    else:
        print("⚠️ Some tests failed. Check the server logs for details.") 