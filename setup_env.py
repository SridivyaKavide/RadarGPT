#!/usr/bin/env python3
"""
Script to help set up .env file with Groq API keys
"""

def create_env_template():
    """Create a template .env file with the correct format"""
    
    print("🔧 Setting up .env file for Groq API keys")
    print("=" * 60)
    print()
    print("📝 Copy and paste your API keys into the .env file like this:")
    print()
    
    # Create template
    template = """# Groq API Keys
# Replace the 'gsk_...' placeholders with your actual API keys

# Single key (fallback)
GROQ_API_KEY=gsk_your_actual_key_here

# Rotation keys (for automatic key rotation)
GROQ_API_KEY_1=gsk_your_first_key_here
GROQ_API_KEY_2=gsk_your_second_key_here
GROQ_API_KEY_3=gsk_your_third_key_here
GROQ_API_KEY_4=gsk_your_fourth_key_here
GROQ_API_KEY_5=gsk_your_fifth_key_here
GROQ_API_KEY_6=gsk_your_sixth_key_here
GROQ_API_KEY_7=gsk_your_seventh_key_here
GROQ_API_KEY_8=gsk_your_eighth_key_here
GROQ_API_KEY_9=gsk_your_ninth_key_here
GROQ_API_KEY_10=gsk_your_tenth_key_here
GROQ_API_KEY_11=gsk_your_eleventh_key_here
GROQ_API_KEY_12=gsk_your_twelfth_key_here
GROQ_API_KEY_13=gsk_your_thirteenth_key_here
GROQ_API_KEY_14=gsk_your_fourteenth_key_here
GROQ_API_KEY_15=gsk_your_fifteenth_key_here
GROQ_API_KEY_16=gsk_your_sixteenth_key_here
GROQ_API_KEY_17=gsk_your_seventeenth_key_here
GROQ_API_KEY_18=gsk_your_eighteenth_key_here
GROQ_API_KEY_19=gsk_your_nineteenth_key_here
GROQ_API_KEY_20=gsk_your_twentieth_key_here
GROQ_API_KEY_21=gsk_your_twenty_first_key_here
GROQ_API_KEY_22=gsk_your_twenty_second_key_here
GROQ_API_KEY_23=gsk_your_twenty_third_key_here
GROQ_API_KEY_24=gsk_your_twenty_fourth_key_here
GROQ_API_KEY_25=gsk_your_twenty_fifth_key_here
GROQ_API_KEY_26=gsk_your_twenty_sixth_key_here
GROQ_API_KEY_27=gsk_your_twenty_seventh_key_here
GROQ_API_KEY_28=gsk_your_twenty_eighth_key_here
GROQ_API_KEY_29=gsk_your_twenty_ninth_key_here

# Other environment variables
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
POSTGRES_DATABASE_URI=your_postgres_connection_string
"""
    
    print(template)
    print("=" * 60)
    print("💡 Instructions:")
    print("1. Create a file named '.env' in your project root")
    print("2. Copy the template above into the .env file")
    print("3. Replace 'gsk_your_actual_key_here' with your real API keys")
    print("4. Make sure there are no spaces around the '=' sign")
    print("5. Don't add quotes around the API keys")
    print("6. Save the file and restart your Flask app")
    print()
    print("🔑 Based on your dashboard, you have these keys available:")
    print("   - 14, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30")
    print("   - Radar, Radar1, Radar2, Radar3, Radar5, Radar6, Radar7, Radar8, Radar9, Radar10, Radar11, Radar12, Radar13")
    print()
    print("📋 Example with your actual keys:")
    print("GROQ_API_KEY=gsk_...c6mc")
    print("GROQ_API_KEY_1=gsk_...X10U")
    print("GROQ_API_KEY_2=gsk_...icF6")
    print("# ... continue with all your keys")

def check_current_env():
    """Check if .env file exists and show current setup"""
    import os
    
    print("🔍 Checking current .env setup...")
    print("=" * 40)
    
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            groq_lines = [line for line in lines if line.startswith('GROQ_API_KEY') and '=' in line]
            if groq_lines:
                print(f"✅ Found {len(groq_lines)} GROQ_API_KEY lines")
                for line in groq_lines[:5]:  # Show first 5
                    key_name, key_value = line.split('=', 1)
                    if key_value.strip() and not key_value.strip().startswith('gsk_your'):
                        print(f"   {key_name}: {key_value.strip()[:10]}...{key_value.strip()[-4:]}")
                    else:
                        print(f"   {key_name}: NOT SET (placeholder)")
            else:
                print("❌ No GROQ_API_KEY lines found")
    else:
        print("❌ .env file not found")
        print("💡 Create a .env file in your project root")

if __name__ == "__main__":
    check_current_env()
    print()
    create_env_template() 