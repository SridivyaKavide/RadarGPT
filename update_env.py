#!/usr/bin/env python3
"""
Script to help update .env file with actual API keys
"""

import os
import re

def update_env_file():
    """Update .env file with actual API keys"""
    
    print("🔧 Updating .env file with actual API keys")
    print("=" * 50)
    
    # Check if .env exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    # Read current .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    # Find all GROQ_API_KEY lines
    lines = content.split('\n')
    updated_lines = []
    
    # Your actual API keys (replace with your real keys)
    actual_keys = [
        "gsk_...c6mc",    # 14
        "gsk_...X10U",    # 14
        "gsk_...icF6",    # 16
        "gsk_...HEpu",    # 17
        "gsk_...svPv",    # 18
        "gsk_...bvXt",    # 19
        "gsk_...k92S",    # 20
        "gsk_...oic6",    # 21
        "gsk_...oHiG",    # 22
        "gsk_...ljbt",    # 23
        "gsk_...DfyT",    # 24
        "gsk_...JklO",    # 25
        "gsk_...0STN",    # 26
        "gsk_...H0M0",    # 27
        "gsk_...FX4p",    # 28
        "gsk_...zUxg",    # 30
        "gsk_...1ssm",    # Radar
        "gsk_...oRIB",    # Radar1
        "gsk_...7BLq",    # Radar10
        "gsk_...gU9u",    # Radar11
        "gsk_...dYQM",    # Radar12
        "gsk_...bfPf",    # Radar13
        "gsk_...uxv4",    # Radar2
        "gsk_...6nWl",    # Radar3
        "gsk_...YeOP",    # Radar5
        "gsk_...xqXw",    # Radar6
        "gsk_...zfbH",    # Radar7
        "gsk_...Vv65",    # Radar8
        "gsk_...6e6r",    # Radar9
    ]
    
    key_index = 0
    
    for line in lines:
        if line.startswith('GROQ_API_KEY') and '=' in line:
            if key_index < len(actual_keys):
                # Replace the placeholder with actual key
                key_name = line.split('=')[0]
                updated_line = f"{key_name}={actual_keys[key_index]}"
                updated_lines.append(updated_line)
                print(f"✅ Updated {key_name} with actual key")
                key_index += 1
            else:
                # Keep original line if we run out of keys
                updated_lines.append(line)
        else:
            # Keep non-GROQ lines unchanged
            updated_lines.append(line)
    
    # Write updated content back to .env
    updated_content = '\n'.join(updated_lines)
    with open('.env', 'w') as f:
        f.write(updated_content)
    
    print(f"\n✅ Updated {key_index} API keys in .env file")
    print("💡 You can now restart your Flask app")
    
    return True

def show_current_keys():
    """Show current API keys in .env file"""
    print("🔍 Current API keys in .env file:")
    print("=" * 40)
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return
    
    with open('.env', 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    groq_lines = [line for line in lines if line.startswith('GROQ_API_KEY') and '=' in line]
    
    for line in groq_lines[:10]:  # Show first 10
        key_name, key_value = line.split('=', 1)
        if key_value.strip().startswith('gsk_'):
            print(f"✅ {key_name}: {key_value.strip()[:10]}...{key_value.strip()[-4:]}")
        else:
            print(f"❌ {key_name}: PLACEHOLDER (needs update)")

if __name__ == "__main__":
    print("⚠️  IMPORTANT: You need to replace the placeholder keys with your actual API keys!")
    print("📋 Copy your actual API keys from your Groq dashboard and replace the placeholders below.")
    print()
    
    show_current_keys()
    print()
    
    # Ask user if they want to update
    response = input("Do you want to update the .env file with your actual API keys? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n🔧 Please replace the placeholder keys in the script with your actual API keys first!")
        print("📝 Edit the 'actual_keys' list in update_env.py with your real keys")
        print("💡 Then run this script again")
    else:
        print("💡 You can manually edit the .env file to replace the placeholder values with your actual API keys") 