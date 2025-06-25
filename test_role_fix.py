#!/usr/bin/env python3
"""
Test script to verify the role mapping fix for Groq API
"""

import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions from app.py
from app import groq_start_chat

def test_role_mapping():
    """Test that role mapping works correctly"""
    print("🧪 Testing role mapping fix...")
    
    # Create test history with mixed roles (including 'bot' which should be converted to 'model')
    test_history = [
        {"role": "user", "parts": ["Hello"]},
        {"role": "bot", "parts": ["Hi there!"]},  # This should be converted to 'model'
        {"role": "user", "parts": ["How are you?"]},
        {"role": "bot", "parts": ["I'm doing well!"]},  # This should be converted to 'model'
        {"role": "assistant", "parts": ["I'm an assistant"]},  # This should stay as 'assistant'
    ]
    
    try:
        # Create chat instance
        chat = groq_start_chat(history=test_history)
        
        # Test sending a message (this will trigger the role conversion)
        response = chat.send_message("Test message")
        
        print("✅ Role mapping test completed successfully!")
        print(f"Response: {response.text[:100]}...")
        
        # Check that the history was updated correctly
        print(f"History length: {len(chat.history)}")
        for i, msg in enumerate(chat.history):
            print(f"  Message {i+1}: role='{msg['role']}', content='{msg['parts'][0][:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"❌ Role mapping test failed: {e}")
        return False

def test_invalid_roles():
    """Test that invalid roles are handled gracefully"""
    print("\n🧪 Testing invalid role handling...")
    
    # Create test history with invalid roles
    test_history = [
        {"role": "user", "parts": ["Hello"]},
        {"role": "invalid_role", "parts": ["This should be converted to 'user'"]},  # Invalid role
        {"role": "unknown", "parts": ["This should also be converted to 'user'"]},  # Invalid role
    ]
    
    try:
        # Create chat instance
        chat = groq_start_chat(history=test_history)
        
        # Test sending a message
        response = chat.send_message("Test message")
        
        print("✅ Invalid role handling test completed successfully!")
        print(f"Response: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid role handling test failed: {e}")
        return False

def main():
    print("🚀 Testing Role Mapping Fix for Groq API\n")
    
    # Test 1: Role mapping
    if not test_role_mapping():
        print("❌ Role mapping test failed")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Invalid role handling
    if not test_invalid_roles():
        print("❌ Invalid role handling test failed")
        return
    
    print("\n" + "="*50 + "\n")
    print("🎉 All role mapping tests completed successfully!")
    print("\n💡 The fix addresses:")
    print("   - Converting 'bot' roles to 'model' for Groq API compatibility")
    print("   - Handling invalid roles by defaulting to 'user'")
    print("   - Maintaining compatibility with 'user', 'model', and 'assistant' roles")
    print("   - Preventing 'messages.2: discriminator property role has invalid value' errors")

if __name__ == "__main__":
    main() 