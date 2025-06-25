#!/usr/bin/env python3
"""
Production setup script for RadarGPT
"""

import os
import subprocess
import sys

def install_requirements():
    """Install production requirements"""
    print("📦 Installing production requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements-production.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        return False
    return True

def setup_environment():
    """Setup environment variables"""
    print("🔧 Setting up environment...")
    
    env_file = ".env"
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write("""# Production Environment Variables
SECRET_KEY=your-super-secret-production-key-2024
DATABASE_URL=sqlite:///production.db
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
""")
        print("✅ Created .env file - please update with your API keys")
    else:
        print("⚠️ .env file already exists")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = ["production_cache", "logs", "instance"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✅ Directories created")

def main():
    print("🏭 RadarGPT Production Setup")
    print("=" * 40)
    
    # Install requirements
    if not install_requirements():
        return
    
    # Setup environment
    setup_environment()
    
    # Create directories
    create_directories()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Update .env file with your OpenRouter API key")
    print("2. Run: python app_production.py")
    print("3. Access at: http://localhost:5000")
    print("\nFor production deployment:")
    print("- Use a proper WSGI server (Gunicorn, uWSGI)")
    print("- Set up HTTPS with a reverse proxy (Nginx)")
    print("- Configure Redis for rate limiting")
    print("- Set up monitoring and logging")

if __name__ == "__main__":
    main() 