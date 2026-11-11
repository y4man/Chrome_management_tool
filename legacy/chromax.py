#!/usr/bin/env python3
"""
Chrome Proxy Manager Enterprise Edition
Handles 1000+ profiles with automatic authentication
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
from concurrent.futures import ThreadPoolExecutor
import psutil
import proxy_profile_generator

# Try to import Selenium for automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not installed. Run: pip install selenium")


class ChromeProxyManagerEnterprise:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome Proxy Manager Enterprise - 1000+ Profiles")
        self.root.geometry("1400x900")
        
        # Colors
        self.bg_color = "#0a0a0a"
        self.card_bg = "#1a1a2e"
        self.accent_color = "#00ff88"
        self.danger_color = "#ff4444"
        self.warning_color = "#ffaa00"
        
        self.root.configure(bg=self.bg_color)
        
        # Database for better performance with 1000+ profiles
        self.init_database()
        
        # Queue for batch operations
        self.operation_queue = queue.Queue()
        self.processing = False
        self.cancel_processing = False
        
        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Chrome paths
        self.chrome_paths = self._get_chrome_paths()
        
        # Current page for pagination
        self.current_page = 0
        self.profiles_per_page = 50
        
        self.setup_ui()
        self.refresh_display()
        
    def init_database(self):
        """Initialize SQLite database for better performance"""
        self.db_path = "proxy_profiles.db"
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
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
                user_agent TEXT,
                status TEXT DEFAULT 'new',
                last_used TIMESTAMP,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auth_saved BOOLEAN DEFAULT 0,
                notes TEXT
            )
        ''')
        
        # Create index for faster searches
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON profiles(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON profiles(status)')
        self.conn.commit()
    
    def _get_chrome_paths(self):
        """Get Chrome paths for current OS"""
        system = platform.system()
        if system == "Windows":
            return [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
        elif system == "Darwin":
            return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
        else:
            return ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
    
    def setup_ui(self):
        """Setup the main UI"""
        # Header
        header_frame = tk.Frame(self.root, bg=self.card_bg, height=100)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame,
                              text="Chrome Proxy Manager Enterprise",
                              bg=self.card_bg,
                              fg=self.accent_color,
                              font=('Arial', 32, 'bold'))
        title_label.pack(pady=20)
        
        subtitle_label = tk.Label(header_frame,
                                 text="Manage 1000+ Chrome profiles with automatic proxy authentication",
                                 bg=self.card_bg,
                                 fg="#888888",
                                 font=('Arial', 14))
        subtitle_label.pack()
        
        # Stats frame
        self.setup_stats_frame()
        
        # Control panel
        self.setup_control_panel()
        
        # Progress bar for batch operations
        self.progress_frame = tk.Frame(self.root, bg=self.bg_color)
        self.progress_frame.pack(fill='x', padx=20, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, 
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=400)
        
        self.progress_label = tk.Label(self.progress_frame,
                                      text="",
                                      bg=self.bg_color,
                                      fg="#888888")
        
        # Main content area
        self.setup_content_area()
        
        # Pagination controls
        self.setup_pagination()
        
        # Status bar
        self.status_bar = tk.Label(self.root,
                                  text="Ready",
                                  bg=self.card_bg,
                                  fg="#888888",
                                  anchor='w',
                                  padx=10,
                                  font=('Arial', 10))
        self.status_bar.pack(fill='x', side='bottom')
    
    def setup_stats_frame(self):
        """Setup statistics display"""
        stats_frame = tk.Frame(self.root, bg=self.bg_color)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        # Total Profiles
        self.stat_total = self.create_stat_card(stats_frame, "Total Profiles", "0", self.accent_color)
        self.stat_total.pack(side='left', expand=True, fill='x', padx=5)
        
        # Ready (Auth Saved)
        self.stat_ready = self.create_stat_card(stats_frame, "Ready", "0", "#00ff00")
        self.stat_ready.pack(side='left', expand=True, fill='x', padx=5)
        
        # Pending Auth
        self.stat_pending = self.create_stat_card(stats_frame, "Pending Auth", "0", self.warning_color)
        self.stat_pending.pack(side='left', expand=True, fill='x', padx=5)
        
        # Active Sessions
        self.stat_active = self.create_stat_card(stats_frame, "Active", "0", "#00aaff")
        self.stat_active.pack(side='left', expand=True, fill='x', padx=5)
    
    def create_stat_card(self, parent, label, value, color):
        """Create a statistics card"""
        card = tk.Frame(parent, bg=self.card_bg, height=80)
        card.pack_propagate(False)
        
        value_label = tk.Label(card,
                              text=value,
                              bg=self.card_bg,
                              fg=color,
                              font=('Arial', 28, 'bold'))
        value_label.pack(pady=(10, 0))
        card.value_label = value_label  # Store reference
        
        text_label = tk.Label(card,
                             text=label,
                             bg=self.card_bg,
                             fg="#888888",
                             font=('Arial', 11))
        text_label.pack()
        
        return card
    
    def setup_control_panel(self):
        """Setup control buttons"""
        control_frame = tk.Frame(self.root, bg=self.bg_color)
        control_frame.pack(fill='x', padx=20, pady=10)
        
        # Left side buttons
        left_frame = tk.Frame(control_frame, bg=self.bg_color)
        left_frame.pack(side='left')
        
        tk.Button(left_frame,
                 text="📁 Batch Import",
                 bg=self.accent_color,
                 fg="#000000",
                 font=('Arial', 11, 'bold'),
                 bd=0,
                 padx=20,
                 pady=10,
                 cursor='hand2',
                 command=self.batch_import).pack(side='left', padx=5)
        
        tk.Button(left_frame,
                 text="🔐 Auto Setup All",
                 bg="#00aaff",
                 fg="white",
                 font=('Arial', 11, 'bold'),
                 bd=0,
                 padx=20,
                 pady=10,
                 cursor='hand2',
                 command=self.auto_setup_all).pack(side='left', padx=5)
        
        tk.Button(left_frame,
                 text="🚀 Launch Multiple",
                 bg="#ff6600",
                 fg="white",
                 font=('Arial', 11, 'bold'),
                 bd=0,
                 padx=20,
                 pady=10,
                 cursor='hand2',
                 command=self.launch_multiple).pack(side='left', padx=5)
        
        tk.Button(left_frame,
                 text="📊 Export",
                 bg=self.card_bg,
                 fg="#cccccc",
                 font=('Arial', 11),
                 bd=0,
                 padx=20,
                 pady=10,
                 cursor='hand2',
                 command=self.export_profiles).pack(side='left', padx=5)
        
        # Search box
        search_frame = tk.Frame(control_frame, bg=self.bg_color)
        search_frame.pack(side='right', fill='x', expand=True, padx=(20, 0))
        
        tk.Label(search_frame,
                text="Search:",
                bg=self.bg_color,
                fg="#888888",
                font=('Arial', 11)).pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_profiles())
        
        search_entry = tk.Entry(search_frame,
                               textvariable=self.search_var,
                               bg=self.card_bg,
                               fg="white",
                               insertbackground="white",
                               font=('Arial', 11),
                               bd=1)
        search_entry.pack(side='left', fill='x', expand=True)
    
    def setup_content_area(self):
        """Setup scrollable content area"""
        # Canvas for scrolling
        canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        canvas_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        
        self.profiles_frame = tk.Frame(canvas, bg=self.bg_color)
        
        canvas.create_window((0, 0), window=self.profiles_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.profiles_frame.bind('<Configure>',
                                lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def setup_pagination(self):
        """Setup pagination controls"""
        pagination_frame = tk.Frame(self.root, bg=self.bg_color)
        pagination_frame.pack(fill='x', padx=20, pady=5)
        
        tk.Button(pagination_frame,
                 text="◀ Previous",
                 bg=self.card_bg,
                 fg="#888888",
                 font=('Arial', 10),
                 bd=0,
                 padx=15,
                 pady=5,
                 command=self.prev_page).pack(side='left', padx=5)
        
        self.page_label = tk.Label(pagination_frame,
                                  text="Page 1 of 1",
                                  bg=self.bg_color,
                                  fg="#888888",
                                  font=('Arial', 10))
        self.page_label.pack(side='left', padx=20)
        
        tk.Button(pagination_frame,
                 text="Next ▶",
                 bg=self.card_bg,
                 fg="#888888",
                 font=('Arial', 10),
                 bd=0,
                 padx=15,
                 pady=5,
                 command=self.next_page).pack(side='left', padx=5)
    
    def batch_import(self):
        """Import proxies from file or text"""
        dialog = BatchImportDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.show_progress("Importing profiles...")
            
            def import_worker():
                proxies = dialog.result['proxies']
                base_name = dialog.result['base_name']
                total = len(proxies)
                
                for i, proxy_line in enumerate(proxies):
                    if self.cancel_processing:
                        break
                    
                    try:
                        # Parse proxy
                        parts = proxy_line.strip().split(':')
                        if len(parts) >= 2:
                            profile_id = f"profile_{uuid.uuid4().hex[:12]}"
                            
                            self.conn.execute('''
                                INSERT INTO profiles 
                                (id, name, proxy_host, proxy_port, proxy_username, proxy_password)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                profile_id,
                                f"{base_name} #{i+1}",
                                parts[0],
                                int(parts[1]),
                                parts[2] if len(parts) > 2 else None,
                                parts[3] if len(parts) > 3 else None
                            ))
                            
                            # Update progress
                            progress = ((i + 1) / total) * 100
                            self.root.after(0, self.update_progress, progress, f"Imported {i+1}/{total}")
                    except Exception as e:
                        print(f"Error importing proxy: {e}")
                
                self.conn.commit()
                self.root.after(0, self.import_complete, total)
            
            threading.Thread(target=import_worker, daemon=True).start()
    
    def auto_setup_all(self):
        """Automatically setup authentication for all profiles"""
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("Error", "Selenium is required for auto-setup.\nRun: pip install selenium")
            return
        
        # Get profiles that need auth setup
        cursor = self.conn.execute('''
            SELECT * FROM profiles 
            WHERE auth_saved = 0 AND proxy_username IS NOT NULL
            LIMIT 100
        ''')
        profiles = cursor.fetchall()
        
        if not profiles:
            messagebox.showinfo("Info", "No profiles need authentication setup!")
            return
        
        result = messagebox.askyesno("Auto Setup", 
                                    f"Setup authentication for {len(profiles)} profiles?\n\n"
                                    "This will launch Chrome instances and save credentials automatically.")
        if not result:
            return
        
        self.show_progress("Setting up authentication...")
        self.cancel_processing = False
        
        def setup_worker():
            total = len(profiles)
            success = 0
            
            for i, profile in enumerate(profiles):
                if self.cancel_processing:
                    break
                
                try:
                    # Update progress
                    self.root.after(0, self.update_progress, 
                                   ((i + 1) / total) * 100,
                                   f"Setting up {profile['name']}...")
                    
                    # Setup authentication
                    if self.setup_profile_auth(dict(profile)):
                        success += 1
                        # Mark as auth saved
                        self.conn.execute(
                            'UPDATE profiles SET auth_saved = 1, status = "ready" WHERE id = ?',
                            (profile['id'],)
                        )
                        self.conn.commit()
                    
                    # Small delay between profiles
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error setting up {profile['name']}: {e}")
            
            self.root.after(0, self.setup_complete, success, total)
        
        threading.Thread(target=setup_worker, daemon=True).start()
    
    def setup_profile_auth(self, profile):
        """Setup authentication for a single profile using Selenium"""
        try:
            chrome_path = self.get_chrome_path()
            if not chrome_path:
                return False
            
            # Profile directory
            profile_dir = os.path.join(os.getcwd(), "chrome_data", profile['id'])
            os.makedirs(profile_dir, exist_ok=True)
            
            # Chrome options
            options = Options()
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument(f"--proxy-server={profile['proxy_host']}:{profile['proxy_port']}")
            options.add_argument("--start-maximized")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            driver = webdriver.Chrome(options=options)
            
            try:
                # Navigate to a test page
                driver.get("http://httpbin.org/ip")
                
                # Handle authentication dialog if it appears
                # Chrome will show native auth dialog
                
                # Wait a moment for auth dialog
                time.sleep(2)
                
                # Try to send credentials using autoit or pyautogui if available
                try:
                    import pyautogui
                    # Type username
                    pyautogui.typewrite(profile['proxy_username'])
                    pyautogui.press('tab')
                    # Type password
                    pyautogui.typewrite(profile['proxy_password'])
                    pyautogui.press('enter')
                except:
                    # If pyautogui not available, use JavaScript approach
                    # This creates a basic auth URL
                    auth_url = f"http://{profile['proxy_username']}:{profile['proxy_password']}@httpbin.org/ip"
                    driver.get(auth_url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Check if authentication worked
                try:
                    ip_element = driver.find_element(By.TAG_NAME, "body")
                    if "origin" in ip_element.text:
                        # Success - credentials are saved
                        return True
                except:
                    pass
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"Selenium error: {e}")
            
        return False
    
    def launch_multiple(self):
        """Launch multiple profiles at once"""
        dialog = LaunchMultipleDialog(self.root, self.conn)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            profiles = dialog.result['profiles']
            delay = dialog.result['delay']
            
            def launch_worker():
                for i, profile in enumerate(profiles):
                    if self.cancel_processing:
                        break
                    
                    self.launch_profile(dict(profile), silent=True)
                    
                    if i < len(profiles) - 1:
                        time.sleep(delay)
                
                self.root.after(0, messagebox.showinfo, "Complete", 
                              f"Launched {len(profiles)} profiles")
            
            threading.Thread(target=launch_worker, daemon=True).start()
    
    def launch_profile(self, profile, silent=False):
        """Launch a single profile"""
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            if not silent:
                messagebox.showerror("Error", "Chrome not found!")
            return
        
        profile_dir = os.path.join(os.getcwd(), "chrome_data", profile['id'])
        os.makedirs(profile_dir, exist_ok=True)
        
        # Build command
        cmd = [
            chrome_path,
            f"--user-data-dir={profile_dir}",
            f"--proxy-server={profile['proxy_host']}:{profile['proxy_port']}"
        ]
        
        if profile.get('user_agent'):
            cmd.append(f"--user-agent={profile['user_agent']}")
        
        # Launch
        subprocess.Popen(cmd)
        
        # Update last used
        self.conn.execute(
            'UPDATE profiles SET last_used = CURRENT_TIMESTAMP WHERE id = ?',
            (profile['id'],)
        )
        self.conn.commit()
        
        if not silent:
            self.update_status(f"Launched: {profile['name']}")
    
    def create_profile_card(self, profile):
        """Create a profile card widget"""
        card = tk.Frame(self.profiles_frame, bg=self.card_bg, relief='solid', bd=1)
        card.pack(fill='x', pady=3, padx=5)
        
        # Status indicator
        status_color = "#00ff00" if profile['auth_saved'] else self.warning_color
        status_bar = tk.Frame(card, bg=status_color, height=4)
        status_bar.pack(fill='x')
        
        # Content
        content = tk.Frame(card, bg=self.card_bg)
        content.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Left side - Info
        info_frame = tk.Frame(content, bg=self.card_bg)
        info_frame.pack(side='left', fill='x', expand=True)
        
        name_label = tk.Label(info_frame,
                             text=profile['name'],
                             bg=self.card_bg,
                             fg="white",
                             font=('Arial', 12, 'bold'))
        name_label.pack(anchor='w')
        
        proxy_text = f"{profile['proxy_host']}:{profile['proxy_port']}"
        if profile['proxy_username']:
            proxy_text += f" ({profile['proxy_username']})"
        
        proxy_label = tk.Label(info_frame,
                             text=proxy_text,
                             bg=self.card_bg,
                             fg="#888888",
                             font=('Arial', 10))
        proxy_label.pack(anchor='w')
        
        status_text = "✓ Ready" if profile['auth_saved'] else "⚠ Auth Required"
        status_label = tk.Label(info_frame,
                               text=status_text,
                               bg=self.card_bg,
                               fg=status_color,
                               font=('Arial', 9))
        status_label.pack(anchor='w')
        
        # Right side - Actions
        actions_frame = tk.Frame(content, bg=self.card_bg)
        actions_frame.pack(side='right')
        
        tk.Button(actions_frame,
                 text="▶",
                 bg="#00ff00",
                 fg="black",
                 font=('Arial', 10, 'bold'),
                 bd=0,
                 width=3,
                 cursor='hand2',
                 command=lambda: self.launch_profile(dict(profile))).pack(side='left', padx=2)
        
        if not profile['auth_saved'] and profile['proxy_username']:
            tk.Button(actions_frame,
                     text="🔐",
                     bg=self.warning_color,
                     fg="black",
                     font=('Arial', 10),
                     bd=0,
                     width=3,
                     cursor='hand2',
                     command=lambda: self.setup_single_auth(dict(profile))).pack(side='left', padx=2)
        
        tk.Button(actions_frame,
                 text="🗑",
                 bg=self.danger_color,
                 fg="white",
                 font=('Arial', 10),
                 bd=0,
                 width=3,
                 cursor='hand2',
                 command=lambda: self.delete_profile(profile['id'])).pack(side='left', padx=2)
    
    def setup_single_auth(self, profile):
        """Setup auth for a single profile"""
        if messagebox.askyesno("Setup Authentication", 
                              f"Setup authentication for {profile['name']}?"):
            self.show_progress("Setting up authentication...")
            
            def worker():
                success = self.setup_profile_auth(profile)
                if success:
                    self.conn.execute(
                        'UPDATE profiles SET auth_saved = 1, status = "ready" WHERE id = ?',
                        (profile['id'],)
                    )
                    self.conn.commit()
                    self.root.after(0, messagebox.showinfo, "Success", "Authentication saved!")
                else:
                    self.root.after(0, messagebox.showerror, "Error", "Failed to setup authentication")
                
                self.root.after(0, self.hide_progress)
                self.root.after(0, self.refresh_display)
            
            threading.Thread(target=worker, daemon=True).start()
    
    def delete_profile(self, profile_id):
        """Delete a profile"""
        if messagebox.askyesno("Delete", "Delete this profile?"):
            self.conn.execute('DELETE FROM profiles WHERE id = ?', (profile_id,))
            self.conn.commit()
            
            # Delete profile data
            profile_dir = os.path.join(os.getcwd(), "chrome_data", profile_id)
            if os.path.exists(profile_dir):
                try:
                    shutil.rmtree(profile_dir)
                except:
                    pass
            
            self.refresh_display()
    
    def refresh_display(self):
        """Refresh the profiles display"""
        # Clear existing
        for widget in self.profiles_frame.winfo_children():
            widget.destroy()
        
        # Get search term
        search = self.search_var.get().strip()
        
        # Count total profiles
        if search:
            cursor = self.conn.execute(
                'SELECT COUNT(*) FROM profiles WHERE name LIKE ?',
                (f'%{search}%',)
            )
        else:
            cursor = self.conn.execute('SELECT COUNT(*) FROM profiles')
        
        total = cursor.fetchone()[0]
        
        # Update stats
        self.update_stats()
        
        # Calculate pages
        total_pages = max(1, (total + self.profiles_per_page - 1) // self.profiles_per_page)
        self.current_page = min(self.current_page, total_pages - 1)
        
        # Update pagination label
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")
        
        # Get profiles for current page
        offset = self.current_page * self.profiles_per_page
        
        if search:
            cursor = self.conn.execute('''
                SELECT * FROM profiles 
                WHERE name LIKE ? 
                ORDER BY created DESC 
                LIMIT ? OFFSET ?
            ''', (f'%{search}%', self.profiles_per_page, offset))
        else:
            cursor = self.conn.execute('''
                SELECT * FROM profiles 
                ORDER BY created DESC 
                LIMIT ? OFFSET ?
            ''', (self.profiles_per_page, offset))
        
        profiles = cursor.fetchall()
        
        if not profiles:
            tk.Label(self.profiles_frame,
                    text="No profiles found" if search else "No profiles yet. Click 'Batch Import' to add profiles.",
                    bg=self.bg_color,
                    fg="#666666",
                    font=('Arial', 14)).pack(pady=50)
        else:
            for profile in profiles:
                self.create_profile_card(profile)
    
    def update_stats(self):
        """Update statistics"""
        # Total
        cursor = self.conn.execute('SELECT COUNT(*) FROM profiles')
        total = cursor.fetchone()[0]
        self.stat_total.value_label.config(text=str(total))
        
        # Ready
        cursor = self.conn.execute('SELECT COUNT(*) FROM profiles WHERE auth_saved = 1')
        ready = cursor.fetchone()[0]
        self.stat_ready.value_label.config(text=str(ready))
        
        # Pending
        cursor = self.conn.execute(
            'SELECT COUNT(*) FROM profiles WHERE auth_saved = 0 AND proxy_username IS NOT NULL'
        )
        pending = cursor.fetchone()[0]
        self.stat_pending.value_label.config(text=str(pending))
        
        # Active (estimate based on Chrome processes)
        try:
            chrome_count = sum(1 for p in psutil.process_iter(['name']) 
                             if 'chrome' in p.info['name'].lower())
            self.stat_active.value_label.config(text=str(chrome_count))
        except:
            self.stat_active.value_label.config(text="0")
    
    def search_profiles(self):
        """Search profiles"""
        self.current_page = 0
        self.refresh_display()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_display()
    
    def next_page(self):
        """Go to next page"""
        # Check if there are more pages
        cursor = self.conn.execute('SELECT COUNT(*) FROM profiles')
        total = cursor.fetchone()[0]
        total_pages = (total + self.profiles_per_page - 1) // self.profiles_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh_display()
    
    def show_progress(self, message):
        """Show progress bar"""
        self.progress_label.config(text=message)
        self.progress_label.pack(side='left', padx=10)
        self.progress_bar.pack(side='left', fill='x', expand=True)
        self.progress_var.set(0)
        
        # Add cancel button
        self.cancel_btn = tk.Button(self.progress_frame,
                                   text="Cancel",
                                   bg=self.danger_color,
                                   fg="white",
                                   bd=0,
                                   padx=10,
                                   command=self.cancel_operation)
        self.cancel_btn.pack(side='right', padx=10)
    
    def hide_progress(self):
        """Hide progress bar"""
        self.progress_label.pack_forget()
        self.progress_bar.pack_forget()
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.pack_forget()
        self.cancel_processing = False
    
    def update_progress(self, value, message):
        """Update progress"""
        self.progress_var.set(value)
        self.progress_label.config(text=message)
    
    def cancel_operation(self):
        """Cancel current operation"""
        self.cancel_processing = True
    
    def import_complete(self, count):
        """Import operation complete"""
        self.hide_progress()
        self.refresh_display()
        messagebox.showinfo("Import Complete", f"Successfully imported {count} profiles!")
    
    def setup_complete(self, success, total):
        """Setup operation complete"""
        self.hide_progress()
        self.refresh_display()
        messagebox.showinfo("Setup Complete", 
                          f"Successfully setup {success} out of {total} profiles!")
    
    def export_profiles(self):
        """Export profiles to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv")]
        )
        
        if filename:
            cursor = self.conn.execute('SELECT * FROM profiles')
            profiles = cursor.fetchall()
            
            if filename.endswith('.json'):
                # Export as JSON
                data = []
                for p in profiles:
                    data.append({
                        'id': p['id'],
                        'name': p['name'],
                        'proxy': f"{p['proxy_host']}:{p['proxy_port']}:{p['proxy_username'] or ''}:{p['proxy_password'] or ''}",
                        'auth_saved': p['auth_saved']
                    })
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                # Export as CSV
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Host', 'Port', 'Username', 'Password', 'Auth Saved'])
                    for p in profiles:
                        writer.writerow([
                            p['name'], 
                            p['proxy_host'], 
                            p['proxy_port'],
                            p['proxy_username'] or '',
                            p['proxy_password'] or '',
                            'Yes' if p['auth_saved'] else 'No'
                        ])
            
            messagebox.showinfo("Export Complete", f"Exported {len(profiles)} profiles")
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.after(3000, lambda: self.status_bar.config(text="Ready"))
    
    def get_chrome_path(self):
        """Get Chrome executable path"""
        for path in self.chrome_paths:
            if os.path.exists(path):
                return path
        return None
    
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Clean up on close"""
        self.conn.close()
        self.executor.shutdown(wait=False)
        self.root.destroy()


class BatchImportDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Import Proxies")
        self.dialog.geometry("700x600")
        self.dialog.configure(bg="#1a1a2e")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title
        tk.Label(self.dialog,
                text="Batch Import Proxies",
                font=('Arial', 20, 'bold'),
                bg="#1a1a2e",
                fg="#00ff88").pack(pady=20)
        
        # Instructions
        tk.Label(self.dialog,
                text="Format: host:port:username:password (one per line)\nOr import from file",
                bg="#1a1a2e",
                fg="#888888",
                font=('Arial', 11)).pack()
        
        # Base name
        name_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        name_frame.pack(pady=10)
        
        tk.Label(name_frame, text="Base Name:", bg="#1a1a2e", fg="white").pack(side='left', padx=5)
        self.base_name = tk.Entry(name_frame, width=30, bg="#2a2a3e", fg="white")
        self.base_name.insert(0, "Proxy")
        self.base_name.pack(side='left')
        
        # Import from file button
        tk.Button(self.dialog,
                 text="Import from File",
                 bg="#00aaff",
                 fg="white",
                 bd=0,
                 padx=20,
                 pady=8,
                 command=self.import_from_file).pack(pady=10)
        
        # Text area
        text_frame = tk.Frame(self.dialog, bg="#0a0a0a")
        text_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.text = tk.Text(text_frame,
                           bg="#0a0a0a",
                           fg="white",
                           insertbackground="white",
                           yscrollcommand=scrollbar.set)
        self.text.pack(fill='both', expand=True)
        scrollbar.config(command=self.text.yview)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame,
                 text="Import",
                 bg="#00ff88",
                 fg="black",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.do_import).pack(side='left', padx=10)
        
        tk.Button(btn_frame,
                 text="Cancel",
                 bg="#666666",
                 fg="white",
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.dialog.destroy).pack(side='left', padx=10)
    
    def import_from_file(self):
        """Import from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'r') as f:
                content = f.read()
                self.text.delete("1.0", "end")
                self.text.insert("1.0", content)
    
    def do_import(self):
        """Process import"""
        content = self.text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Warning", "Please enter proxies or import from file")
            return
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        self.result = {
            'base_name': self.base_name.get() or "Proxy",
            'proxies': lines
        }
        
        self.dialog.destroy()


