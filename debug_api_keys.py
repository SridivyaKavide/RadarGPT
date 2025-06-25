#!/usr/bin/env python3
"""
Debug script to check Groq API keys
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def debug_api_keys():
    """Debug API key issues"""
    
    print("🔍 Debugging Groq API Keys")
    print("=" * 50)
    
    # Check single key first
    single_key = os.getenv('GROQ_API_KEY')
    if single_key:
        print(f"✅ GROQ_API_KEY found: {single_key[:10]}...{single_key[-4:]}")
        test_single_key(single_key)
    else:
        print("❌ GROQ_API_KEY not found")
    
    print("\n" + "=" * 50)
    
    # Check rotation keys
    rotation_keys = []
    for i in range(1, 30):
        key = os.getenv(f'GROQ_API_KEY_{i}')
        if key:
            rotation_keys.append((i, key))
    
    if rotation_keys:
        print(f"✅ Found {len(rotation_keys)} rotation keys:")
        for i, key in rotation_keys:
            print(f"   GROQ_API_KEY_{i}: {key[:10]}...{key[-4:]}")
        
        # Test first few keys
        for i, key in rotation_keys[:3]:
            print(f"\n🧪 Testing GROQ_API_KEY_{i}...")
            test_single_key(key, key_name=f"GROQ_API_KEY_{i}")
    else:
        print("❌ No rotation keys found")
    
    print("\n" + "=" * 50)
    print("💡 Troubleshooting Tips:")
    print("1. Make sure your API keys are valid and active")
    print("2. Check if you have sufficient credits/quota")
    print("3. Verify the API key format (should start with 'gsk_')")
    print("4. Try creating a new API key in your Groq dashboard")
    print("5. Check if your account is properly set up")

def test_single_key(api_key, key_name="API Key"):
    """Test a single API key"""
    try:
        # Create client with explicit API key
        client = Groq(api_key=api_key)
        
        # Test with a simple request
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            temperature=1,
            max_tokens=10,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        response = completion.choices[0].message.content
        print(f"   ✅ {key_name} works! Response: {response}")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str or 'invalid api key' in error_str:
            print(f"   ❌ {key_name} is INVALID: {e}")
        elif 'rate limit' in error_str or '429' in error_str:
            print(f"   ⚠️ {key_name} rate limited: {e}")
        else:
            print(f"   ❌ {key_name} error: {e}")
        return False

def check_env_file():
    """Check if .env file exists and has the right format"""
    print("\n📁 Checking .env file...")
    
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            groq_lines = [line for line in lines if line.startswith('GROQ_API_KEY')]
            if groq_lines:
                print(f"✅ Found {len(groq_lines)} GROQ_API_KEY lines")
                for line in groq_lines[:3]:  # Show first 3
                    if '=' in line:
                        key_name, key_value = line.split('=', 1)
                        if key_value.strip():
                            print(f"   {key_name}: {key_value.strip()[:10]}...{key_value.strip()[-4:]}")
                        else:
                            print(f"   {key_name}: EMPTY")
            else:
                print("❌ No GROQ_API_KEY lines found in .env")
    else:
        print("❌ .env file not found")

if __name__ == "__main__":
    check_env_file()
    debug_api_keys() 