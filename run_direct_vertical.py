import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from app import app, db, login_manager
from direct_vertical_insights import direct_vertical_routes

# Load environment variables
load_dotenv()

# Register the direct vertical routes blueprint
app.register_blueprint(direct_vertical_routes)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)