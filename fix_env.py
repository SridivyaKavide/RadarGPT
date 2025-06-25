#!/usr/bin/env python3
"""
Script to fix .env file formatting issues
"""

import os
import re

def fix_env_file():
    """Fix .env file formatting issues"""
    
    print("🔧 Fixing .env file formatting issues")
    print("=" * 50)
    
    # Check if .env exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    # Read current .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    # Fix the formatting issues
    lines = content.split('\n')
    fixed_lines = []
    
    # Add missing GROQ_API_KEY (use the first rotation key as fallback)
    groq_keys = []
    
    for line in lines:
        # Fix spaces around = signs for GROQ_API_KEY lines
        if line.startswith('GROQ_API_KEY_') and ' = ' in line:
            # Remove spaces around = sign
            fixed_line = line.replace(' = ', '=')
            fixed_lines.append(fixed_line)
            
            # Extract the key value for fallback
            if '=' in fixed_line:
                key_value = fixed_line.split('=', 1)[1].strip()
                if key_value.startswith('gsk_'):
                    groq_keys.append(key_value)
        else:
            fixed_lines.append(line)
    
    # Add the missing GROQ_API_KEY at the beginning
    if groq_keys:
        # Use the first key as the fallback
        fallback_key = groq_keys[0]
        fixed_lines.insert(0, f"GROQ_API_KEY={fallback_key}")
        print(f"✅ Added missing GROQ_API_KEY={fallback_key[:10]}...{fallback_key[-4:]}")
    
    # Write fixed content back to .env
    fixed_content = '\n'.join(fixed_lines)
    with open('.env', 'w') as f:
        f.write(fixed_content)
    
    print(f"✅ Fixed {len(groq_keys)} GROQ_API_KEY lines")
    print("💡 Removed spaces around = signs")
    print("💡 Added missing GROQ_API_KEY fallback")
    
    return True

def verify_fix():
    """Verify the fix worked"""
    print("\n🔍 Verifying the fix...")
    print("=" * 30)
    
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Check main key
    main_key = os.getenv('GROQ_API_KEY')
    if main_key:
        print(f"✅ GROQ_API_KEY found: {main_key[:10]}...{main_key[-4:]}")
    else:
        print("❌ GROQ_API_KEY still missing")
    
    # Check rotation keys
    rotation_keys = []
    for i in range(1, 30):
        key = os.getenv(f'GROQ_API_KEY_{i}')
        if key and key.startswith('gsk_'):
            rotation_keys.append(key)
    
    print(f"✅ Found {len(rotation_keys)} rotation keys")
    
    if main_key and rotation_keys:
        print("🎉 All API keys are properly configured!")
        return True
    else:
        print("❌ Some keys are still missing or invalid")
        return False

if __name__ == "__main__":
    print("🔧 Fixing .env file formatting issues")
    print("=" * 50)
    
    # Fix the file
    success = fix_env_file()
    
    if success:
        # Verify the fix
        verify_fix()
        
        print("\n💡 Your Flask app should now work correctly!")
        print("🚀 Try running your Flask app again")
    else:
        print("\n❌ Failed to fix .env file") 