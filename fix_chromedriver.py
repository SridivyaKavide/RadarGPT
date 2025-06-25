#!/usr/bin/env python3
"""
Fix ChromeDriver Windows compatibility issue
"""

import os
import shutil
import platform
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def clean_chromedriver_cache():
    """Clean the ChromeDriver cache to fix Windows path issues"""
    print("🧹 Cleaning ChromeDriver cache...")
    
    # Clean webdriver-manager cache
    cache_dir = os.path.expanduser("~/.wdm")
    if os.path.exists(cache_dir):
        print(f"Removing cache directory: {cache_dir}")
        shutil.rmtree(cache_dir)
        print("✅ Cache cleaned")
    else:
        print("No cache directory found")
    
    # Clean any existing chromedriver processes
    try:
        os.system("taskkill /f /im chromedriver.exe 2>nul")
        print("✅ Killed any existing ChromeDriver processes")
    except:
        pass

def test_chromedriver_installation():
    """Test ChromeDriver installation"""
    print("\n🧪 Testing ChromeDriver installation...")
    
    try:
        # Install ChromeDriver
        driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver installed at: {driver_path}")
        
        # Check if path contains problematic files
        if "THIRD_PARTY_NOTICES" in driver_path:
            print("⚠️  Path contains THIRD_PARTY_NOTICES - this might cause issues")
            return False
        
        # Test with Selenium
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Test a simple page load
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ ChromeDriver test successful - loaded: {title}")
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver test failed: {e}")
        return False

def fix_chromedriver():
    """Main fix function"""
    print("🔧 Fixing ChromeDriver Windows compatibility...")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Clean cache
    clean_chromedriver_cache()
    
    # Test installation
    success = test_chromedriver_installation()
    
    if success:
        print("\n🎉 ChromeDriver fix successful!")
        print("Your application should now work without ChromeDriver errors.")
    else:
        print("\n❌ ChromeDriver fix failed.")
        print("Try running this script again, or manually install ChromeDriver.")
    
    return success

if __name__ == "__main__":
    fix_chromedriver() 