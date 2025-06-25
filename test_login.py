from app import app, db, User
from flask_login import login_user
from flask import session, request
import requests

def test_login():
    client = app.test_client()
    with app.app_context():
        # Get a test user
        user = User.query.first()
        print('Found user:', user.username if user else None)
        
        # Try to login using session transaction
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            print('Session after setting user_id:', dict(sess))
        
        # Test the analytics endpoint
        response = client.get('/api/analytics?period=7d&persona=all')
        print('Analytics response status:', response.status_code)
        print('Analytics response headers:', dict(response.headers))
        print('Analytics response content:', response.data[:200])

if __name__ == '__main__':
    test_login() 