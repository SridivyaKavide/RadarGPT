import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from app import app, db, login_manager
from app_routes_fast import fast_routes

# Load environment variables
load_dotenv()

# Register the fast routes blueprint
app.register_blueprint(fast_routes)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)