class LaunchMultipleDialog:
    def __init__(self, parent, conn):
        self.result = None
        self.conn = conn
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Launch Multiple Profiles")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg="#1a1a2e")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title 
        tk.Label(self.dialog,
                text="Launch Multiple Profiles",
                font=('Arial', 20, 'bold'),
                bg="#1a1a2e",
                fg="#00ff88").pack(pady=20)
        
        # Options
        options_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        options_frame.pack(pady=10)
        
        tk.Label(options_frame, text="Launch:", bg="#1a1a2e", fg="white").grid(row=0, column=0, sticky='e', padx=10)
        
        self.launch_option = tk.StringVar(value="ready")
        tk.Radiobutton(options_frame, text="Ready profiles only", 
                      variable=self.launch_option, value="ready",
                      bg="#1a1a2e", fg="white", selectcolor="#2a2a3e").grid(row=0, column=1, sticky='w')
        
        tk.Radiobutton(options_frame, text="All profiles", 
                      variable=self.launch_option, value="all",
                      bg="#1a1a2e", fg="white", selectcolor="#2a2a3e").grid(row=1, column=1, sticky='w')
        
        tk.Label(options_frame, text="Delay between launches:", 
                bg="#1a1a2e", fg="white").grid(row=2, column=0, sticky='e', padx=10, pady=10)
        
        self.delay_var = tk.IntVar(value=5)
        delay_frame = tk.Frame(options_frame, bg="#1a1a2e")
        delay_frame.grid(row=2, column=1, sticky='w')
        
        tk.Scale(delay_frame, from_=1, to=30, orient='horizontal',
                variable=self.delay_var, bg="#1a1a2e", fg="white",
                highlightthickness=0, length=200).pack(side='left')
        
        self.delay_label = tk.Label(delay_frame, text="5 seconds", bg="#1a1a2e", fg="#888888")
        self.delay_label.pack(side='left', padx=10)
        
        self.delay_var.trace('w', lambda *args: self.delay_label.config(text=f"{self.delay_var.get()} seconds"))
        
        tk.Label(options_frame, text="Maximum profiles:", 
                bg="#1a1a2e", fg="white").grid(row=3, column=0, sticky='e', padx=10, pady=10)
        
        self.max_var = tk.IntVar(value=10)
        tk.Spinbox(options_frame, from_=1, to=100, textvariable=self.max_var,
                  bg="#2a2a3e", fg="white", width=10).grid(row=3, column=1, sticky='w')
        
        # Preview
        preview_label = tk.Label(self.dialog, text="Preview:", bg="#1a1a2e", fg="white")
        preview_label.pack(pady=(20, 5))
        
        preview_frame = tk.Frame(self.dialog, bg="#0a0a0a")
        preview_frame.pack(fill='both', expand=True, padx=20, pady=5)
        
        scrollbar = tk.Scrollbar(preview_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.preview_listbox = tk.Listbox(preview_frame,
                                         bg="#0a0a0a",
                                         fg="white",
                                         yscrollcommand=scrollbar.set)
        self.preview_listbox.pack(fill='both', expand=True)
        scrollbar.config(command=self.preview_listbox.yview)
        
        # Update preview
        self.update_preview()
        self.launch_option.trace('w', lambda *args: self.update_preview())
        self.max_var.trace('w', lambda *args: self.update_preview())
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame,
                 text="Launch",
                 bg="#ff6600",
                 fg="white",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.launch).pack(side='left', padx=10)
        
        tk.Button(btn_frame,
                 text="Cancel",
                 bg="#666666",
                 fg="white",
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.dialog.destroy).pack(side='left', padx=10)
    
    def update_preview(self):
        """Update preview list"""
        self.preview_listbox.delete(0, 'end')
        
        # Get profiles
        if self.launch_option.get() == "ready":
            cursor = self.conn.execute(
                'SELECT name FROM profiles WHERE auth_saved = 1 LIMIT ?',
                (self.max_var.get(),)
            )
        else:
            cursor = self.conn.execute(
                'SELECT name FROM profiles LIMIT ?',
                (self.max_var.get(),)
            )
        
        profiles = cursor.fetchall()
        
        for i, profile in enumerate(profiles):
            self.preview_listbox.insert('end', f"{i+1}. {profile['name']}")
    
    def launch(self):
        """Launch selected profiles"""
        # Get profiles
        if self.launch_option.get() == "ready":
            cursor = self.conn.execute(
                'SELECT * FROM profiles WHERE auth_saved = 1 LIMIT ?',
                (self.max_var.get(),)
            )
        else:
            cursor = self.conn.execute(
                'SELECT * FROM profiles LIMIT ?',
                (self.max_var.get(),)
            )
        
        profiles = cursor.fetchall()
        
        if not profiles:
            messagebox.showwarning("Warning", "No profiles to launch")
            return
        
        self.result = {
            'profiles': profiles,
            'delay': self.delay_var.get()
        }
        
        self.dialog.destroy()


