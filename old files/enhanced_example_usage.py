#!/usr/bin/env python3
"""
Enhanced example script for Chrome Profile Manager with captcha handling
"""
from enhanced_chrome_profile_manager import EnhancedChromeProfileAPI
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Initialize API
api = EnhancedChromeProfileAPI()

# Configuration
profile_id = "profile_87c1c3a3999f"  # Use your actual profile ID
captcha_api_key = "YOUR_2CAPTCHA_API_KEY"  # Optional: for automated solving

# Get Selenium driver with profile
driver = api.get_selenium_driver(profile_id, headless=False)

if driver:
    try:
        # Navigate to target site
        driver.get("https://example.com")
        
        # Wait for page load
        wait = WebDriverWait(driver, 10)
        
        # Check for captcha
        try:
            captcha_element = driver.find_element(By.CLASS_NAME, "g-recaptcha")
            print("Captcha detected!")
            
            # Handle captcha (manual or automated)
            api.handle_captcha(driver, "recaptcha", captcha_api_key)
            
        except:
            print("No captcha found, proceeding...")
        
        # Your automation logic here
        print(f"Current IP: {driver.find_element(By.TAG_NAME, 'body').text}")
        
        # Keep browser open for debugging
        input("Press Enter to close browser...")
        
    finally:
        driver.quit()
else:
    print("Profile not found!")

# For handling multiple profiles with rotation
def run_multiple_profiles(profile_ids, target_url):
    """Run automation on multiple profiles"""
    for profile_id in profile_ids:
        print(f"\nRunning profile: {profile_id}")
        
        driver = api.get_selenium_driver(profile_id)
        if not driver:
            continue
        
        try:
            driver.get(target_url)
            
            # Handle potential captcha
            time.sleep(2)  # Wait for captcha to load
            
            # Your automation logic here
            # ...
            
            time.sleep(5)  # Simulate work
            
        except Exception as e:
            print(f"Error with profile {profile_id}: {e}")
        
        finally:
            driver.quit()
            time.sleep(2)  # Delay between profiles

# Example: Run all profiles
all_profiles = ["profile_87c1c3a3999f", "profile_xyz123"]  # Your profile IDs
run_multiple_profiles(all_profiles, "https://example.com")
