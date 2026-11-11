#!/usr/bin/env python3
"""
Chrome Profile Manager - Modified Version
Complete automation for proxy profiles with Gmail integration
Modified workflow as requested
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
import requests

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
    from selenium.webdriver.common.alert import Alert
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


class GmailValidator:
    """Validates Gmail accounts by attempting login"""
    
    def __init__(self):
        self.good_emails = []
        self.bad_emails = []
        self.validated = False
    
    def validate_from_csv(self, csv_file_path, progress_callback=None):
        """Validate emails from CSV file with headers: email,password"""
        email_list = []
        
        # Read CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'email' in row and 'password' in row:
                    email_list.append({
                        'email': row['email'].strip(),
                        'password': row['password'].strip()
                    })
        
        return self.validate_batch(email_list, progress_callback)
    
    def validate_batch(self, email_list, progress_callback=None):
        """Validate a batch of Gmail accounts"""
        total = len(email_list)
        self.good_emails = []
        self.bad_emails = []
        
        for i, email_data in enumerate(email_list):
            if progress_callback:
                progress_callback(i + 1, total, f"Checking {email_data['email']}...")
            
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
            # Create a headless driver for validation
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=options)
            driver.set_window_size(1280, 720)
            
            # Try to login
            driver.get("https://accounts.google.com")
            time.sleep(2)
            
            # Enter email
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_field.send_keys(email_data['email'])
            
            # Click Next
            next_button = driver.find_element(By.ID, "identifierNext")
            next_button.click()
            time.sleep(3)
            
            # Check for email error
            try:
                error = driver.find_element(By.CSS_SELECTOR, '[jsname="B34EJ"] span')
                if error:
                    return False
            except:
                pass
            
            # Enter password
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_field.send_keys(email_data['password'])
            
            # Click Next
            password_next = driver.find_element(By.ID, "passwordNext")
            password_next.click()
            time.sleep(3)
            
            # Check if logged in successfully
            if "myaccount.google.com" in driver.current_url or "mail.google.com" in driver.current_url:
                return True
            
            # Check for password error
            try:
                error = driver.find_element(By.CSS_SELECTOR, '[jsname="B34EJ"] span')
                if error:
                    return False
            except:
                pass
            
            # Check for 2FA
            if "challenge" in driver.current_url:
                return False
            
            return False
            
        except Exception as e:
            print(f"Error validating {email_data['email']}: {e}")
            return False
        finally:
            if driver:
                driver.quit()


class ProxyManager:
    """Manages proxy categorization by country"""
    
    def __init__(self):
        self.proxies_by_country = {}
        self.all_proxies = []
    
    def import_proxies(self, proxies_text):
        """Import proxies and categorize by country"""
        self.all_proxies = []
        self.proxies_by_country = {}
        
        lines = proxies_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse proxy format: host:port:username:password or host:port
            parts = line.split(':')
            if len(parts) >= 2:
                proxy = {
                    'host': parts[0],
                    'port': parts[1],
                    'username': parts[2] if len(parts) >= 3 else None,
                    'password': parts[3] if len(parts) >= 4 else None,
                    'country': 'Unknown'
                }
                
                # Get country (you can enhance this with actual geo-IP lookup)
                proxy['country'] = self.get_proxy_country(proxy['host'])
                
                self.all_proxies.append(proxy)
                
                # Categorize by country
                if proxy['country'] not in self.proxies_by_country:
                    self.proxies_by_country[proxy['country']] = []
                self.proxies_by_country[proxy['country']].append(proxy)
        
        return self.proxies_by_country
    
    def get_proxy_country(self, host):
        """Get country of proxy (simplified - you can use real geo-IP service)"""
        # This is a simplified version - in production, use a real geo-IP service
        try:
            # Try to get country from IP info service
            response = requests.get(f"http://ip-api.com/json/{host}", timeout=5)
            data = response.json()
            if data.get('status') == 'success':
                return data.get('country', 'Unknown')
        except:
            pass
        
        return 'Unknown'


class ChromeProfileManager:
    """Main manager for Chrome profiles with automated setup"""
    
    def __init__(self):
        self.profiles = []
        self.setup_directories()
        self.chrome_path = self.find_chrome()
        self.driver_path = self.find_chromedriver()
    
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
    
    def find_chromedriver(self):
        """Find chromedriver executable"""
        # Check current directory first
        if os.path.exists("chromedriver.exe") or os.path.exists("chromedriver"):
            return "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        
        # Check PATH
        from shutil import which
        return which("chromedriver")
    
    def create_profile(self, name, proxy, email):
        """Create a single profile with unique ID"""
        profile_id = f"profile_{uuid.uuid4().hex[:12]}"
        profile_dir = self.data_dir / profile_id
        profile_dir.mkdir(exist_ok=True)
        
        profile = {
            'id': profile_id,
            'name': name,
            'proxy_host': proxy['host'],
            'proxy_port': proxy['port'],
            'proxy_username': proxy.get('username'),
            'proxy_password': proxy.get('password'),
            'proxy_country': proxy.get('country', 'Unknown'),
            'email': email['email'],
            'email_password': email['password'],
            'profile_dir': str(profile_dir),
            'status': 'pending',
            'setup_complete': False,
            'created': datetime.now().isoformat()
        }
        
        return profile
    
    def setup_profile_auto(self, profile, progress_callback=None):
        """Automatically setup profile with proxy and Gmail login"""
        driver = None
        try:
            if progress_callback:
                progress_callback(f"Setting up {profile['name']}...")
            
            # Create Chrome options
            options = Options()
            options.add_argument(f"--user-data-dir={profile['profile_dir']}")
            
            # Don't use proxy in Chrome args, we'll handle it via auth popup
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Set Chrome binary
            if self.chrome_path:
                options.binary_location = self.chrome_path
            
            # Create driver
            driver = webdriver.Chrome(options=options)
            
            # Anti-detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            # Step 1: Setup proxy with authentication popup
            if progress_callback:
                progress_callback(f"Setting up proxy for {profile['name']}...")
            
            # Navigate to a site that will trigger proxy auth
            driver.get(f"http://{profile['proxy_username']}:{profile['proxy_password']}@{profile['proxy_host']}:{profile['proxy_port']}")
            time.sleep(2)
            
            # Handle proxy auth popup if it appears
            try:
                # Switch to alert (proxy auth popup)
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                alert = Alert(driver)
                
                # Send username and password
                alert.send_keys(profile['proxy_username'] + Keys.TAB + profile['proxy_password'])
                alert.accept()
                time.sleep(2)
            except:
                # No popup, might be using extension or already authenticated
                pass
            
            # Verify proxy is working
            driver.get("http://ipinfo.io/json")
            time.sleep(3)
            
            try:
                body = driver.find_element(By.TAG_NAME, "pre").text
                data = json.loads(body)
                if 'ip' in data:
                    profile['proxy_ip'] = data.get('ip', 'Unknown')
                    print(f"✓ Proxy working for {profile['name']}: {profile['proxy_ip']}")
            except:
                print(f"✗ Proxy failed for {profile['name']}")
                profile['status'] = 'proxy_failed'
                return False
            
            # Step 2: Login to Gmail
            if progress_callback:
                progress_callback(f"Logging into Gmail for {profile['name']}...")
            
            # Navigate to Gmail
            driver.get("https://accounts.google.com")
            time.sleep(3)
            
            # Enter email
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_input.clear()
            email_input.send_keys(profile['email'])
            
            # Click Next
            next_btn = driver.find_element(By.ID, "identifierNext")
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(3)
            
            # Enter password
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.clear()
            password_input.send_keys(profile['email_password'])
            
            # Click Sign in
            signin_btn = driver.find_element(By.ID, "passwordNext")
            driver.execute_script("arguments[0].click();", signin_btn)
            time.sleep(5)
            
            # Check if logged in
            if "myaccount.google.com" in driver.current_url or "mail.google.com" in driver.current_url:
                # Navigate to Gmail to ensure cookies are saved
                driver.get("https://mail.google.com")
                time.sleep(3)
                
                profile['status'] = 'ready'
                profile['setup_complete'] = True
                print(f"✓ Gmail logged in for {profile['name']}")
                
                # Save cookies
                self.save_cookies(driver, profile['id'])
                return True
            else:
                profile['status'] = 'email_failed'
                return False
            
        except Exception as e:
            print(f"Setup error for {profile['name']}: {e}")
            profile['status'] = 'error'
            return False
        finally:
            if driver:
                # Keep browser open for a moment to save session
                time.sleep(2)
                driver.quit()
    
    def save_cookies(self, driver, profile_id):
        """Save cookies for profile"""
        try:
            cookies = driver.get_cookies()
            cookie_file = self.data_dir / profile_id / "cookies.json"
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
        except Exception as e:
            print(f"Error saving cookies: {e}")
    
    def launch_profile(self, profile_id):
        """Launch a profile by ID for external use"""
        profile_dir = self.data_dir / profile_id
        
        if not profile_dir.exists():
            return False
        
        if not self.chrome_path:
            return False
        
        cmd = [
            self.chrome_path,
            f"--user-data-dir={profile_dir}",
            "--start-maximized"
        ]
        
        subprocess.Popen(cmd)
        return True
    
    def get_profile_info(self, profile_id):
        """Get profile information by ID"""
        profile_file = self.data_dir / profile_id / "profile_info.json"
        if profile_file.exists():
            with open(profile_file, 'r') as f:
                return json.load(f)
        return None


class ChromeProfileManagerGUI:
    """Main GUI Application with modified workflow"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome Profile Manager - Modified")
        self.root.geometry("1200x800")
        
        # Style
        self.setup_style()
        
        # Managers
        self.manager = ChromeProfileManager()
        self.gmail_validator = GmailValidator()
        self.proxy_manager = ProxyManager()
        
        # Database
        self.setup_database()
        
        # GUI
        self.setup_gui()
        
        # Load existing data
        self.load_data()
    
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
        self.db_path = "chrome_profiles_modified.db"
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
                proxy_country TEXT,
                proxy_ip TEXT,
                email TEXT,
                email_password TEXT,
                profile_dir TEXT,
                status TEXT DEFAULT 'pending',
                setup_complete BOOLEAN DEFAULT 0,
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
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT,
                password TEXT,
                country TEXT DEFAULT 'Unknown',
                added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def setup_gui(self):
        """Setup GUI components"""
        # Header
        header = tk.Frame(self.root, bg="#1a1a1a", height=80)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Chrome Profile Manager - Modified Workflow",
                font=('Arial', 24, 'bold'), bg="#1a1a1a", fg=self.accent_color).pack(pady=20)
        
        # Main workflow steps
        self.setup_workflow_panel()
        
        # Progress Frame
        self.setup_progress_frame()
        
        # Content tabs
        self.setup_content_area()
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                             bg="#1a1a1a", fg="#888888", anchor='w')
        status_bar.pack(fill='x', side='bottom', padx=10, pady=5)
    
    def setup_workflow_panel(self):
        """Setup workflow steps panel"""
        workflow_frame = tk.Frame(self.root, bg="#1a1a1a")
        workflow_frame.pack(fill='x', padx=10, pady=10)
        
        # Step labels
        steps = [
            ("Step 1: Upload Gmail CSV", self.upload_gmail_csv, self.accent_color),
            ("Step 2: Import Proxies", self.import_proxies, "#00aaff"),
            ("Step 3: Setup All Profiles", self.setup_all_profiles, "#ff6600"),
            ("Step 4: Export Profile IDs", self.export_profile_ids, "#888888")
        ]
        
        for i, (text, command, color) in enumerate(steps):
            tk.Button(workflow_frame, text=text, command=command,
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
                                          length=600)
    
    def setup_content_area(self):
        """Setup main content area with tabs"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Gmail Validation tab
        self.gmail_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.gmail_frame, text="Gmail Validation")
        self.setup_gmail_view()
        
        # Proxies tab
        self.proxies_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.proxies_frame, text="Proxies by Country")
        self.setup_proxies_view()
        
        # Profiles tab
        self.profiles_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.profiles_frame, text="Profiles")
        self.setup_profiles_view()
        
        # Log tab
        self.log_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(self.log_frame, text="Logs")
        self.setup_log_view()
    
    def setup_gmail_view(self):
        """Setup Gmail validation view"""
        # Good emails
        tk.Label(self.gmail_frame, text="Good Emails", 
                bg=self.bg_color, fg=self.accent_color,
                font=('Arial', 14, 'bold')).pack(pady=5)
        
        self.good_emails_text = scrolledtext.ScrolledText(self.gmail_frame, 
                                                         height=10, width=80,
                                                         bg="#1a1a1a", fg="#00ff00")
        self.good_emails_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Bad emails
        tk.Label(self.gmail_frame, text="Bad Emails", 
                bg=self.bg_color, fg=self.error_color,
                font=('Arial', 14, 'bold')).pack(pady=5)
        
        self.bad_emails_text = scrolledtext.ScrolledText(self.gmail_frame, 
                                                        height=10, width=80,
                                                        bg="#1a1a1a", fg="#ff4444")
        self.bad_emails_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def setup_proxies_view(self):
        """Setup proxies by country view"""
        # Country list
        country_frame = tk.Frame(self.proxies_frame, bg=self.bg_color)
        country_frame.pack(side='left', fill='y', padx=10, pady=10)
        
        tk.Label(country_frame, text="Countries", 
                bg=self.bg_color, fg=self.accent_color,
                font=('Arial', 12, 'bold')).pack()
        
        self.country_listbox = tk.Listbox(country_frame, bg="#1a1a1a", fg="white",
                                         selectbackground=self.accent_color)
        self.country_listbox.pack(fill='both', expand=True, pady=10)
        self.country_listbox.bind('<<ListboxSelect>>', self.on_country_select)
        
        # Proxy details
        details_frame = tk.Frame(self.proxies_frame, bg=self.bg_color)
        details_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(details_frame, text="Proxies in Selected Country", 
                bg=self.bg_color, fg=self.accent_color,
                font=('Arial', 12, 'bold')).pack()
        
        self.proxy_details_text = scrolledtext.ScrolledText(details_frame,
                                                           bg="#1a1a1a", fg="white")
        self.proxy_details_text.pack(fill='both', expand=True, pady=10)
    
    def setup_profiles_view(self):
        """Setup profiles treeview"""
        columns = ('Name', 'Proxy Country', 'Email', 'Status', 'Setup Complete', 'Profile ID')
        self.profiles_tree = ttk.Treeview(self.profiles_frame, columns=columns, show='tree headings')
        
        # Configure columns
        self.profiles_tree.heading('#0', text='#')
        self.profiles_tree.column('#0', width=50)
        
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
        
        # Right-click menu
        self.profiles_menu = tk.Menu(self.root, tearoff=0)
        self.profiles_menu.add_command(label="Launch Profile", command=self.launch_selected_profile)
        self.profiles_menu.add_command(label="Copy Profile ID", command=self.copy_profile_id)
        self.profiles_tree.bind("<Button-3>", self.show_profile_menu)
    
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
    
    def upload_gmail_csv(self):
        """Step 1: Upload and validate Gmail CSV"""
        filename = filedialog.askopenfilename(
            title="Select Gmail CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.log(f"Loading Gmail CSV: {filename}")
        self.show_progress("Validating Gmail accounts...")
        
        def validate_worker():
            def progress_callback(current, total, message):
                self.progress_var.set((current / total) * 100)
                self.progress_label.config(text=message)
                self.root.update()
            
            good, bad = self.gmail_validator.validate_from_csv(filename, progress_callback)
            
            # Update UI
            self.root.after(0, self.update_gmail_lists, good, bad)
            self.root.after(0, self.hide_progress)
            self.root.after(0, lambda: messagebox.showinfo("Validation Complete", 
                                                          f"Good: {len(good)}, Bad: {len(bad)}"))
        
        threading.Thread(target=validate_worker, daemon=True).start()
    
    def update_gmail_lists(self, good_emails, bad_emails):
        """Update Gmail lists in UI and database"""
        # Clear existing
        self.good_emails_text.delete('1.0', 'end')
        self.bad_emails_text.delete('1.0', 'end')
        
        # Update good emails
        for email_data in good_emails:
            self.good_emails_text.insert('end', f"{email_data['email']}:{email_data['password']}\n")
            
            # Save to database
            self.conn.execute('''
                INSERT OR REPLACE INTO validated_emails (email, password, status)
                VALUES (?, ?, 'good')
            ''', (email_data['email'], email_data['password']))
        
        # Update bad emails
        for email_data in bad_emails:
            self.bad_emails_text.insert('end', f"{email_data['email']}:{email_data['password']}\n")
            
            # Save to database
            self.conn.execute('''
                INSERT OR REPLACE INTO validated_emails (email, password, status)
                VALUES (?, ?, 'bad')
            ''', (email_data['email'], email_data['password']))
        
        self.conn.commit()
        self.log(f"Validation complete: {len(good_emails)} good, {len(bad_emails)} bad")
    
    def import_proxies(self):
        """Step 2: Import and categorize proxies"""
        dialog = ProxyImportDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.log("Categorizing proxies by country...")
            self.show_progress("Categorizing proxies...")
            
            def categorize_worker():
                proxies_by_country = self.proxy_manager.import_proxies(dialog.result)
                
                # Save to database
                for country, proxies in proxies_by_country.items():
                    for proxy in proxies:
                        self.conn.execute('''
                            INSERT INTO proxies (host, port, username, password, country)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (proxy['host'], proxy['port'], proxy['username'], 
                             proxy['password'], country))
                
                self.conn.commit()
                
                # Update UI
                self.root.after(0, self.update_proxy_view, proxies_by_country)
                self.root.after(0, self.hide_progress)
                self.root.after(0, lambda: messagebox.showinfo("Import Complete", 
                                                              f"Imported {len(self.proxy_manager.all_proxies)} proxies"))
            
            threading.Thread(target=categorize_worker, daemon=True).start()
    
    def update_proxy_view(self, proxies_by_country):
        """Update proxy view with categorized data"""
        # Clear country list
        self.country_listbox.delete(0, 'end')
        
        # Add countries
        for country in sorted(proxies_by_country.keys()):
            count = len(proxies_by_country[country])
            self.country_listbox.insert('end', f"{country} ({count})")
        
        self.log(f"Proxies categorized into {len(proxies_by_country)} countries")
    
    def on_country_select(self, event):
        """Handle country selection"""
        selection = self.country_listbox.curselection()
        if not selection:
            return
        
        country_text = self.country_listbox.get(selection[0])
        country = country_text.split(' (')[0]
        
        # Display proxies for selected country
        self.proxy_details_text.delete('1.0', 'end')
        
        if country in self.proxy_manager.proxies_by_country:
            for proxy in self.proxy_manager.proxies_by_country[country]:
                proxy_str = f"{proxy['host']}:{proxy['port']}"
                if proxy['username']:
                    proxy_str += f" (Auth: {proxy['username']})"
                self.proxy_details_text.insert('end', proxy_str + '\n')
    
    def setup_all_profiles(self):
        """Step 3: Setup all profiles automatically"""
        # Check if we have validated emails and proxies
        good_emails = self.gmail_validator.good_emails
        all_proxies = self.proxy_manager.all_proxies
        
        if not good_emails:
            messagebox.showwarning("Warning", "Please upload and validate Gmail accounts first")
            return
        
        if not all_proxies:
            messagebox.showwarning("Warning", "Please import proxies first")
            return
        
        # Create profiles
        profiles_to_create = min(len(good_emails), len(all_proxies))
        
        if messagebox.askyesno("Confirm", f"Create and setup {profiles_to_create} profiles?"):
            self.log(f"Creating {profiles_to_create} profiles...")
            self.show_progress("Setting up profiles...")
            
            def setup_worker():
                created_profiles = []
                
                # Create profiles
                for i in range(profiles_to_create):
                    profile_name = f"Profile_{i+1}_{good_emails[i]['email'].split('@')[0]}"
                    profile = self.manager.create_profile(
                        name=profile_name,
                        proxy=all_proxies[i],
                        email=good_emails[i]
                    )
                    created_profiles.append(profile)
                    
                    # Save to database
                    self.conn.execute('''
                        INSERT INTO profiles (id, name, proxy_host, proxy_port, 
                                            proxy_username, proxy_password, proxy_country,
                                            email, email_password, profile_dir, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (profile['id'], profile['name'], profile['proxy_host'], 
                         profile['proxy_port'], profile['proxy_username'], 
                         profile['proxy_password'], profile['proxy_country'],
                         profile['email'], profile['email_password'], 
                         profile['profile_dir'], profile['status']))
                
                self.conn.commit()
                
                # Setup each profile
                success_count = 0
                for i, profile in enumerate(created_profiles):
                    def progress_callback(message):
                        self.progress_var.set(((i + 0.5) / len(created_profiles)) * 100)
                        self.progress_label.config(text=message)
                        self.root.update()
                    
                    if self.manager.setup_profile_auto(profile, progress_callback):
                        success_count += 1
                        self.log(f"✓ Setup complete: {profile['name']}")
                        
                        # Save profile info to file for external use
                        profile_info_file = Path(profile['profile_dir']) / "profile_info.json"
                        with open(profile_info_file, 'w') as f:
                            json.dump(profile, f, indent=2)
                    else:
                        self.log(f"✗ Setup failed: {profile['name']}")
                    
                    # Update database
                    self.conn.execute('''
                        UPDATE profiles 
                        SET status = ?, setup_complete = ?, proxy_ip = ?
                        WHERE id = ?
                    ''', (profile['status'], profile['setup_complete'], 
                         profile.get('proxy_ip'), profile['id']))
                    self.conn.commit()
                    
                    # Update progress
                    self.progress_var.set(((i + 1) / len(created_profiles)) * 100)
                    
                    # Refresh display
                    self.root.after(0, self.load_profiles)
                
                self.root.after(0, self.hide_progress)
                self.root.after(0, lambda: messagebox.showinfo("Setup Complete", 
                                                              f"Successfully setup {success_count}/{len(created_profiles)} profiles"))
            
            threading.Thread(target=setup_worker, daemon=True).start()
    
    def export_profile_ids(self):
        """Step 4: Export profile IDs for external use"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt")]
        )
        
        if filename:
            cursor = self.conn.execute('''
                SELECT id, name, proxy_country, email, status, profile_dir 
                FROM profiles 
                WHERE setup_complete = 1
            ''')
            
            profiles = []
            for row in cursor:
                profiles.append({
                    'id': row['id'],
                    'name': row['name'],
                    'proxy_country': row['proxy_country'],
                    'email': row['email'],
                    'status': row['status'],
                    'profile_dir': row['profile_dir']
                })
            
            if filename.endswith('.json'):
                with open(filename, 'w') as f:
                    json.dump(profiles, f, indent=2)
            else:
                with open(filename, 'w') as f:
                    f.write("Profile IDs for external use:\n\n")
                    for profile in profiles:
                        f.write(f"ID: {profile['id']}\n")
                        f.write(f"Name: {profile['name']}\n")
                        f.write(f"Email: {profile['email']}\n")
                        f.write(f"Country: {profile['proxy_country']}\n")
                        f.write(f"Directory: {profile['profile_dir']}\n")
                        f.write("-" * 50 + "\n")
            
            messagebox.showinfo("Export Complete", f"Exported {len(profiles)} profile IDs")
            self.log(f"Exported {len(profiles)} profile IDs to {filename}")
    
    def launch_selected_profile(self):
        """Launch selected profile"""
        selection = self.profiles_tree.selection()
        if not selection:
            return
        
        item = self.profiles_tree.item(selection[0])
        profile_id = item['values'][5]  # Profile ID column
        
        if self.manager.launch_profile(profile_id):
            self.log(f"Launched profile: {profile_id}")
    
    def copy_profile_id(self):
        """Copy profile ID to clipboard"""
        selection = self.profiles_tree.selection()
        if not selection:
            return
        
        item = self.profiles_tree.item(selection[0])
        profile_id = item['values'][5]  # Profile ID column
        
        self.root.clipboard_clear()
        self.root.clipboard_append(profile_id)
        self.log(f"Copied profile ID: {profile_id}")
    
    def show_profile_menu(self, event):
        """Show right-click menu for profiles"""
        self.profiles_menu.post(event.x_root, event.y_root)
    
    def load_profiles(self):
        """Load profiles into treeview"""
        # Clear existing
        for item in self.profiles_tree.get_children():
            self.profiles_tree.delete(item)
        
        # Load from database
        cursor = self.conn.execute('SELECT * FROM profiles ORDER BY created DESC')
        
        for i, row in enumerate(cursor, 1):
            values = (
                row['name'],
                row['proxy_country'],
                row['email'],
                row['status'],
                '✓' if row['setup_complete'] else '✗',
                row['id']
            )
            
            # Color based on status
            tags = []
            if row['status'] == 'ready':
                tags.append('ready')
            elif 'failed' in row['status']:
                tags.append('failed')
            
            self.profiles_tree.insert('', 'end', text=str(i), values=values, tags=tags)
        
        # Configure tags
        self.profiles_tree.tag_configure('ready', foreground='#00ff00')
        self.profiles_tree.tag_configure('failed', foreground='#ff4444')
    
    def load_data(self):
        """Load existing data from database"""
        self.load_profiles()
        
        # Load validated emails
        cursor = self.conn.execute('SELECT * FROM validated_emails')
        good_emails = []
        bad_emails = []
        
        for row in cursor:
            email_data = {'email': row['email'], 'password': row['password']}
            if row['status'] == 'good':
                good_emails.append(email_data)
            else:
                bad_emails.append(email_data)
        
        self.gmail_validator.good_emails = good_emails
        self.gmail_validator.bad_emails = bad_emails
        self.update_gmail_lists(good_emails, bad_emails)
        
        # Load proxies
        cursor = self.conn.execute('SELECT DISTINCT country FROM proxies')
        countries = [row['country'] for row in cursor]
        
        proxies_by_country = {}
        for country in countries:
            cursor = self.conn.execute('SELECT * FROM proxies WHERE country = ?', (country,))
            proxies_by_country[country] = []
            for row in cursor:
                proxies_by_country[country].append({
                    'host': row['host'],
                    'port': row['port'],
                    'username': row['username'],
                    'password': row['password'],
                    'country': country
                })
        
        if proxies_by_country:
            self.proxy_manager.proxies_by_country = proxies_by_country
            self.update_proxy_view(proxies_by_country)
    
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


