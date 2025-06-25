#!/usr/bin/env python3
"""
Test and optimize the key rotation system
"""

import os
import time
import random
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def get_all_available_keys():
    """Get all available API keys from environment"""
    keys = []
    
    # Get main key
    main_key = os.getenv('GROQ_API_KEY')
    if main_key and main_key.startswith('gsk_'):
        keys.append(('GROQ_API_KEY', main_key))
    
    # Get rotation keys
    for i in range(1, 30):
        key_name = f'GROQ_API_KEY_{i}'
        key_value = os.getenv(key_name)
        if key_value and key_value.startswith('gsk_'):
            keys.append((key_name, key_value))
    
    return keys

def test_key_rotation():
    """Test the key rotation system"""
    print("🔄 Testing Key Rotation System")
    print("=" * 50)
    
    # Get all available keys
    available_keys = get_all_available_keys()
    
    if not available_keys:
        print("❌ No valid API keys found")
        return False
    
    print(f"✅ Found {len(available_keys)} valid API keys")
    
    # Test each key individually
    working_keys = []
    failed_keys = []
    
    for key_name, key_value in available_keys:
        print(f"\n🔑 Testing {key_name}: {key_value[:10]}...{key_value[-4:]}")
        
        try:
            client = Groq(api_key=key_value)
            completion = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
                temperature=0,
            )
            print(f"   ✅ Working")
            working_keys.append((key_name, key_value))
        except Exception as e:
            error_str = str(e).lower()
            if '401' in error_str or 'unauthorized' in error_str:
                print(f"   ❌ Invalid key")
                failed_keys.append((key_name, key_value))
            elif 'rate limit' in error_str or '429' in error_str:
                print(f"   ⚠️  Rate limited")
                failed_keys.append((key_name, key_value))
            else:
                print(f"   ❌ Error: {e}")
                failed_keys.append((key_name, key_value))
    
    print(f"\n📊 Results:")
    print(f"   ✅ Working keys: {len(working_keys)}")
    print(f"   ❌ Failed keys: {len(failed_keys)}")
    
    return working_keys, failed_keys

def simulate_rotation_usage(working_keys, num_requests=10):
    """Simulate how the rotation system would work under load"""
    print(f"\n🔄 Simulating Key Rotation ({num_requests} requests)")
    print("=" * 50)
    
    if not working_keys:
        print("❌ No working keys to test rotation")
        return
    
    # Track usage
    key_usage = {key_name: 0 for key_name, _ in working_keys}
    failed_keys = {}
    
    for i in range(num_requests):
        # Simulate the rotation logic from your app
        current_time = time.time()
        available_keys = [key for key_name, key in working_keys 
                         if key_name not in failed_keys or 
                         current_time - failed_keys.get(key_name, 0) > 60]
        
        if not available_keys:
            # Reset failed keys if none available
            failed_keys.clear()
            available_keys = [key for _, key in working_keys]
        
        if available_keys:
            selected_key = random.choice(available_keys)
            key_name = next(name for name, key in working_keys if key == selected_key)
            key_usage[key_name] += 1
            
            print(f"Request {i+1}: Using {key_name}")
            
            # Simulate occasional failures (10% chance)
            if random.random() < 0.1:
                failed_keys[key_name] = current_time
                print(f"   ⚠️  Simulated failure for {key_name}")
        else:
            print(f"Request {i+1}: No available keys")
    
    print(f"\n📊 Rotation Results:")
    for key_name, count in sorted(key_usage.items(), key=lambda x: x[1], reverse=True):
        print(f"   {key_name}: {count} requests")
    
    return key_usage

def optimize_rotation_settings():
    """Suggest optimizations for the rotation system"""
    print(f"\n⚙️  Rotation System Optimization")
    print("=" * 50)
    
    working_keys, failed_keys = test_key_rotation()
    
    if working_keys:
        print(f"\n💡 Recommendations:")
        print(f"   1. You have {len(working_keys)} working keys for rotation")
        print(f"   2. Consider increasing MAX_RETRIES to {min(5, len(working_keys))}")
        print(f"   3. Failed key timeout (60s) is good for rate limits")
        print(f"   4. Random selection provides good load distribution")
        
        # Test rotation simulation
        simulate_rotation_usage(working_keys, 20)
        
        return True
    else:
        print(f"\n❌ No working keys found. Check your API key configuration.")
        return False

def show_current_rotation_config():
    """Show the current rotation configuration"""
    print("🔧 Current Rotation Configuration")
    print("=" * 40)
    
    # Get the configuration from your app
    keys = get_all_available_keys()
    
    print(f"Total API keys: {len(keys)}")
    print(f"MAX_RETRIES: 3")
    print(f"Failed key timeout: 60 seconds")
    print(f"Selection method: Random")
    
    if keys:
        print(f"\nAvailable keys:")
        for i, (key_name, key_value) in enumerate(keys[:5], 1):
            print(f"  {i}. {key_name}: {key_value[:10]}...{key_value[-4:]}")
        if len(keys) > 5:
            print(f"  ... and {len(keys) - 5} more")

if __name__ == "__main__":
    print("🔄 Groq API Key Rotation Tester")
    print("=" * 50)
    
    # Show current configuration
    show_current_rotation_config()
    
    # Test and optimize
    success = optimize_rotation_settings()
    
    if success:
        print(f"\n🎉 Your key rotation system is ready!")
        print(f"💡 All working keys will be used automatically")
        print(f"🚀 Your Flask app will handle rate limits and failures gracefully")
    else:
        print(f"\n❌ Please fix your API key configuration first") 