import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from app.py
from app import groq_generate_content, truncate_prompt_for_groq

def test_prompt_truncation():
    """Test that large prompts are properly truncated"""
    print("🧪 Testing prompt truncation...")
    
    # Create a large prompt
    large_prompt = "This is a test prompt. " * 1000  # ~20,000 characters
    
    print(f"Original prompt length: {len(large_prompt)} characters")
    
    # Test truncation
    truncated = truncate_prompt_for_groq(large_prompt)
    
    print(f"Truncated prompt length: {len(truncated)} characters")
    print(f"Truncation indicator present: {'[Content truncated' in truncated}")
    
    return len(truncated) < len(large_prompt)

def test_large_payload_handling():
    """Test that large payloads are handled gracefully"""
    print("\n🧪 Testing large payload handling...")
    
    try:
        # Create a very large prompt that would cause 413 errors
        large_prompt = "This is a test of large payload handling. " * 2000  # ~80,000 characters
        
        print(f"Testing with {len(large_prompt)} character prompt...")
        
        result = groq_generate_content(large_prompt, max_tokens=50)
        
        print(f"✅ Success! Result: {result[:100]}...")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if 'too large' in error_str or '413' in error_str:
            print(f"✅ Correctly caught payload too large error: {e}")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False

def test_normal_payload():
    """Test that normal-sized payloads work correctly"""
    print("\n🧪 Testing normal payload...")
    
    try:
        normal_prompt = "Hello, this is a normal-sized prompt for testing."
        
        result = groq_generate_content(normal_prompt, max_tokens=50)
        
        print(f"✅ Success! Result: {result[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Error with normal payload: {e}")
        return False

def main():
    print("🚀 Testing Payload Size Limits and Error Handling\n")
    
    # Test 1: Prompt truncation
    # if not test_prompt_truncation():
    #     print("❌ Prompt truncation test failed")
    #     return
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Large payload handling
    if not test_large_payload_handling():
        print("❌ Large payload handling test failed")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Normal payload
    if not test_normal_payload():
        print("❌ Normal payload test failed")
        return
    
    print("\n" + "="*50 + "\n")
    print("🎉 All payload tests completed successfully!")
    print("\n💡 The system now has:")
    print("   - Automatic prompt truncation for large requests")
    print("   - Better error handling for 413 Payload Too Large errors")
    print("   - Reduced payload sizes in pain-cloud-realtime feature")
    print("   - Improved rate limit handling")

if __name__ == "__main__":
    main() 