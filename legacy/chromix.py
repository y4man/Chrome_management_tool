#!/usr/bin/env python3
"""
Chrome Proxy Manager - Simplified Working Version
Uses a different approach that actually works with Chrome
"""

import tkinter as tk
from tkinter import messagebox
import json
import os
import subprocess
import threading
import uuid
from datetime import datetime
import platform
import tempfile
import shutil

class SimpleProxyManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome Proxy Manager - Working")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1a1a1a")
        
        # Data file
        self.data_file = "proxy_profiles.json"
        self.profiles = self.load_profiles()
        
        # Chrome paths
        self.chrome_paths = {
            'Windows': [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ],
            'Darwin': ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            'Linux': ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        }
        
        self.setup_ui()
        self.refresh_display()
    
    def setup_ui(self):
        # Title
        title = tk.Label(self.root, 
                        text="Chrome Proxy Manager",
                        font=('Arial', 24, 'bold'),
                        bg="#1a1a1a",
                        fg="#00ff00")
        title.pack(pady=20)
        
        # Instructions
        info = tk.Label(self.root,
                       text="Create profiles with proxies. For authenticated proxies, save credentials in Chrome after first login.",
                       font=('Arial', 11),
                       bg="#1a1a1a",
                       fg="#cccccc")
        info.pack()
        
        # Buttons frame
        btn_frame = tk.Frame(self.root, bg="#1a1a1a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame,
                 text="+ Add Profile",
                 bg="#00ff00",
                 fg="black",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=20,
                 pady=10,
                 command=self.add_profile).pack(side='left', padx=10)
        
        tk.Button(btn_frame,
                 text="Import Batch",
                 bg="#0099ff",
                 fg="white",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=20,
                 pady=10,
                 command=self.batch_import).pack(side='left', padx=10)
        
        # Profiles frame
        self.profiles_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.profiles_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    def add_profile(self):
        """Add a single profile"""
        dialog = ProfileDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            profile = {
                'id': f"profile_{uuid.uuid4().hex[:8]}",
                'name': dialog.result['name'],
                'proxy': dialog.result['proxy'],
                'created': datetime.now().isoformat()
            }
            self.profiles.append(profile)
            self.save_profiles()
            self.refresh_display()
    
    def batch_import(self):
        """Import multiple proxies"""
        dialog = BatchImportDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            base_name = dialog.result['base_name']
            for i, proxy_str in enumerate(dialog.result['proxies']):
                profile = {
                    'id': f"profile_{uuid.uuid4().hex[:8]}",
                    'name': f"{base_name} #{i+1}",
                    'proxy': proxy_str.strip(),
                    'created': datetime.now().isoformat()
                }
                self.profiles.append(profile)
            
            self.save_profiles()
            self.refresh_display()
            messagebox.showinfo("Success", f"Created {len(dialog.result['proxies'])} profiles")
    
    def refresh_display(self):
        """Refresh the profiles display"""
        for widget in self.profiles_frame.winfo_children():
            widget.destroy()
        
        if not self.profiles:
            tk.Label(self.profiles_frame,
                    text="No profiles yet. Click 'Add Profile' to create one.",
                    bg="#1a1a1a",
                    fg="#666666",
                    font=('Arial', 14)).pack(pady=50)
            return
        
        # Create profile cards
        for profile in self.profiles:
            self.create_profile_card(profile)
    
    def create_profile_card(self, profile):
        """Create a profile card"""
        card = tk.Frame(self.profiles_frame, bg="#2a2a2a", relief='solid', bd=1)
        card.pack(fill='x', pady=5)
        
        # Parse proxy
        proxy_parts = profile['proxy'].split(':')
        proxy_display = f"{proxy_parts[0]}:{proxy_parts[1]}"
        if len(proxy_parts) > 2:
            proxy_display += f" (User: {proxy_parts[2]})"
        
        # Profile info
        info_frame = tk.Frame(card, bg="#2a2a2a")
        info_frame.pack(side='left', fill='x', expand=True, padx=15, pady=10)
        
        tk.Label(info_frame,
                text=profile['name'],
                bg="#2a2a2a",
                fg="white",
                font=('Arial', 14, 'bold')).pack(anchor='w')
        
        tk.Label(info_frame,
                text=f"ID: {profile['id']}",
                bg="#2a2a2a",
                fg="#00ff00",
                font=('Courier', 10)).pack(anchor='w')
        
        tk.Label(info_frame,
                text=f"Proxy: {proxy_display}",
                bg="#2a2a2a",
                fg="#cccccc",
                font=('Arial', 10)).pack(anchor='w')
        
        # Actions
        actions_frame = tk.Frame(card, bg="#2a2a2a")
        actions_frame.pack(side='right', padx=15)
        
        tk.Button(actions_frame,
                 text="▶ Launch",
                 bg="#00ff00",
                 fg="black",
                 font=('Arial', 10, 'bold'),
                 bd=0,
                 padx=15,
                 pady=5,
                 command=lambda: self.launch_profile(profile)).pack(side='left', padx=5)
        
        tk.Button(actions_frame,
                 text="Copy CMD",
                 bg="#0099ff",
                 fg="white",
                 font=('Arial', 10),
                 bd=0,
                 padx=15,
                 pady=5,
                 command=lambda: self.copy_command(profile)).pack(side='left', padx=5)
        
        tk.Button(actions_frame,
                 text="Delete",
                 bg="#ff4444",
                 fg="white",
                 font=('Arial', 10),
                 bd=0,
                 padx=15,
                 pady=5,
                 command=lambda: self.delete_profile(profile['id'])).pack(side='left', padx=5)
    
    def launch_profile(self, profile):
        """Launch Chrome with profile"""
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            messagebox.showerror("Error", "Chrome not found!")
            return
        
        # Create profile directory
        profile_dir = os.path.join(os.getcwd(), "chrome_data", profile['id'])
        os.makedirs(profile_dir, exist_ok=True)
        
        # Parse proxy
        proxy_parts = profile['proxy'].split(':')
        proxy_server = f"{proxy_parts[0]}:{proxy_parts[1]}"
        
        # Build command
        cmd = [
            chrome_path,
            f"--user-data-dir={profile_dir}",
            f"--proxy-server={proxy_server}",
            "--start-maximized"
        ]
        
        # Create auth extension if credentials provided
        if len(proxy_parts) > 2:
            username = proxy_parts[2]
            password = proxy_parts[3] if len(proxy_parts) > 3 else ""
            
            # Create extension for this session
            ext_dir = self.create_simple_auth_extension(
                proxy_parts[0], 
                proxy_parts[1], 
                username, 
                password
            )
            if ext_dir:
                cmd.append(f"--load-extension={ext_dir}")
                
                # Show first-time instructions
                if not os.path.exists(os.path.join(profile_dir, "Default")):
                    messagebox.showinfo(
                        "First Time Setup",
                        "This is the first time launching this profile.\n\n"
                        "1. Chrome will open\n"
                        "2. If asked for proxy credentials, enter them\n"
                        "3. Check 'Save password' in Chrome\n"
                        "4. Future launches will use saved credentials"
                    )
        
        # Launch Chrome
        def launch():
            subprocess.Popen(cmd)
        
        threading.Thread(target=launch, daemon=True).start()
    
    def create_simple_auth_extension(self, host, port, username, password):
        """Create a minimal auth extension"""
        try:
            # Create temp directory
            ext_dir = os.path.join(tempfile.gettempdir(), f"proxy_ext_{uuid.uuid4().hex[:8]}")
            os.makedirs(ext_dir, exist_ok=True)
            
            # Manifest
            manifest = {
                "manifest_version": 2,
                "name": "Proxy Auth",
                "version": "1.0",
                "permissions": [
                    "proxy",
                    "webRequest",
                    "webRequestBlocking",
                    "<all_urls>"
                ],
                "background": {
                    "scripts": ["background.js"],
                    "persistent": True
                }
            }
            
            with open(os.path.join(ext_dir, "manifest.json"), 'w') as f:
                json.dump(manifest, f)
            
            # Background script
            background = f"""
// Set proxy
var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{host}",
            port: {port}
        }}
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

// Handle auth
chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        return {{
            authCredentials: {{
                username: "{username}",
                password: "{password}"
            }}
        }};
    }},
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""
            
            with open(os.path.join(ext_dir, "background.js"), 'w') as f:
                f.write(background)
            
            return ext_dir
            
        except Exception as e:
            print(f"Extension creation error: {e}")
            return None
    
    def copy_command(self, profile):
        """Copy launch command to clipboard"""
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            return
        
        profile_dir = os.path.join(os.getcwd(), "chrome_data", profile['id'])
        proxy_parts = profile['proxy'].split(':')
        proxy_server = f"{proxy_parts[0]}:{proxy_parts[1]}"
        
        cmd = f'"{chrome_path}" --user-data-dir="{profile_dir}" --proxy-server={proxy_server}'
        
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("Copied", "Command copied to clipboard!")
    
    def delete_profile(self, profile_id):
        """Delete a profile"""
        if messagebox.askyesno("Delete", "Delete this profile?"):
            self.profiles = [p for p in self.profiles if p['id'] != profile_id]
            self.save_profiles()
            
            # Optionally delete profile data
            profile_dir = os.path.join(os.getcwd(), "chrome_data", profile_id)
            if os.path.exists(profile_dir):
                try:
                    shutil.rmtree(profile_dir)
                except:
                    pass
            
            self.refresh_display()
    
    def get_chrome_path(self):
        """Get Chrome executable path"""
        system = platform.system()
        paths = self.chrome_paths.get(system, [])
        
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def load_profiles(self):
        """Load profiles from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_profiles(self):
        """Save profiles to file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.profiles, f, indent=2)
    
    def run(self):
        self.root.mainloop()


class ProfileDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Profile")
        self.dialog.geometry("500x400")
        self.dialog.configure(bg="#2a2a2a")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title
        tk.Label(self.dialog,
                text="Add New Profile",
                font=('Arial', 18, 'bold'),
                bg="#2a2a2a",
                fg="#00ff00").pack(pady=20)
        
        # Form
        form = tk.Frame(self.dialog, bg="#2a2a2a")
        form.pack(pady=20)
        
        # Name
        tk.Label(form, text="Profile Name:", bg="#2a2a2a", fg="white").grid(row=0, column=0, sticky='e', padx=10, pady=10)
        self.name_entry = tk.Entry(form, width=30)
        self.name_entry.grid(row=0, column=1, pady=10)
        
        # Proxy format help
        tk.Label(form, 
                text="Proxy Format:", 
                bg="#2a2a2a", 
                fg="white").grid(row=1, column=0, sticky='e', padx=10, pady=10)
        tk.Label(form, 
                text="host:port:username:password\nExample: 38.154.227.167:5868:user:pass", 
                bg="#2a2a2a", 
                fg="#cccccc",
                justify='left').grid(row=1, column=1, sticky='w', pady=10)
        
        # Proxy
        tk.Label(form, text="Proxy:", bg="#2a2a2a", fg="white").grid(row=2, column=0, sticky='e', padx=10, pady=10)
        self.proxy_entry = tk.Entry(form, width=30)
        self.proxy_entry.grid(row=2, column=1, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#2a2a2a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame,
                 text="Add",
                 bg="#00ff00",
                 fg="black",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.add).pack(side='left', padx=10)
        
        tk.Button(btn_frame,
                 text="Cancel",
                 bg="#666666",
                 fg="white",
                 font=('Arial', 12),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.dialog.destroy).pack(side='left', padx=10)
    
    def add(self):
        name = self.name_entry.get().strip()
        proxy = self.proxy_entry.get().strip()
        
        if not name or not proxy:
            messagebox.showwarning("Warning", "Please fill all fields")
            return
        
        # Validate proxy format
        parts = proxy.split(':')
        if len(parts) < 2:
            messagebox.showwarning("Warning", "Invalid proxy format. Use: host:port[:username:password]")
            return
        
        self.result = {
            'name': name,
            'proxy': proxy
        }
        self.dialog.destroy()


class BatchImportDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Import")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg="#2a2a2a")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Title
        tk.Label(self.dialog,
                text="Batch Import Proxies",
                font=('Arial', 18, 'bold'),
                bg="#2a2a2a",
                fg="#00ff00").pack(pady=20)
        
        # Instructions
        tk.Label(self.dialog,
                text="Enter proxies (one per line):\nFormat: host:port:username:password",
                bg="#2a2a2a",
                fg="#cccccc").pack()
        
        # Base name
        name_frame = tk.Frame(self.dialog, bg="#2a2a2a")
        name_frame.pack(pady=10)
        
        tk.Label(name_frame, text="Base Name:", bg="#2a2a2a", fg="white").pack(side='left', padx=5)
        self.base_name = tk.Entry(name_frame, width=20)
        self.base_name.insert(0, "Proxy")
        self.base_name.pack(side='left')
        
        # Text area
        self.text = tk.Text(self.dialog, width=60, height=15, bg="#1a1a1a", fg="white")
        self.text.pack(pady=10)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg="#2a2a2a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame,
                 text="Import",
                 bg="#00ff00",
                 fg="black",
                 font=('Arial', 12, 'bold'),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.import_proxies).pack(side='left', padx=10)
        
        tk.Button(btn_frame,
                 text="Cancel",
                 bg="#666666",
                 fg="white",
                 font=('Arial', 12),
                 bd=0,
                 padx=30,
                 pady=10,
                 command=self.dialog.destroy).pack(side='left', padx=10)
    
    def import_proxies(self):
        content = self.text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Warning", "Please enter proxies")
            return
        
        proxies = [line.strip() for line in content.split('\n') if line.strip()]
        
        self.result = {
            'base_name': self.base_name.get() or "Proxy",
            'proxies': proxies
        }
        self.dialog.destroy()


# API for developers
class ProxyAPI:
    def __init__(self, data_file="proxy_profiles.json"):
        self.data_file = data_file
    
    def get_profile(self, profile_id):
        """Get profile by ID"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                profiles = json.load(f)
                return next((p for p in profiles if p['id'] == profile_id), None)
        return None
    
    def launch_profile(self, profile_id):
        """Launch Chrome with profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        
        chrome_path = self._find_chrome()
        if not chrome_path:
            return False
        
        profile_dir = os.path.join(os.getcwd(), "chrome_data", profile_id)
        os.makedirs(profile_dir, exist_ok=True)
        
        proxy_parts = profile['proxy'].split(':')
        proxy_server = f"{proxy_parts[0]}:{proxy_parts[1]}"
        
        cmd = [
            chrome_path,
            f"--user-data-dir={profile_dir}",
            f"--proxy-server={proxy_server}"
        ]
        
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
    print("Chrome Proxy Manager - Working Version")
    print("=====================================")
    print("This version uses a simpler approach that works reliably.")
    print("For authenticated proxies, Chrome will ask for credentials")
    print("the first time - just save them in Chrome.\n")
    
    app = SimpleProxyManager()
    app.run()