# Developer API
class ProxyManagerAPI:
    """API for developers to use profiles programmatically"""
    def __init__(self, db_path="proxy_profiles.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def get_profile(self, profile_id):
        """Get profile by ID"""
        cursor = self.conn.execute('SELECT * FROM profiles WHERE id = ?', (profile_id,))
        return cursor.fetchone()
    
    def get_ready_profiles(self, limit=None):
        """Get profiles with saved authentication"""
        query = 'SELECT * FROM profiles WHERE auth_saved = 1'
        if limit:
            query += f' LIMIT {limit}'
        cursor = self.conn.execute(query)
        return cursor.fetchall()
    
    def launch_profile(self, profile_id, headless=False):
        """Launch Chrome with profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        
        chrome_path = self._find_chrome()
        if not chrome_path:
            return False
        
        profile_dir = os.path.join(os.getcwd(), "chrome_data", profile_id)
        os.makedirs(profile_dir, exist_ok=True)
        
        cmd = [
            chrome_path,
            f"--user-data-dir={profile_dir}",
            f"--proxy-server={profile['proxy_host']}:{profile['proxy_port']}"
        ]
        
        if headless:
            cmd.append("--headless")
        
        subprocess.Popen(cmd)
        return True
    
    def _find_chrome(self):
        """Find Chrome executable"""
        if platform.system() == "Windows":
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        return None


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Chrome Proxy Manager Enterprise Edition")
    print("="*60)
    print("Features:")
    print("- Handle 1000+ profiles efficiently")
    print("- Automatic authentication setup")
    print("- Batch operations")
    print("- SQLite database for performance")
    print("- Pagination for large datasets")
    print("- API for developers")
    print("="*60 + "\n")
    
    if not SELENIUM_AVAILABLE:
        print("⚠️  WARNING: Selenium not installed!")
        print("   Auto-authentication setup requires Selenium.")
        print("   Install with: pip install selenium")
        print("   Also install pyautogui for better auth handling: pip install pyautogui\n")
    
    app = ChromeProxyManagerEnterprise()
    app.run()