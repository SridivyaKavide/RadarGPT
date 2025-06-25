#!/usr/bin/env python3
"""
Comprehensive Groq API Key Validation Script
"""

import os
import requests
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def check_key_via_api(api_key):
    """Check API key validity via direct API call"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "model": "qwen/qwen3-32b",
        "messages": [{"role": "user", "content": "test"}],
        "temperature": 1,
        "max_tokens": 10,
        "top_p": 1,
        "stream": False
    }
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "Valid and active"
        elif response.status_code == 401:
            return False, "Invalid API key"
        elif response.status_code == 429:
            return False, "Rate limited"
        elif response.status_code == 403:
            return False, "Forbidden - check permissions"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"

def check_key_via_groq_library(api_key):
    """Check API key validity via Groq library"""
    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": "test"}],
            temperature=1,
            max_tokens=10,
            top_p=1,
            stream=False,
            stop=None,
        )
        return True, "Valid and active"
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str:
            return False, "Invalid API key"
        elif '429' in error_str or 'rate limit' in error_str:
            return False, "Rate limited"
        elif '403' in error_str or 'forbidden' in error_str:
            return False, "Forbidden - check permissions"
        else:
            return False, f"Error: {e}"

def validate_api_key_format(api_key):
    """Validate API key format"""
    if not api_key:
        return False, "Empty key"
    
    if not api_key.startswith('gsk_'):
        return False, "Invalid format - should start with 'gsk_'"
    
    if len(api_key) < 50:
        return False, "Too short - should be at least 50 characters"
    
    return True, "Valid format"

def check_all_keys():
    """Check all API keys in environment"""
    print("🔍 Comprehensive Groq API Key Validation")
    print("=" * 60)
    
    # Collect all keys
    all_keys = []
    
    # Single key
    single_key = os.getenv('GROQ_API_KEY')
    if single_key:
        all_keys.append(('GROQ_API_KEY', single_key))
    
    # Rotation keys
    for i in range(1, 30):
        key = os.getenv(f'GROQ_API_KEY_{i}')
        if key:
            all_keys.append((f'GROQ_API_KEY_{i}', key))
    
    if not all_keys:
        print("❌ No API keys found in environment variables")
        return
    
    print(f"📋 Found {len(all_keys)} API keys to validate")
    print()
    
    valid_keys = []
    invalid_keys = []
    
    for key_name, api_key in all_keys:
        print(f"🔑 Testing {key_name}: {api_key[:10]}...{api_key[-4:]}")
        
        # Check format
        format_valid, format_msg = validate_api_key_format(api_key)
        if not format_valid:
            print(f"   ❌ Format: {format_msg}")
            invalid_keys.append((key_name, api_key, format_msg))
            continue
        
        print(f"   ✅ Format: {format_msg}")
        
        # Check via API
        api_valid, api_msg = check_key_via_api(api_key)
        if api_valid:
            print(f"   ✅ API: {api_msg}")
        else:
            print(f"   ❌ API: {api_msg}")
        
        # Check via library
        lib_valid, lib_msg = check_key_via_groq_library(api_key)
        if lib_valid:
            print(f"   ✅ Library: {lib_msg}")
        else:
            print(f"   ❌ Library: {lib_msg}")
        
        # Overall status
        if api_valid and lib_valid:
            print(f"   🎉 STATUS: VALID AND ACTIVE")
            valid_keys.append((key_name, api_key))
        else:
            print(f"   💥 STATUS: INVALID")
            invalid_keys.append((key_name, api_key, f"API: {api_msg}, Library: {lib_msg}"))
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Valid keys: {len(valid_keys)}")
    print(f"❌ Invalid keys: {len(invalid_keys)}")
    
    if valid_keys:
        print("\n🎉 VALID KEYS:")
        for key_name, api_key in valid_keys:
            print(f"   {key_name}: {api_key[:10]}...{api_key[-4:]}")
    
    if invalid_keys:
        print("\n💥 INVALID KEYS:")
        for key_name, api_key, error in invalid_keys:
            print(f"   {key_name}: {error}")
    
    print("\n" + "=" * 60)
    print("💡 TROUBLESHOOTING TIPS:")
    print("1. Valid keys should start with 'gsk_' and be 50+ characters")
    print("2. Check your Groq dashboard for active keys")
    print("3. Ensure you have sufficient credits/quota")
    print("4. Try creating new API keys if all are invalid")
    print("5. Check if your account is properly verified")

def check_specific_key(api_key):
    """Check a specific API key"""
    print(f"🔍 Checking specific API key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 50)
    
    # Format check
    format_valid, format_msg = validate_api_key_format(api_key)
    print(f"📋 Format: {format_msg}")
    
    if not format_valid:
        print("❌ Key format is invalid")
        return False
    
    # API check
    api_valid, api_msg = check_key_via_api(api_key)
    print(f"🌐 API Test: {api_msg}")
    
    # Library check
    lib_valid, lib_msg = check_key_via_groq_library(api_key)
    print(f"📚 Library Test: {lib_msg}")
    
    # Overall result
    if api_valid and lib_valid:
        print("🎉 RESULT: VALID AND ACTIVE")
        return True
    else:
        print("💥 RESULT: INVALID")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Check specific key provided as argument
        api_key = sys.argv[1]
        check_specific_key(api_key)
    else:
        # Check all keys in environment
        check_all_keys() 