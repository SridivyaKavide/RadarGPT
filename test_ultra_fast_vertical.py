import time
import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from app.py
from app import groq_generate_content_fast, generate_fallback_response

def test_ultra_fast_generation():
    """Test the ultra-fast generation function"""
    print("🚀 Testing ultra-fast generation...")
    
    # Test with a simple prompt
    prompt = "Analyze customer retention for SaaS startups"
    
    start_time = time.time()
    
    try:
        response = groq_generate_content_fast(prompt, max_tokens=200, temperature=0.7)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Ultra-fast generation completed in {duration:.2f} seconds")
        print(f"📊 Response length: {len(response)} characters")
        print(f"📝 Response preview: {response[:100]}...")
        
        if duration < 10:  # Should be under 10 seconds
            print("🎉 Speed test PASSED - Under 10 seconds!")
            return True
        else:
            print("⚠️ Speed test FAILED - Took too long")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_fallback_response():
    """Test the fallback response generation"""
    print("\n🔄 Testing fallback response...")
    
    start_time = time.time()
    
    try:
        response = generate_fallback_response("test prompt")
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Fallback response generated in {duration:.3f} seconds")
        print(f"📊 Response length: {len(response)} characters")
        
        if duration < 0.1:  # Should be nearly instant
            print("🎉 Fallback test PASSED - Nearly instant!")
            return True
        else:
            print("⚠️ Fallback test FAILED - Took too long")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Ultra-Fast Vertical Insights")
    print("=" * 50)
    
    # Test ultra-fast generation
    generation_success = test_ultra_fast_generation()
    
    # Test fallback response
    fallback_success = test_fallback_response()
    
    print("\n" + "=" * 50)
    if generation_success and fallback_success:
        print("🎉 All tests passed! Vertical insights are now ultra-fast.")
        print("📈 Expected performance: Under 10 seconds for most requests")
    else:
        print("⚠️ Some tests failed. Check the implementation.") 