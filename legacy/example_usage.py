#!/usr/bin/env python3
"""
Example script for using Chrome Profile Manager API
"""
from chromix import ChromeProfileAPI
import subprocess
import platform

# Initialize API
api = ChromeProfileAPI()

# Get profile by ID
profile_id = "profile_abc123"  # Replace with actual profile ID
profile = api.get_profile(profile_id)

if profile:
    print(f"Using profile: {profile['name']}")
    
    # Get Chrome arguments
    chrome_args = api.get_chrome_args(profile_id)
    
    # Get Chrome path based on OS
    if platform.system() == "Windows":
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif platform.system() == "Darwin":
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        chrome_path = "/usr/bin/google-chrome"
    
    # Launch Chrome
    cmd = [chrome_path] + chrome_args + ["https://example.com"]
    subprocess.Popen(cmd)
    
    # Get current proxy (for logging or other use)
    proxy = api.get_next_proxy(profile_id)
    if proxy:
        print(f"Using proxy: {proxy['host']}:{proxy['port']}")
else:
    print("Profile not found!")

# For Selenium example:
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
for arg in chrome_args:
    chrome_options.add_argument(arg)

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://example.com")
"""
