from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Import blueprints
from pain_cloud_realtime import pain_cloud_realtime_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///painradar.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Register blueprints
app.register_blueprint(pain_cloud_realtime_bp, url_prefix='/pain-cloud-realtime')

if __name__ == '__main__':
    app.run(debug=True)