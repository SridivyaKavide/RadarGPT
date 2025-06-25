#!/usr/bin/env python3
"""
Fix database records with incorrect role values
"""

import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app and create context
from app import app, db, QueryChat

def fix_chat_roles():
    """Fix chat records with incorrect role values"""
    with app.app_context():
        print("🔧 Fixing QueryChat records with incorrect role values...")
        
        # Find records with 'model' role and change them to 'bot'
        model_chats = QueryChat.query.filter_by(role='model').all()
        print(f"Found {len(model_chats)} records with role 'model'")
        
        if model_chats:
            for chat in model_chats:
                print(f"  Fixing ID {chat.id}: 'model' -> 'bot'")
                chat.role = 'bot'
            
            # Commit the changes
            db.session.commit()
            print(f"✅ Fixed {len(model_chats)} records")
        else:
            print("✅ No records to fix")
        
        # Verify the fix
        print("\n🔍 Verifying fix...")
        remaining_model_chats = QueryChat.query.filter_by(role='model').all()
        if remaining_model_chats:
            print(f"❌ Still have {len(remaining_model_chats)} records with 'model' role")
        else:
            print("✅ All records now have valid roles")
        
        # Show some sample records
        print("\n📋 Sample QueryChat records after fix:")
        sample_chats = QueryChat.query.all()[:10]
        for chat in sample_chats:
            print(f"  ID: {chat.id}, Role: '{chat.role}', Text: '{chat.text[:50]}...'")

if __name__ == "__main__":
    fix_chat_roles() 