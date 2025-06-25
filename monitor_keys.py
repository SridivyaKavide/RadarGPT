#!/usr/bin/env python3
"""
Monitor Groq API key usage and rate limit status
"""

import os
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def get_key_status():
    """Get status of all API keys"""
    print("🔍 Monitoring Groq API Key Status")
    print("=" * 50)
    
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
    
    print(f"📊 Found {len(keys)} API keys")
    
    # Test each key
    working_keys = []
    rate_limited_keys = []
    failed_keys = []
    
    for key_name, key_value in keys:
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
            working_keys.append(key_name)
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
                print(f"   ⚠️  Rate Limited")
                rate_limited_keys.append(key_name)
            elif '401' in error_str or 'unauthorized' in error_str:
                print(f"   ❌ Invalid Key")
                failed_keys.append(key_name)
            else:
                print(f"   ❌ Error: {e}")
                failed_keys.append(key_name)
    
    print(f"\n📈 Summary:")
    print(f"   ✅ Working keys: {len(working_keys)}")
    print(f"   ⚠️  Rate limited keys: {len(rate_limited_keys)}")
    print(f"   ❌ Failed keys: {len(failed_keys)}")
    
    if rate_limited_keys:
        print(f"\n⚠️  Rate Limited Keys:")
        for key in rate_limited_keys[:5]:  # Show first 5
            print(f"   - {key}")
        if len(rate_limited_keys) > 5:
            print(f"   ... and {len(rate_limited_keys) - 5} more")
    
    if failed_keys:
        print(f"\n❌ Failed Keys:")
        for key in failed_keys[:5]:  # Show first 5
            print(f"   - {key}")
        if len(failed_keys) > 5:
            print(f"   ... and {len(failed_keys) - 5} more")
    
    return working_keys, rate_limited_keys, failed_keys

def suggest_optimizations(working_keys, rate_limited_keys, failed_keys):
    """Suggest optimizations based on current status"""
    print(f"\n💡 Optimization Suggestions:")
    print("=" * 40)
    
    total_keys = len(working_keys) + len(rate_limited_keys) + len(failed_keys)
    
    if len(working_keys) >= 20:
        print(f"✅ Excellent! You have {len(working_keys)} working keys")
        print(f"   - Your rotation system should handle load well")
        print(f"   - Consider increasing request frequency")
    elif len(working_keys) >= 10:
        print(f"⚠️  Good! You have {len(working_keys)} working keys")
        print(f"   - Monitor rate limits closely")
        print(f"   - Consider adding more API keys if needed")
    else:
        print(f"❌ Low! Only {len(working_keys)} working keys")
        print(f"   - Consider adding more API keys")
        print(f"   - Reduce request frequency")
    
    if len(rate_limited_keys) > 0:
        print(f"\n⚠️  Rate Limited Keys: {len(rate_limited_keys)}")
        print(f"   - These keys will be available again in 5 minutes")
        print(f"   - The rotation system will automatically skip them")
    
    if len(failed_keys) > 0:
        print(f"\n❌ Failed Keys: {len(failed_keys)}")
        print(f"   - These keys may be invalid or revoked")
        print(f"   - Consider removing them from your .env file")
    
    # Calculate availability percentage
    availability = (len(working_keys) / total_keys) * 100 if total_keys > 0 else 0
    print(f"\n📊 Overall Availability: {availability:.1f}%")
    
    if availability >= 80:
        print(f"   🟢 Excellent availability")
    elif availability >= 60:
        print(f"   🟡 Good availability")
    else:
        print(f"   🔴 Low availability - consider adding more keys")

def monitor_continuously(interval=60):
    """Monitor keys continuously"""
    print(f"\n🔄 Starting continuous monitoring (every {interval} seconds)")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        while True:
            working_keys, rate_limited_keys, failed_keys = get_key_status()
            suggest_optimizations(working_keys, rate_limited_keys, failed_keys)
            
            print(f"\n⏰ Next check in {interval} seconds...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Monitoring stopped")

if __name__ == "__main__":
    print("🔍 Groq API Key Monitor")
    print("=" * 50)
    
    # One-time status check
    working_keys, rate_limited_keys, failed_keys = get_key_status()
    suggest_optimizations(working_keys, rate_limited_keys, failed_keys)
    
    # Ask if user wants continuous monitoring
    response = input(f"\n🔄 Start continuous monitoring? (y/n): ").strip().lower()
    if response == 'y':
        interval = input("Enter monitoring interval in seconds (default 60): ").strip()
        try:
            interval = int(interval) if interval else 60
        except ValueError:
            interval = 60
        
        monitor_continuously(interval)
    else:
        print("💡 Run this script again anytime to check key status") 