class ProxyImportDialog:
    """Dialog for importing proxies"""
    
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Import Proxies")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg="#1a1a1a")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title
        tk.Label(self.dialog, text="Import Proxies",
                font=('Arial', 18, 'bold'), bg="#1a1a1a", fg="#00ff88").pack(pady=20)
        
        # Instructions
        tk.Label(self.dialog, 
                text="Format: host:port:username:password or host:port",
                bg="#1a1a1a", fg="#888888", font=('Arial', 11)).pack()
        
        # Text area
        self.text = scrolledtext.ScrolledText(self.dialog, height=20, width=60,
                                            bg="#0a0a0a", fg="white",
                                            font=('Consolas', 10))
        self.text.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#1a1a1a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Import", command=self.import_proxies,
                 bg="#00ff88", fg="black", font=('Arial', 12, 'bold'),
                 bd=0, padx=40, pady=10).pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="Cancel", command=self.dialog.destroy,
                 bg="#666666", fg="white", font=('Arial', 11),
                 bd=0, padx=30, pady=10).pack(side='left', padx=10)
    
    def import_proxies(self):
        """Process proxy import"""
        content = self.text.get('1.0', 'end-1c').strip()
        if content:
            self.result = content
            self.dialog.destroy()


# Example of external script usage
def example_external_usage():
    """Example of how to use profiles from another script"""
    # Load profile IDs from exported JSON
    with open('profile_ids.json', 'r') as f:
        profiles = json.load(f)
    
    # Use specific profile
    profile_id = profiles[0]['id']
    profile_dir = profiles[0]['profile_dir']
    
    # Launch Chrome with this profile
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--start-maximized",
        "https://example.com"  # Your test site
    ]
    
    subprocess.Popen(cmd)


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Chrome Profile Manager - Modified Workflow")
    print("="*60)
    print("Workflow Steps:")
    print("1. Upload Gmail CSV (email,password)")
    print("2. Import proxies (categorized by country)")
    print("3. Auto-setup all profiles")
    print("4. Export profile IDs for external use")
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
    
    if not manager.driver_path:
        print("WARNING: ChromeDriver not found!")
        print("Download from: https://chromedriver.chromium.org/")
        print("Place chromedriver.exe in the same directory as this script")
    
    print("\nStarting GUI...\n")
    
    # Run GUI
    app = ChromeProfileManagerGUI()
    app.run()


if __name__ == "__main__":
    main()