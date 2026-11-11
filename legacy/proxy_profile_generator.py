#!/usr/bin/env python3
"""
Generate proxy profiles with random names for Chrome Profile Manager
"""

import random
import json

# Your proxy list
proxies = [
    "38.154.227.167:5868:jcuieang:1dt1dya9ckqi",
    "198.23.239.134:6540:jcuieang:1dt1dya9ckqi",
    "207.244.217.165:6712:jcuieang:1dt1dya9ckqi",
    "107.172.163.27:6543:jcuieang:1dt1dya9ckqi",
    "216.10.27.159:6837:jcuieang:1dt1dya9ckqi",
    "136.0.207.84:6661:jcuieang:1dt1dya9ckqi",
    "64.64.118.149:6732:jcuieang:1dt1dya9ckqi",
    "142.147.128.93:6593:jcuieang:1dt1dya9ckqi",
    "104.239.105.125:6655:jcuieang:1dt1dya9ckqi",
    "206.41.172.74:6634:jcuieang:1dt1dya9ckqi"
]

# Lists for generating random names
first_names = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel",
    "India", "Juliet", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa",
    "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey",
    "Phoenix", "Thunder", "Storm", "Shadow", "Lightning", "Falcon", "Eagle",
    "Tiger", "Dragon", "Wolf", "Bear", "Hawk", "Panther", "Cobra", "Viper"
]

last_names = [
    "Runner", "Blazer", "Striker", "Hunter", "Ranger", "Warrior", "Fighter",
    "Raider", "Crusher", "Defender", "Guardian", "Protector", "Sentinel",
    "Watcher", "Keeper", "Master", "Chief", "Captain", "Major", "Colonel",
    "Prime", "Elite", "Ultra", "Supreme", "Ultimate", "Extreme", "Maximum"
]

colors = [
    "Red", "Blue", "Green", "Black", "White", "Silver", "Gold", "Purple",
    "Orange", "Yellow", "Crimson", "Azure", "Emerald", "Onyx", "Pearl"
]

# Country mapping based on your screenshot
country_mapping = {
    "38.154.227.167": ("United States", "Piscataway"),
    "198.23.239.134": ("United States", "Buffalo"),
    "207.244.217.165": ("Croatia", "Zagreb"),
    "107.172.163.27": ("United States", "Bloomingdale"),
    "216.10.27.159": ("United States", "Dallas"),
    "136.0.207.84": ("United States", "Orem"),
    "64.64.118.149": ("United States", "Greenlawn"),
    "142.147.128.93": ("United States", "Ashburn"),
    "104.239.105.125": ("United States", "Dallas"),
    "206.41.172.74": ("France", "Paris")
}

def generate_random_name():
    """Generate a random profile name"""
    # Different name generation patterns
    patterns = [
        lambda: f"{random.choice(colors)} {random.choice(first_names)}",
        lambda: f"{random.choice(first_names)} {random.choice(last_names)}",
        lambda: f"{random.choice(colors)} {random.choice(first_names)} {random.choice(last_names)}",
        lambda: f"{random.choice(first_names)}-{random.randint(100, 999)}",
        lambda: f"{random.choice(colors)}{random.choice(first_names)}{random.randint(10, 99)}"
    ]
    
    return random.choice(patterns)()

def create_import_file_with_names():
    """Create import file with base names for batch import"""
    print("=== PROXY IMPORT FILE WITH RANDOM BASE NAME ===\n")
    
    base_name = generate_random_name()
    print(f"Base Name for Import: {base_name}\n")
    
    print("Proxy List:")
    print("-" * 50)
    
    with open("proxies_import.txt", "w") as f:
        for proxy in proxies:
            f.write(proxy + "\n")
            print(proxy)
    
    print("-" * 50)
    print(f"\nSaved to: proxies_import.txt")
    print(f"Use '{base_name}' as the base name when importing")
    print("\nProfiles will be created as:")
    for i in range(1, 11):
        print(f"  - {base_name} #{i}")

def create_individual_profiles():
    """Create individual profile configurations with unique random names"""
    profiles = []
    
    print("\n\n=== INDIVIDUAL PROFILES WITH UNIQUE NAMES ===\n")
    
    for i, proxy in enumerate(proxies):
        parts = proxy.split(':')
        host = parts[0]
        port = parts[1]
        username = parts[2]
        password = parts[3]
        
        # Get location info
        country, city = country_mapping.get(host, ("Unknown", "Unknown"))
        
        # Generate unique name
        name = generate_random_name()
        
        profile = {
            "name": name,
            "proxy": proxy,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "country": country,
            "city": city,
            "status": "Working"
        }
        
        profiles.append(profile)
        print(f"{i+1}. {name}")
        print(f"   Proxy: {host}:{port}")
        print(f"   Location: {city}, {country}")
        print(f"   Status: Working\n")
    
    # Save as JSON
    with open("profiles_config.json", "w") as f:
        json.dump(profiles, f, indent=2)
    
    print(f"Saved {len(profiles)} profiles to: profiles_config.json")
    
    return profiles

def create_simple_import():
    """Create a simple import file for the Chrome Profile Manager"""
    print("\n\n=== SIMPLE IMPORT FORMAT ===\n")
    print("Copy and paste this into the Chrome Profile Manager:")
    print("-" * 60)
    
    for proxy in proxies:
        print(proxy)
    
    print("-" * 60)

def main():
    print("Chrome Profile Manager - Bulk Profile Generator")
    print("=" * 60)
    
    # Generate all formats
    create_import_file_with_names()
    create_individual_profiles()
    create_simple_import()
    
    print("\n\n=== HOW TO USE ===")
    print("1. For Chrome Profile Manager Enterprise:")
    print("   - Click 'Batch Import'")
    print("   - Copy the proxies from above or use 'proxies_import.txt'")
    print("   - Enter a base name (or use the suggested random name)")
    print("   - Click Import")
    print("\n2. For programmatic use:")
    print("   - Use 'profiles_config.json' with the API")
    print("\n3. All profiles will be created with:")
    print("   - Random unique names")
    print("   - Correct proxy configuration")
    print("   - Location information")
    print("   - Ready for auto-authentication setup")

if __name__ == "__main__":
    main()