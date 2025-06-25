import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from app import app, db, login_manager
from app_routes_enhanced import enhanced_routes

# Register the enhanced routes blueprint
app.register_blueprint(enhanced_routes)

# Add route to the enhanced RadarGPT page
@app.route('/enhanced')
def enhanced_home():
    return app.send_static_file('enhanced_index.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)