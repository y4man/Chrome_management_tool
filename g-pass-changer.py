import csv
import time
import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('password_change_log.txt'),
        logging.StreamHandler()
    ]
)

class GmailPasswordChanger:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.success_count = 0
        self.failure_count = 0
        self.bad_emails = []  # Cannot login
        self.password_change_failed = []  # Login OK but password change failed
        self.successful_accounts = []
        
    def get_chrome_options(self):
        """Get Chrome options for each new instance"""
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional options to appear more human-like
        prefs = {"credentials_enable_service": False,
                 "profile.password_manager_enabled": False}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument('--disable-features=ChromeWhatsNewUI')
        
        return chrome_options
    
    def human_delay(self, min_seconds=0.5, max_seconds=1.5):
        """Add human-like delay"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def type_like_human(self, element, text):
        """Type text character by character with human-like delays"""
        element.click()
        self.human_delay(0.2, 0.5)
        element.clear()
        self.human_delay(0.2, 0.5)
        
        for char in text:
            element.send_keys(char)
            self.human_delay(0.05, 0.15)
    
    def read_csv(self):
        """Read email credentials from CSV file"""
        accounts = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    accounts.append({
                        'email': row['emails'].strip(),
                        'current_password': row['current password'].strip(),
                        'new_password': row['new password'].strip()
                    })
            logging.info(f"Loaded {len(accounts)} accounts from CSV")
            return accounts
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
            return []
    
    def wait_for_page_load(self, driver, timeout=10):
        """Wait for page to load completely"""
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
    
    def handle_popups(self, driver):
        """Handle various popups that might appear"""
        popup_handled = False
        
        # List of popup selectors to try
        popup_selectors = [
            "//button[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'I agree')]",
            "//button[contains(text(), 'Got it')]",
            "//div[@role='button'][contains(text(), 'Continue')]",
            "//span[contains(text(), 'Continue')]//parent::button"
        ]
        
        for selector in popup_selectors:
            try:
                popup = driver.find_element(By.XPATH, selector)
                if popup.is_displayed() and popup.is_enabled():
                    popup.click()
                    popup_handled = True
                    logging.info("Handled popup")
                    self.human_delay(1, 2)
                    break
            except:
                continue
        
        return popup_handled
    
    def check_for_captcha(self, driver):
        """Check for CAPTCHA and wait for manual solving"""
        captcha_selectors = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[@class='g-recaptcha']",
            "//*[contains(text(), 'I\'m not a robot')]"
        ]
        
        for selector in captcha_selectors:
            try:
                driver.find_element(By.XPATH, selector)
                print("\n⚠️ CAPTCHA DETECTED!")
                print("Please solve the CAPTCHA manually.")
                print("Press ENTER after solving...")
                input()
                self.human_delay(1, 2)
                return True
            except:
                continue
        return False
    
    def login_to_gmail(self, driver, email, password):
        """Attempt to login to Gmail with better error handling"""
        try:
            # Navigate to Gmail
            logging.info(f"Opening Gmail login for: {email}")
            driver.get("https://accounts.google.com/signin/v2/identifier")
            self.wait_for_page_load(driver)
            self.human_delay(2, 3)
            
            # STEP 1: Enter Email
            try:
                # Wait for email field
                email_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "identifierId"))
                )
                
                # Make sure field is interactable
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "identifierId"))
                )
                
                logging.info("Entering email...")
                self.type_like_human(email_field, email)
                
                # Click Next button
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "identifierNext"))
                )
                next_button.click()
                
                self.wait_for_page_load(driver)
                self.human_delay(3, 5)
                
            except TimeoutException:
                logging.error(f"Email field not found for: {email}")
                return False
            
            # Check for CAPTCHA
            self.check_for_captcha(driver)
            
            # Check for account not found error
            error_messages = [
                "Couldn't find your Google Account",
                "Enter a valid email or phone number",
                "find your Google Account"
            ]
            
            page_text = driver.page_source
            for error_msg in error_messages:
                if error_msg in page_text:
                    logging.error(f"Account not found: {email}")
                    return False
            
            # STEP 2: Enter Password
            password_entered = False
            max_wait = 30  # Maximum 30 seconds to wait for password field
            start_time = time.time()
            
            while not password_entered and (time.time() - start_time) < max_wait:
                try:
                    # Try different selectors for password field
                    password_selectors = [
                        (By.NAME, "password"),
                        (By.NAME, "Passwd"),
                        (By.ID, "password"),
                        (By.CSS_SELECTOR, "input[type='password']"),
                        (By.XPATH, "//input[@type='password' and @name='password']")
                    ]
                    
                    password_field = None
                    for selector_type, selector_value in password_selectors:
                        try:
                            password_field = WebDriverWait(driver, 2).until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            if password_field.is_displayed():
                                break
                        except:
                            continue
                    
                    if password_field and password_field.is_displayed():
                        # Wait for field to be clickable
                        WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable(password_field)
                        )
                        
                        logging.info("Entering password...")
                        self.type_like_human(password_field, password)
                        
                        # Try to find and click the Next button
                        next_button = None
                        next_selectors = [
                            (By.ID, "passwordNext"),
                            (By.XPATH, "//button[@type='button']//span[contains(text(), 'Next')]"),
                            (By.XPATH, "//div[@id='passwordNext']")
                        ]
                        
                        for selector_type, selector_value in next_selectors:
                            try:
                                next_button = driver.find_element(selector_type, selector_value)
                                if next_button.is_displayed():
                                    break
                            except:
                                continue
                        
                        if next_button:
                            next_button.click()
                        else:
                            password_field.send_keys(Keys.RETURN)
                        
                        password_entered = True
                        self.wait_for_page_load(driver)
                        self.human_delay(3, 5)
                        
                except Exception as e:
                    # Check if we need to handle account selection
                    try:
                        # Sometimes Google shows account selection screen
                        account_element = driver.find_element(By.XPATH, f"//*[contains(text(), '{email}')]")
                        account_element.click()
                        self.human_delay(2, 3)
                    except:
                        pass
                    
                    time.sleep(1)
            
            if not password_entered:
                logging.error(f"Failed to enter password for: {email}")
                return False
            
            # Check for CAPTCHA after password
            self.check_for_captcha(driver)
            
            # Check for wrong password
            self.human_delay(1, 2)
            error_indicators = [
                "Wrong password",
                "incorrect password",
                "Try again",
                "Your password is incorrect"
            ]
            
            page_text = driver.page_source
            for error in error_indicators:
                if error in page_text:
                    logging.error(f"Wrong password for: {email}")
                    return False
            
            # Handle 2FA if present
            if "2-Step Verification" in driver.page_source or "Verify it" in driver.page_source:
                print(f"\n⚠️ 2FA detected for {email}")
                print("Please complete 2FA verification.")
                print("Press ENTER when done...")
                input()
                self.human_delay(2, 3)
            
            # Check for successful login
            self.human_delay(2, 3)
            success_indicators = [
                "myaccount.google.com",
                "mail.google.com",
                "accounts.google.com/b/0/ManageAccount",
                "Google Account"
            ]
            
            current_url = driver.current_url
            page_source = driver.page_source
            
            for indicator in success_indicators:
                if indicator in current_url or indicator in page_source:
                    logging.info(f"Successfully logged in: {email}")
                    return True
            
            # If no clear success indicator, check if we can access account settings
            try:
                driver.get("https://myaccount.google.com")
                self.human_delay(2, 3)
                if "myaccount.google.com" in driver.current_url:
                    logging.info(f"Successfully logged in: {email}")
                    return True
            except:
                pass
            
            logging.error(f"Login verification failed for: {email}")
            return False
            
        except Exception as e:
            logging.error(f"Login error for {email}: {str(e)}")
            return False
    
    def change_password(self, driver, email, current_password, new_password):
        """Change password for logged-in account"""
        try:
            # Navigate to password change page
            logging.info("Navigating to password change page...")
            driver.get("https://myaccount.google.com/signinoptions/password")
            self.wait_for_page_load(driver)
            self.human_delay(3, 5)
            
            # May need to re-enter password
            try:
                reauth_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                if reauth_field.is_displayed():
                    logging.info("Re-authenticating...")
                    self.type_like_human(reauth_field, current_password)
                    reauth_field.send_keys(Keys.RETURN)
                    self.human_delay(3, 5)
            except:
                pass
            
            # Find password fields
            password_fields = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            
            visible_fields = [f for f in password_fields if f.is_displayed()]
            
            if len(visible_fields) >= 2:
                logging.info("Entering new password...")
                self.type_like_human(visible_fields[0], new_password)
                self.human_delay(0.5, 1)
                self.type_like_human(visible_fields[1], new_password)
                self.human_delay(0.5, 1)
                
                # Try multiple methods to find and click the change password button
                button_clicked = False
                
                # Method 1: Try different button selectors
                button_selectors = [
                    "//button[contains(text(), 'Change password')]",
                    "//button[contains(text(), 'CHANGE PASSWORD')]",
                    "//button[contains(., 'Change') and contains(., 'password')]",
                    "//button[@type='button'][contains(., 'Change')]",
                    "//button[@type='submit'][contains(., 'Change')]",
                    "//div[@role='button'][contains(text(), 'Change password')]",
                    "//span[contains(text(), 'Change password')]/parent::button",
                    "//button[contains(@aria-label, 'Change password')]",
                    "//button[contains(@jsname, 'LgbsSe')]",  # Google's internal button name
                    "//div[@jsname='LgbsSe']//button"
                ]
                
                for selector in button_selectors:
                    try:
                        change_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        
                        # Scroll button into view
                        driver.execute_script("arguments[0].scrollIntoView(true);", change_button)
                        self.human_delay(0.5, 1)
                        
                        # Try JavaScript click first
                        driver.execute_script("arguments[0].click();", change_button)
                        button_clicked = True
                        logging.info(f"Clicked change password button using selector: {selector}")
                        break
                    except:
                        try:
                            # Try regular click if JS click fails
                            change_button = driver.find_element(By.XPATH, selector)
                            change_button.click()
                            button_clicked = True
                            logging.info(f"Clicked change password button using regular click: {selector}")
                            break
                        except:
                            continue
                
                # Method 2: If button not found by text, try by position or class
                if not button_clicked:
                    try:
                        # Sometimes the button is the last button on the page
                        all_buttons = driver.find_elements(By.TAG_NAME, "button")
                        for button in reversed(all_buttons):
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.lower()
                                if "change" in button_text or "save" in button_text or "confirm" in button_text:
                                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                    self.human_delay(0.5, 1)
                                    driver.execute_script("arguments[0].click();", button)
                                    button_clicked = True
                                    logging.info("Clicked button by searching all buttons")
                                    break
                    except:
                        pass
                
                # Method 3: Try pressing Enter on the password field
                if not button_clicked:
                    try:
                        visible_fields[1].send_keys(Keys.RETURN)
                        button_clicked = True
                        logging.info("Submitted form using Enter key")
                    except:
                        pass
                
                if not button_clicked:
                    logging.error("Could not find or click the change password button")
                    return False
                
                self.human_delay(2, 3)
                
                # HANDLE CONFIRMATION POPUP
                logging.info("Looking for confirmation popup...")
                confirmation_clicked = False
                
                # Wait a bit for popup to appear
                time.sleep(2)
                
                # Try different confirmation button selectors
                confirm_selectors = [
                    "//button[contains(text(), 'Confirm')]",
                    "//button[contains(text(), 'CONFIRM')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[contains(text(), 'Ok')]",
                    "//button[contains(text(), 'Yes')]",
                    "//button[contains(text(), 'Continue')]",
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'Done')]",
                    "//button[contains(text(), 'Change')]",
                    "//div[@role='button'][contains(text(), 'Confirm')]",
                    "//span[contains(text(), 'Confirm')]/parent::button",
                    "//button[@jsaction and contains(., 'Confirm')]",
                    "//button[@data-mdc-dialog-action='ok']",
                    "//button[@data-mdc-dialog-action='accept']",
                    "//div[@role='dialog']//button[contains(@class, 'primary')]",
                    "//div[@role='dialog']//button[last()]",
                    "//div[contains(@class, 'dialog')]//button[contains(text(), 'Confirm')]",
                    "//div[contains(@class, 'modal')]//button[contains(text(), 'Confirm')]"
                ]
                
                for selector in confirm_selectors:
                    try:
                        confirm_button = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        
                        # Make sure it's visible and in a dialog/popup
                        if confirm_button.is_displayed():
                            driver.execute_script("arguments[0].click();", confirm_button)
                            confirmation_clicked = True
                            logging.info(f"Clicked confirmation button using selector: {selector}")
                            break
                    except:
                        continue
                
                # If no confirmation button found by specific selectors, try finding any button in a dialog
                if not confirmation_clicked:
                    try:
                        # Look for buttons within dialog elements
                        dialog_buttons = driver.find_elements(By.XPATH, "//div[@role='dialog']//button")
                        for button in dialog_buttons:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.lower()
                                # Click buttons that seem like confirmation
                                if any(word in button_text for word in ['confirm', 'ok', 'yes', 'continue', 'done', 'change']):
                                    driver.execute_script("arguments[0].click();", button)
                                    confirmation_clicked = True
                                    logging.info(f"Clicked dialog button with text: {button.text}")
                                    break
                    except:
                        pass
                
                # Wait after handling popup
                self.human_delay(3, 5)
                
                # Check for success
                success_messages = [
                    "Password changed",
                    "Your password was changed",
                    "Password updated",
                    "successfully changed",
                    "Success",
                    "password has been changed"
                ]
                
                # Wait for page change or success message
                time.sleep(2)
                page_text = driver.page_source.lower()
                
                for msg in success_messages:
                    if msg.lower() in page_text:
                        logging.info(f"✓ Password changed successfully for: {email}")
                        return True
                
                # Alternative: Check if we're redirected away from password page
                current_url = driver.current_url
                if "password" not in current_url and ("myaccount.google.com" in current_url or "security" in current_url):
                    logging.info(f"✓ Password changed successfully for: {email} (detected by redirect)")
                    return True
                
                # Sometimes success is shown briefly then redirects
                # Check multiple times over a few seconds
                for i in range(3):
                    time.sleep(1)
                    page_text = driver.page_source.lower()
                    for msg in success_messages:
                        if msg.lower() in page_text:
                            logging.info(f"✓ Password changed successfully for: {email}")
                            return True
                
                logging.error(f"Password change confirmation not found for: {email}")
                return False
                
            else:
                logging.error(f"Could not find password fields for: {email}")
                return False
                
        except Exception as e:
            logging.error(f"Password change failed for {email}: {e}")
            return False
    
    def process_account(self, account, account_number, total_accounts):
        """Process a single account"""
        driver = None
        try:
            print(f"\n{'='*60}")
            print(f"[{account_number}/{total_accounts}] Processing: {account['email']}")
            print(f"{'='*60}")
            
            # Create new Chrome instance
            driver = webdriver.Chrome(options=self.get_chrome_options())
            
            # Attempt login
            if self.login_to_gmail(driver, account['email'], account['current_password']):
                # Handle any popups after login
                self.handle_popups(driver)
                
                # Attempt password change
                if self.change_password(driver, account['email'], 
                                      account['current_password'], account['new_password']):
                    self.successful_accounts.append(account)
                    self.success_count += 1
                else:
                    self.password_change_failed.append(account)
                    self.failure_count += 1
            else:
                self.bad_emails.append(account)
            
        except Exception as e:
            logging.error(f"Unexpected error processing {account['email']}: {e}")
            self.bad_emails.append(account)
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            self.human_delay(2, 3)
    
    def save_results(self):
        """Save results to files"""
        # Save bad emails
        if self.bad_emails:
            with open('bad_emails.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['email', 'current_password', 'new_password'])
                writer.writeheader()
                writer.writerows(self.bad_emails)
            print(f"\n✓ Bad emails saved to 'bad_emails.csv' ({len(self.bad_emails)} accounts)")
        
        # Save password change failed
        if self.password_change_failed:
            with open('password_change_failed.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['email', 'current_password', 'new_password'])
                writer.writeheader()
                writer.writerows(self.password_change_failed)
            print(f"✓ Failed password changes saved to 'password_change_failed.csv' ({len(self.password_change_failed)} accounts)")
        
        # Save successful accounts
        if self.successful_accounts:
            with open('successful_accounts.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['email', 'new_password'])
                writer.writeheader()
                for acc in self.successful_accounts:
                    writer.writerow({'email': acc['email'], 'new_password': acc['new_password']})
            print(f"✓ Successful accounts saved to 'successful_accounts.csv' ({len(self.successful_accounts)} accounts)")
    
    def run(self):
        """Main execution function"""
        accounts = self.read_csv()
        if not accounts:
            logging.error("No accounts found in CSV file")
            return
        
        print("\n" + "="*60)
        print("GMAIL PASSWORD CHANGER - OPTIMIZED VERSION")
        print("="*60)
        print(f"\nTotal accounts to process: {len(accounts)}")
        print("\nFeatures:")
        print("- Fresh Chrome for each account")
        print("- Smart password field detection")
        print("- Automatic popup handling")
        print("- Manual CAPTCHA solving support")
        print("="*60)
        
        # Process each account
        for i, account in enumerate(accounts):
            self.process_account(account, i + 1, len(accounts))
        
        # Save results
        self.save_results()
        
        # Print summary
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Total processed: {len(accounts)}")
        print(f"✓ Successful: {self.success_count}")
        print(f"✗ Bad emails: {len(self.bad_emails)}")
        print(f"⚠ Password change failed: {len(self.password_change_failed)}")
        print("="*60)

def main():
    # Clear console
    os.system('cls' if os.name == 'nt' else 'clear') 
    
    # Configuration
    CSV_FILE = "gmails_with_passwords.csv"  # Your CSV file
    
    # Create and run the password changer
    changer = GmailPasswordChanger(CSV_FILE)
    changer.run()

if __name__ == "__main__":
    main()
    
    
    
