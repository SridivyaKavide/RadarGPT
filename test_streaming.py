import time
import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from app.py
from app import groq_generate_content_fast_stream, groq_generate_content_fast

def test_streaming_generation():
    """Test the streaming generation function"""
    print("🚀 Testing streaming generation...")
    
    # Test with a simple prompt
    prompt = "Analyze customer retention for SaaS startups"
    
    start_time = time.time()
    
    try:
        # Test streaming
        print("📡 Testing streaming response...")
        full_response = ""
        chunk_count = 0
        
        for chunk in groq_generate_content_fast_stream(prompt, max_tokens=200, temperature=0.7):
            full_response += chunk
            chunk_count += 1
            print(f"📦 Chunk {chunk_count}: {len(chunk)} characters")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Streaming generation completed in {duration:.2f} seconds")
        print(f"📊 Total chunks: {chunk_count}")
        print(f"📝 Total response length: {len(full_response)} characters")
        print(f"📄 Response preview: {full_response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Streaming generation failed: {e}")
        return False

def test_non_streaming_generation():
    """Test the non-streaming generation function for comparison"""
    print("\n🔄 Testing non-streaming generation...")
    
    # Test with a simple prompt
    prompt = "Analyze customer retention for SaaS startups"
    
    start_time = time.time()
    
    try:
        # Test non-streaming
        response = groq_generate_content_fast(prompt, max_tokens=200, temperature=0.7)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Non-streaming generation completed in {duration:.2f} seconds")
        print(f"📝 Response length: {len(response)} characters")
        print(f"📄 Response preview: {response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Non-streaming generation failed: {e}")
        return False

def test_streaming_vs_non_streaming():
    """Compare streaming vs non-streaming performance"""
    print("\n⚡ Performance Comparison Test")
    print("=" * 50)
    
    # Test both methods
    streaming_success = test_streaming_generation()
    non_streaming_success = test_non_streaming_generation()
    
    if streaming_success and non_streaming_success:
        print("\n🎉 Both streaming and non-streaming tests passed!")
        print("✅ Your streaming implementation is working correctly")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")
    
    return streaming_success and non_streaming_success

if __name__ == "__main__":
    print("🧪 Starting Streaming Tests")
    print("=" * 50)
    
    success = test_streaming_vs_non_streaming()
    
    if success:
        print("\n🎉 All tests passed! Your streaming system is ready.")
        print("\n📋 Next steps:")
        print("1. Start your Flask app: python app.py")
        print("2. Visit: http://localhost:5000/vertical-insights-streaming")
        print("3. Select a vertical and enter a query")
        print("4. Watch the streaming response in real-time!")
    else:
        print("\n❌ Some tests failed. Please check your implementation.") 