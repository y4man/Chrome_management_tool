#!/usr/bin/env python3
"""
Example: Using Chrome profiles in your scripts
"""
from chrome_profile_manager_fixed import ChromeProfileAPI
import subprocess
import platform

# Initialize API
api = ChromeProfileAPI()

# Your profile ID (copy from the app)
profile_id = "profile_87c1c3a3999f"

# Get profile
profile = api.get_profile(profile_id)
if profile:
    print(f"Using profile: {profile['name']}")
    
    # Get Chrome args
    chrome_args = api.get_chrome_args(profile_id)
    
    # Get Chrome path
    if platform.system() == "Windows":
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    else:
        chrome_path = "/usr/bin/google-chrome"
    
    # Launch Chrome
    cmd = [chrome_path] + chrome_args + ["https://example.com"]
    subprocess.Popen(cmd)
    
    print("Chrome launched with profile!")
else:
    print("Profile not found!")
