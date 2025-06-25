#!/usr/bin/env python3
"""
Check database for chat records with incorrect role values
"""

import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app and create context
from app import app, db, QueryChat

def check_chat_roles():
    """Check for any chat records with incorrect role values"""
    with app.app_context():
        print("🔍 Checking QueryChat records for role values...")
        
        # Get all chat records
        chats = QueryChat.query.all()
        print(f"Total QueryChat records: {len(chats)}")
        
        # Check for invalid roles
        invalid_roles = []
        for chat in chats:
            if chat.role not in ['user', 'bot']:
                invalid_roles.append(chat)
        
        if invalid_roles:
            print(f"❌ Found {len(invalid_roles)} records with invalid roles:")
            for chat in invalid_roles:
                print(f"  ID: {chat.id}, Role: '{chat.role}', Text: '{chat.text[:50]}...'")
        else:
            print("✅ All QueryChat records have valid roles ('user' or 'bot')")
        
        # Show some sample records
        print("\n📋 Sample QueryChat records:")
        sample_chats = QueryChat.query.limit(10).all()
        for chat in sample_chats:
            print(f"  ID: {chat.id}, Role: '{chat.role}', Text: '{chat.text[:50]}...'")

if __name__ == "__main__":
    check_chat_roles() 