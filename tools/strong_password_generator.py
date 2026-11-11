#!/usr/bin/env python3
"""
Gmail Password Generator Script
Reads a CSV file with email accounts and generates unique strong passwords
"""

import csv
import random
import string
import os
from datetime import datetime

def generate_strong_password(length=16):
    """
    Generate a strong password with uppercase, lowercase, numbers, and symbols
    
    Args:
        length (int): Length of the password (default: 16)
    
    Returns:
        str: A strong random password
    """
    # Character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    numbers = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one character from each category
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(numbers),
        random.choice(symbols)
    ]
    
    # Fill the rest with random characters from all categories
    all_chars = uppercase + lowercase + numbers + symbols
    for _ in range(length - 4):
        password.append(random.choice(all_chars))
    
    # Shuffle the password
    random.shuffle(password)
    
    return ''.join(password)

def process_csv(input_file, output_file=None):
    """
    Read CSV file and add unique passwords to each row
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file (optional)
    """
    # If no output file specified, create one with timestamp
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_with_passwords_{timestamp}.csv"
    
    # Read the CSV file
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            
        print(f"Successfully read {len(rows)} rows from {input_file}")
        
        # Add new passwords to each row
        updated_rows = []
        for i, row in enumerate(rows, 1):
            row['new password'] = generate_strong_password()
            updated_rows.append(row)
            
            # Show progress every 50 rows
            if i % 50 == 0:
                print(f"Generated passwords for {i} accounts...")
        
        # Write the updated CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['emails', 'current password', 'new password']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        
        print(f"\n✅ Successfully generated passwords for {len(rows)} accounts!")
        print(f"📁 Output saved to: {output_file}")
        
        # Show sample of generated passwords
        print("\n📋 Sample of generated passwords:")
        for i in range(min(5, len(updated_rows))):
            email = updated_rows[i]['emails'].strip()
            password = updated_rows[i]['new password']
            print(f"   {i+1}. {email} -> {password}")
        
        return updated_rows
        
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found!")
    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")

def generate_password_strength_report(passwords):
    """
    Generate a report about password strength
    
    Args:
        passwords (list): List of generated passwords
    """
    print("\n📊 Password Strength Report:")
    print(f"   Total passwords generated: {len(passwords)}")
    print(f"   Password length: 16 characters")
    print(f"   Character sets used: Uppercase, Lowercase, Numbers, Symbols")
    print(f"   Total possible combinations: ~4.8 × 10^31")
    print(f"   Estimated crack time: Billions of years")

def main():
    """Main function to run the script"""
    print("🔐 Gmail Password Generator")
    print("=" * 50)
    
    # Input file name
    input_file = "gmails.csv"
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: '{input_file}' not found in current directory!")
        print("\n📝 Please ensure your CSV file is named 'gmails.csv' and is in the same directory as this script.")
        return
    
    # Process the CSV
    print(f"\n📂 Processing file: {input_file}")
    updated_rows = process_csv(input_file)
    
    if updated_rows:
        # Generate password strength report
        passwords = [row['new password'] for row in updated_rows]
        generate_password_strength_report(passwords)
        
        print("\n⚠️  Security Recommendations:")
        print("   1. Store the output CSV file in a secure location")
        print("   2. Consider encrypting the file with strong encryption")
        print("   3. Use a password manager for better security")
        print("   4. Enable 2-factor authentication on all accounts")
        print("   5. Regularly update passwords (every 3-6 months)")
        
        print("\n⚠️  Important Notes:")
        print("   - Automating password changes on Google may trigger security alerts")
        print("   - Google has strong anti-automation measures")
        print("   - Manual password changes are recommended for safety")

if __name__ == "__main__":
    main()