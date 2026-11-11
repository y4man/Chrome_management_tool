#!/usr/bin/env python3
"""
Chrome Proxy Manager Ultimate - Robust Enterprise Edition
Complete automation for proxy profiles with Gmail integration
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import os
import subprocess
import threading
import queue
import uuid
from datetime import datetime
import platform
import tempfile
import shutil
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import re
import csv
import zipfile
import base64
from pathlib import Path
import random

# Try to import Selenium for automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("ERROR: Selenium not installed. Run: pip install selenium")

# Try to import undetected-chromedriver
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False


class ProxyAuthExtension:
    """Handles proxy authentication via Chrome extension"""
    
    @staticmethod
    def create(proxy_host, proxy_port, proxy_username, proxy_password, extension_dir):
        """Create proxy auth extension that actually works"""
        
        # Create extension directory
        os.makedirs(extension_dir, exist_ok=True)
        
        # manifest.json for Manifest V2 (more compatible)
        manifest = {
            "version": "1.0",
            "manifest_version": 2,
            "name": "Proxy Auto Auth",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"],
                "persistent": True
            }
        }
        
        # background.js with working authentication
        background_js = f'''
var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{proxy_host}",
            port: parseInt({proxy_port})
        }},
        bypassList: ["127.0.0.1"]
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{proxy_username}",
            password: "{proxy_password}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);
'''
        
        # Write files
        with open(os.path.join(extension_dir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        with open(os.path.join(extension_dir, 'background.js'), 'w') as f:
            f.write(background_js)
        
        return extension_dir


class GmailValidator:
    """Validates Gmail accounts before using them"""
    
    def __init__(self):
        self.good_emails = []
        self.bad_emails = []
        self.validated = False
    
    def validate_batch(self, email_list, progress_callback=None):
        """Validate a batch of Gmail accounts"""
        total = len(email_list)
        
        for i, email_data in enumerate(email_list):
            if progress_callback:
                progress_callback(i + 1, total, f"Validating {email_data['email']}...")
            
            if self.validate_single(email_data):
                self.good_emails.append(email_data)
            else:
                self.bad_emails.append(email_data)
            
            # Small delay between validations
            time.sleep(2)
        
        self.validated = True
        return self.good_emails, self.bad_emails
    
    def validate_single(self, email_data):
        """Validate a single Gmail account"""
        driver = None
        try:
            # Create a temporary driver for validation
            options = Options()
            options.add_argument('--headless')  # Run in background
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=options)
            driver.set_window_size(1280, 720)
            
            # Try to login
            success = self.attempt_gmail_login(driver, email_data['email'], email_data['password'])
            
            return success
            
        except Exception as e:
            print(f"Validation error for {email_data['email']}: {e}")
            return False
        finally:
            if driver:
                driver.quit()
    
    def attempt_gmail_login(self, driver, email, password):
        """Attempt to login to Gmail"""
        try:
            driver.get("https://accounts.google.com")
            time.sleep(2)
            
            # Find and fill email
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_field.send_keys(email)
            
            # Click Next
            next_button = driver.find_element(By.ID, "identifierNext")
            next_button.click()
            time.sleep(3)
            
            # Check for error (invalid email)
            try:
                error = driver.find_element(By.CSS_SELECTOR, '[jsname="B34EJ"] span')
                if error:
                    print(f"Invalid email: {email}")
                    return False
            except:
                pass
            
            # Find and fill password
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_field.send_keys(password)
            
            # Click Next
            password_next = driver.find_element(By.ID, "passwordNext")
            password_next.click()
            time.sleep(3)
            
            # Check if logged in successfully
            if "myaccount.google.com" in driver.current_url or "mail.google.com" in driver.current_url:
                return True
            
            # Check for wrong password
            try:
                error = driver.find_element(By.CSS_SELECTOR, '[jsname="B34EJ"] span')
                if error:
                    print(f"Wrong password for: {email}")
                    return False
            except:
                pass
            
            # Check for captcha or 2FA
            if "challenge" in driver.current_url:
                print(f"2FA or captcha required for: {email}")
                return False
            
            return False
            
        except TimeoutException:
            print(f"Timeout validating: {email}")
            return False
        except Exception as e:
            print(f"Error validating {email}: {e}")
            return False


class ChromeProfileManager:
    """Main manager for Chrome profiles with proxy and email"""
    
    def __init__(self):
        self.profiles = []
        self.setup_directories()
        self.chrome_path = self.find_chrome()
    
    def setup_directories(self):
        """Create necessary directories"""
        self.base_dir = Path.cwd()
        self.data_dir = self.base_dir / "chrome_profiles_data"
        self.extensions_dir = self.base_dir / "proxy_extensions"
        self.data_dir.mkdir(exist_ok=True)
        self.extensions_dir.mkdir(exist_ok=True)
    
    def find_chrome(self):
        """Find Chrome executable"""
        if platform.system() == "Windows":
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe")
            ]
        elif platform.system() == "Darwin":
            paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
        else:
            paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]
        
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def create_profile(self, profile_data):
        """Create a single profile with all setup"""
        profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        profile_dir = self.data_dir / profile_id
        profile_dir.mkdir(exist_ok=True)
        
        # Store profile data
        profile = {
            'id': profile_id,
            'name': profile_data['name'],
            'proxy_host': profile_data['proxy_host'],
            'proxy_port': profile_data['proxy_port'],
            'proxy_username': profile_data.get('proxy_username'),
            'proxy_password': profile_data.get('proxy_password'),
            'email': profile_data.get('email'),
            'email_password': profile_data.get('email_password'),
            'profile_dir': str(profile_dir),
            'status': 'pending',
            'proxy_authenticated': False,
            'email_logged_in': False,
            'created': datetime.now().isoformat()
        }
        
        return profile
    
    def setup_profile_complete(self, profile, progress_callback=None):
        """Complete setup: proxy auth + email login"""
        driver = None
        try:
            if progress_callback:
                progress_callback(f"Setting up {profile['name']}...")
            
            # Create Chrome driver with proxy extension
            driver = self.create_driver_with_proxy(profile)
            if not driver:
                profile['status'] = 'failed'
                return False
            
            # Step 1: Test proxy
            if progress_callback:
                progress_callback(f"Testing proxy for {profile['name']}...")
            
            driver.get("http://ipinfo.io/json")
            time.sleep(3)
            
            try:
                body = driver.find_element(By.TAG_NAME, "pre").text
                data = json.loads(body)
                if 'ip' in data:
                    profile['proxy_authenticated'] = True
                    profile['proxy_ip'] = data.get('ip', 'Unknown')
                    print(f"✓ Proxy working for {profile['name']}: {profile['proxy_ip']}")
            except:
                print(f"✗ Proxy failed for {profile['name']}")
                profile['status'] = 'proxy_failed'
                return False
            
            # Step 2: Login to Gmail
            if profile.get('email') and profile.get('email_password'):
                if progress_callback:
                    progress_callback(f"Logging into Gmail for {profile['name']}...")
                
                if self.login_gmail(driver, profile['email'], profile['email_password']):
                    profile['email_logged_in'] = True
                    profile['status'] = 'ready'
                    print(f"✓ Gmail logged in for {profile['name']}")
                    
                    # Save cookies
                    self.save_cookies(driver, profile['id'])
                else:
                    print(f"✗ Gmail login failed for {profile['name']}")
                    profile['status'] = 'email_failed'
            else:
                profile['status'] = 'ready'
            
            return True
            
        except Exception as e:
            print(f"Setup error for {profile['name']}: {e}")
            profile['status'] = 'error'
            return False
        finally:
            if driver:
                # Keep browser open for a moment to save session
                time.sleep(2)
                driver.quit()
    
    def create_driver_with_proxy(self, profile):
        """Create Chrome driver with proxy authentication"""
        try:
            options = Options()
            
            # User data directory
            options.add_argument(f"--user-data-dir={profile['profile_dir']}")
            
            # Create and load proxy extension if auth required
            if profile.get('proxy_username') and profile.get('proxy_password'):
                ext_dir = self.extensions_dir / f"ext_{profile['id']}"
                ProxyAuthExtension.create(
                    profile['proxy_host'],
                    profile['proxy_port'],
                    profile['proxy_username'],
                    profile['proxy_password'],
                    str(ext_dir)
                )
                options.add_argument(f"--load-extension={ext_dir}")
            else:
                # Simple proxy without auth
                options.add_argument(f"--proxy-server={profile['proxy_host']}:{profile['proxy_port']}")
            
            # Other options
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            if self.chrome_path:
                options.binary_location = self.chrome_path
            
            driver = webdriver.Chrome(options=options)
            
            # Anti-detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            return driver
            
        except Exception as e:
            print(f"Error creating driver: {e}")
            return None
    
    def login_gmail(self, driver, email, password):
        """Login to Gmail with better handling"""
        try:
            driver.get("https://accounts.google.com")
            time.sleep(3)
            
            # Email input
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # Next button
            next_btn = driver.find_element(By.ID, "identifierNext")
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(3)
            
            # Password input
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.clear()
            password_input.send_keys(password)
            
            # Sign in button
            signin_btn = driver.find_element(By.ID, "passwordNext")
            driver.execute_script("arguments[0].click();", signin_btn)
            time.sleep(5)
            
            # Check if logged in
            if "myaccount.google.com" in driver.current_url or not driver.find_elements(By.ID, "identifierId"):
                # Navigate to Gmail to ensure cookies are saved
                driver.get("https://mail.google.com")
                time.sleep(3)
                return True
            
            return False
            
        except Exception as e:
            print(f"Gmail login error: {e}")
            return False
    
    def save_cookies(self, driver, profile_id):
        """Save cookies for profile"""
        try:
            cookies = driver.get_cookies()
            cookie_file = self.data_dir / profile_id / "cookies.json"
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
        except Exception as e:
            print(f"Error saving cookies: {e}")
    
    def launch_profile(self, profile):
        """Launch a profile in Chrome"""
        if not self.chrome_path:
            print("Chrome not found!")
            return False
        
        cmd = [
            self.chrome_path,
            f"--user-data-dir={profile['profile_dir']}"
        ]
        
        # Add proxy if no saved auth
        if not profile.get('proxy_authenticated'):
            if profile.get('proxy_username'):
                # Load extension
                ext_dir = self.extensions_dir / f"ext_{profile['id']}"
                if ext_dir.exists():
                    cmd.append(f"--load-extension={ext_dir}")
            else:
                cmd.append(f"--proxy-server={profile['proxy_host']}:{profile['proxy_port']}")
        
        subprocess.Popen(cmd)
        return True


class ChromeProxyManagerGUI:
    """Main GUI Application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome Proxy Manager Ultimate")
        self.root.geometry("1200x800")
        
        # Style
        self.setup_style()
        
        # Manager
        self.manager = ChromeProfileManager()
        self.validator = GmailValidator()
        
        # Database
        self.setup_database()
        
        # GUI
        self.setup_gui()
        
        # Load existing profiles
        self.load_profiles()
    
    def setup_style(self):
        """Setup dark theme"""
        self.bg_color = "#0a0a0a"
        self.fg_color = "#ffffff"
        self.accent_color = "#00ff88"
        self.error_color = "#ff4444"
        self.warning_color = "#ffaa00"
        
        self.root.configure(bg=self.bg_color)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", 
                       background="#1a1a1a",
                       foreground="white",
                       fieldbackground="#1a1a1a")
    
    def setup_database(self):
        """Setup SQLite database"""
        self.db_path = "proxy_profiles_ultimate.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                proxy_host TEXT NOT NULL,
                proxy_port INTEGER NOT NULL,
                proxy_username TEXT,
                proxy_password TEXT,
                proxy_ip TEXT,
                email TEXT,
                email_password TEXT,
                profile_dir TEXT,
                status TEXT DEFAULT 'pending',
                proxy_authenticated BOOLEAN DEFAULT 0,
                email_logged_in BOOLEAN DEFAULT 0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS validated_emails (
                email TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'good',
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def setup_gui(self):
        """Setup GUI components"""
        # Header
        header = tk.Frame(self.root, bg="#1a1a1a", height=80)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Chrome Proxy Manager Ultimate",
                font=('Arial', 24, 'bold'), bg="#1a1a1a", fg=self.accent_color).pack(pady=20)
        
        # Control Panel
        self.setup_control_panel()
        
        # Progress Frame
        self.setup_progress_frame()
        
        # Main Content
        self.setup_content_area()
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                             bg="#1a1a1a", fg="#888888", anchor='w')
        status_bar.pack(fill='x', side='bottom', padx=10, pady=5)
    
    def setup_control_panel(self):
        """Setup control buttons"""
        control_frame = tk.Frame(self.root, bg=self.bg_color)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Main buttons
        buttons = [
            ("📁 Import Batch", self.import_batch, self.accent_color),
            ("✓ Validate Emails", self.validate_emails, "#00aaff"),
            ("🚀 Setup All Profiles", self.setup_all_profiles, "#ff6600"),
            ("▶ Launch Profile", self.launch_selected, "#00ff00"),
            ("📊 Export Data", self.export_data, "#888888"),
            ("🗑 Clear All", self.clear_all, self.error_color)
        ]
        
        for text, command, color in buttons:
            tk.Button(control_frame, text=text, command=command,
                     bg=color, fg="white" if color != self.accent_color else "black",
                     font=('Arial', 11, 'bold'), bd=0, padx=20, pady=10,
                     cursor='hand2').pack(side='left', padx=5)
    
    def setup_progress_frame(self):
        """Setup progress display"""
        self.progress_frame = tk.Frame(self.root, bg=self.bg_color)
        self.progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_label = tk.Label(self.progress_frame, text="", 
                                      bg=self.bg_color, fg=self.accent_color)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, 
                                          variable=self.progress_var,
                                          length=400)
    
    def setup_content_area(self):
        """Setup main content area with tabs"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Profiles tab
        self.profiles_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.profiles_frame, text="Profiles")
        self.setup_profiles_view()
        
        # Validated Emails tab
        self.emails_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.emails_frame, text="Validated Emails")
        self.setup_emails_view()
        
        # Log tab
        self.log_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.log_frame, text="Logs")
        self.setup_log_view()
    
    def setup_profiles_view(self):
        """Setup profiles treeview"""
        # Create Treeview
        columns = ('Name', 'Proxy', 'Email', 'Status', 'Proxy Auth', 'Email Login')
        self.profiles_tree = ttk.Treeview(self.profiles_frame, columns=columns, show='tree headings')
        
        # Configure columns
        self.profiles_tree.heading('#0', text='ID')
        self.profiles_tree.column('#0', width=100)
        
        for col in columns:
            self.profiles_tree.heading(col, text=col)
            self.profiles_tree.column(col, width=150)
        
        # Scrollbars
        vsb = ttk.Scrollbar(self.profiles_frame, orient='vertical', command=self.profiles_tree.yview)
        hsb = ttk.Scrollbar(self.profiles_frame, orient='horizontal', command=self.profiles_tree.xview)
        self.profiles_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Pack
        self.profiles_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        self.profiles_frame.grid_rowconfigure(0, weight=1)
        self.profiles_frame.grid_columnconfigure(0, weight=1)
    
    def setup_emails_view(self):
        """Setup validated emails view"""
        # Create frames for good and bad emails
        tk.Label(self.emails_frame, text="Good Emails", 
                bg=self.bg_color, fg=self.accent_color,
                font=('Arial', 14, 'bold')).pack(pady=5)
        
        self.good_emails_text = scrolledtext.ScrolledText(self.emails_frame, 
                                                         height=10, width=80,
                                                         bg="#1a1a1a", fg="#00ff00")
        self.good_emails_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        tk.Label(self.emails_frame, text="Bad Emails", 
                bg=self.bg_color, fg=self.error_color,
                font=('Arial', 14, 'bold')).pack(pady=5)
        
        self.bad_emails_text = scrolledtext.ScrolledText(self.emails_frame, 
                                                        height=10, width=80,
                                                        bg="#1a1a1a", fg="#ff4444")
        self.bad_emails_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def setup_log_view(self):
        """Setup log view"""
        self.log_text = scrolledtext.ScrolledText(self.log_frame, 
                                                 bg="#1a1a1a", fg="#888888",
                                                 font=('Consolas', 10))
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.root.update()
    
    def import_batch(self):
        """Import batch profiles"""
        dialog = BatchImportDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            profiles_data = dialog.result
            self.log(f"Importing {len(profiles_data)} profiles...")
            
            # Create profiles
            for data in profiles_data:
                profile = self.manager.create_profile(data)
                
                # Save to database
                self.conn.execute('''
                    INSERT INTO profiles (id, name, proxy_host, proxy_port, 
                                        proxy_username, proxy_password, 
                                        email, email_password, profile_dir, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (profile['id'], profile['name'], profile['proxy_host'], 
                     profile['proxy_port'], profile['proxy_username'], 
                     profile['proxy_password'], profile['email'], 
                     profile['email_password'], profile['profile_dir'], 
                     profile['status']))
            
            self.conn.commit()
            self.load_profiles()
            self.log(f"✓ Imported {len(profiles_data)} profiles")
            messagebox.showinfo("Success", f"Imported {len(profiles_data)} profiles")
    
    def validate_emails(self):
        """Validate all emails before setup"""
        # Get unique emails from profiles
        cursor = self.conn.execute('''
            SELECT DISTINCT email, email_password 
            FROM profiles 
            WHERE email IS NOT NULL AND email_password IS NOT NULL
        ''')
        
        email_list = []
        for row in cursor:
            email_list.append({
                'email': row['email'],
                'password': row['email_password']
            })
        
        if not email_list:
            messagebox.showinfo("Info", "No emails to validate")
            return
        
        self.log(f"Starting validation of {len(email_list)} emails...")
        self.show_progress("Validating emails...")
        
        def validate_worker():
            def progress_callback(current, total, message):
                self.progress_var.set((current / total) * 100)
                self.progress_label.config(text=message)
                self.root.update()
            
            good, bad = self.validator.validate_batch(email_list, progress_callback)
            
            # Update UI
            self.root.after(0, self.update_email_lists, good, bad)
            self.root.after(0, self.hide_progress)
            self.root.after(0, lambda: messagebox.showinfo("Validation Complete", 
                                                          f"Good: {len(good)}, Bad: {len(bad)}"))
        
        threading.Thread(target=validate_worker, daemon=True).start()
    
    def update_email_lists(self, good_emails, bad_emails):
        """Update email lists in UI"""
        # Clear existing
        self.good_emails_text.delete('1.0', 'end')
        self.bad_emails_text.delete('1.0', 'end')
        
        # Add good emails
        for email_data in good_emails:
            self.good_emails_text.insert('end', f"{email_data['email']}:{email_data['password']}\n")
            
            # Save to database
            self.conn.execute('''
                INSERT OR REPLACE INTO validated_emails (email, password, status)
                VALUES (?, ?, 'good')
            ''', (email_data['email'], email_data['password']))
        
        # Add bad emails
        for email_data in bad_emails:
            self.bad_emails_text.insert('end', f"{email_data['email']}:{email_data['password']}\n")
            
            # Save to database
            self.conn.execute('''
                INSERT OR REPLACE INTO validated_emails (email, password, status)
                VALUES (?, ?, 'bad')
            ''', (email_data['email'], email_data['password']))
        
        self.conn.commit()
    
    def setup_all_profiles(self):
        """Setup all profiles with proxy and email"""
        # Get pending profiles
        cursor = self.conn.execute('''
            SELECT * FROM profiles 
            WHERE status IN ('pending', 'failed', 'proxy_failed', 'email_failed')
        ''')
        profiles = [dict(row) for row in cursor]
        
        if not profiles:
            messagebox.showinfo("Info", "No profiles need setup")
            return
        
        # If emails not validated, suggest validation first
        if not self.validator.validated:
            if messagebox.askyesno("Validate Emails", 
                                  "Email validation recommended before setup. Validate now?"):
                self.validate_emails()
                return
        
        self.log(f"Starting setup of {len(profiles)} profiles...")
        self.show_progress("Setting up profiles...")
        
        def setup_worker():
            total = len(profiles)
            success_count = 0
            
            for i, profile in enumerate(profiles):
                def progress_callback(message):
                    self.progress_var.set(((i + 0.5) / total) * 100)
                    self.progress_label.config(text=message)
                    self.root.update()
                
                # Check if email is validated as good
                if profile['email']:
                    cursor = self.conn.execute('''
                        SELECT status FROM validated_emails WHERE email = ?
                    ''', (profile['email'],))
                    result = cursor.fetchone()
                    
                    if result and result['status'] == 'bad':
                        self.log(f"Skipping {profile['name']} - bad email")
                        profile['status'] = 'email_invalid'
                        continue
                
                # Setup profile
                success = self.manager.setup_profile_complete(profile, progress_callback)
                
                if success:
                    success_count += 1
                    self.log(f"✓ Setup complete: {profile['name']}")
                else:
                    self.log(f"✗ Setup failed: {profile['name']}")
                
                # Update database
                self.conn.execute('''
                    UPDATE profiles 
                    SET status = ?, proxy_authenticated = ?, email_logged_in = ?, proxy_ip = ?
                    WHERE id = ?
                ''', (profile['status'], profile.get('proxy_authenticated', False),
                     profile.get('email_logged_in', False), profile.get('proxy_ip'),
                     profile['id']))
                self.conn.commit()
                
                # Update progress
                self.progress_var.set(((i + 1) / total) * 100)
                
                # Refresh display
                self.root.after(0, self.load_profiles)
            
            self.root.after(0, self.hide_progress)
            self.root.after(0, lambda: messagebox.showinfo("Setup Complete", 
                                                          f"Successfully setup {success_count}/{total} profiles"))
        
        threading.Thread(target=setup_worker, daemon=True).start()
    
    def launch_selected(self):
        """Launch selected profile"""
        selection = self.profiles_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile")
            return
        
        profile_id = self.profiles_tree.item(selection[0])['text']
        
        # Get profile from database
        cursor = self.conn.execute('SELECT * FROM profiles WHERE id = ?', (profile_id,))
        profile = dict(cursor.fetchone())
        
        if self.manager.launch_profile(profile):
            self.log(f"Launched: {profile['name']}")
            
            # Update last used
            self.conn.execute('UPDATE profiles SET last_used = CURRENT_TIMESTAMP WHERE id = ?', 
                            (profile_id,))
            self.conn.commit()
    
    def export_data(self):
        """Export profiles data"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv")]
        )
        
        if filename:
            cursor = self.conn.execute('SELECT * FROM profiles')
            profiles = [dict(row) for row in cursor]
            
            if filename.endswith('.json'):
                with open(filename, 'w') as f:
                    json.dump(profiles, f, indent=2)
            else:
                import csv
                with open(filename, 'w', newline='') as f:
                    if profiles:
                        writer = csv.DictWriter(f, fieldnames=profiles[0].keys())
                        writer.writeheader()
                        writer.writerows(profiles)
            
            messagebox.showinfo("Success", f"Exported {len(profiles)} profiles")
    
    def clear_all(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm", "Delete all profiles and data?"):
            # Delete from database
            self.conn.execute('DELETE FROM profiles')
            self.conn.execute('DELETE FROM validated_emails')
            self.conn.commit()
            
            # Delete directories
            if self.manager.data_dir.exists():
                shutil.rmtree(self.manager.data_dir)
            if self.manager.extensions_dir.exists():
                shutil.rmtree(self.manager.extensions_dir)
            
            # Recreate directories
            self.manager.setup_directories()
            
            # Refresh
            self.load_profiles()
            self.update_email_lists([], [])
            
            messagebox.showinfo("Success", "All data cleared")
    
    def load_profiles(self):
        """Load profiles into treeview"""
        # Clear existing
        for item in self.profiles_tree.get_children():
            self.profiles_tree.delete(item)
        
        # Load from database
        cursor = self.conn.execute('SELECT * FROM profiles ORDER BY created DESC')
        
        for row in cursor:
            values = (
                row['name'],
                f"{row['proxy_host']}:{row['proxy_port']}",
                row['email'] or 'N/A',
                row['status'],
                '✓' if row['proxy_authenticated'] else '✗',
                '✓' if row['email_logged_in'] else '✗'
            )
            
            # Color based on status
            tags = []
            if row['status'] == 'ready':
                tags.append('ready')
            elif 'failed' in row['status']:
                tags.append('failed')
            
            self.profiles_tree.insert('', 'end', text=row['id'], values=values, tags=tags)
        
        # Configure tags
        self.profiles_tree.tag_configure('ready', foreground='#00ff00')
        self.profiles_tree.tag_configure('failed', foreground='#ff4444')
    
    def show_progress(self, message):
        """Show progress bar"""
        self.progress_label.config(text=message)
        self.progress_label.pack(side='left', padx=10)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=10)
        self.progress_var.set(0)
    
    def hide_progress(self):
        """Hide progress bar"""
        self.progress_label.pack_forget()
        self.progress_bar.pack_forget()
    
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Clean up on close"""
        self.conn.close()
        self.root.destroy()


class BatchImportDialog:
    """Dialog for batch import"""
    
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Import Profiles")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg="#1a1a1a")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title
        tk.Label(self.dialog, text="Batch Import Profiles",
                font=('Arial', 20, 'bold'), bg="#1a1a1a", fg="#00ff88").pack(pady=20)
        
        # Instructions
        tk.Label(self.dialog, 
                text="Format: ProfileName:ProxyHost:ProxyPort:ProxyUser:ProxyPass:Email:EmailPass",
                bg="#1a1a1a", fg="#888888", font=('Arial', 11)).pack()
        
        # Import button
        tk.Button(self.dialog, text="Import from File", command=self.import_file,
                 bg="#00aaff", fg="white", font=('Arial', 11, 'bold'),
                 bd=0, padx=20, pady=10).pack(pady=20)
        
        # Text area
        self.text = scrolledtext.ScrolledText(self.dialog, height=20, width=80,
                                            bg="#0a0a0a", fg="white",
                                            font=('Consolas', 10))
        self.text.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#1a1a1a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Import", command=self.process_import,
                 bg="#00ff88", fg="black", font=('Arial', 12, 'bold'),
                 bd=0, padx=40, pady=15).pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="Cancel", command=self.dialog.destroy,
                 bg="#666666", fg="white", font=('Arial', 11),
                 bd=0, padx=30, pady=10).pack(side='left', padx=10)
    
    def import_file(self):
        """Import from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                self.text.delete('1.0', 'end')
                self.text.insert('1.0', f.read())
    
    def process_import(self):
        """Process the import"""
        content = self.text.get('1.0', 'end-1c').strip()
        if not content:
            messagebox.showwarning("Warning", "No data to import")
            return
        
        profiles = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) >= 3:
                profile = {
                    'name': parts[0] if len(parts) >= 7 else f"Profile_{i}",
                    'proxy_host': parts[1] if len(parts) >= 7 else parts[0],
                    'proxy_port': int(parts[2] if len(parts) >= 7 else parts[1]),
                    'proxy_username': parts[3] if len(parts) >= 4 else None,
                    'proxy_password': parts[4] if len(parts) >= 5 else None,
                    'email': parts[5] if len(parts) >= 6 else None,
                    'email_password': parts[6] if len(parts) >= 7 else None
                }
                profiles.append(profile)
        
        if profiles:
            self.result = profiles
            self.dialog.destroy()
        else:
            messagebox.showwarning("Warning", "No valid profiles found")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Chrome Proxy Manager Ultimate")
    print("="*60)
    print("Features:")
    print("- Automated proxy authentication")
    print("- Gmail validation and login")
    print("- Batch profile management")
    print("- Clean and robust architecture")
    print("="*60 + "\n")
    
    if not SELENIUM_AVAILABLE:
        print("ERROR: Selenium is required!")
        print("Install: pip install selenium")
        return
    
    # Check Chrome
    manager = ChromeProfileManager()
    if not manager.chrome_path:
        print("ERROR: Chrome not found!")
        print("Please install Google Chrome")
        return
    
    print(f"Chrome found: {manager.chrome_path}")
    print("\nStarting GUI...\n")
    
    # Run GUI
    app = ChromeProxyManagerGUI()
    app.run()


if __name__ == "__main__":
    main()