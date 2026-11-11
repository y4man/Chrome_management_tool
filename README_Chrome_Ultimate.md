# Chrome Proxy Manager Ultimate

A robust enterprise-grade tool for managing Chrome profiles with proxy authentication and Gmail integration.

## Features

### Core Features
- **Automated Proxy Authentication**: Handles proxy credentials automatically via Chrome extension
- **Gmail Validation**: Tests Gmail accounts before using them in profiles
- **Batch Profile Setup**: Set up hundreds of profiles automatically
- **Smart Email Management**: Separates good and bad Gmail accounts
- **Complete Automation**: One-click setup for proxy auth + Gmail login
- **SQLite Database**: Efficient storage for managing 1000+ profiles

### Key Improvements
- Proxy authentication that actually works (via Chrome extension)
- Gmail validation before profile setup
- Robust error handling
- Clean, modular architecture
- Progress tracking for all operations
- Profile status management

## Installation

### Requirements
```bash
# Required
pip install selenium

# Optional but recommended
pip install undetected-chromedriver
```

### Chrome Driver
Download ChromeDriver from: https://chromedriver.chromium.org/
Make sure it matches your Chrome version.

## Usage

### 1. Run the Application
```bash
python chromax_ultimate.py
```

### 2. Import Profiles

Click **"📁 Import Batch"** and use this format:

```
ProfileName:ProxyHost:ProxyPort:ProxyUser:ProxyPass:Gmail:GmailPassword
```

Example:
```
Work_Profile_1:proxy1.example.com:8080:user1:pass1:work1@gmail.com:gmail_pass1
Work_Profile_2:proxy2.example.com:3128:user2:pass2:work2@gmail.com:gmail_pass2
Personal_1:proxy3.example.com:8888:user3:pass3:personal@gmail.com:gmail_pass3
```

### 3. Validate Emails (Recommended)

Click **"✓ Validate Emails"** to test all Gmail accounts:
- Good emails will be shown in green
- Bad emails (wrong password, 2FA, etc.) will be shown in red
- Only good emails will be used for profile setup

### 4. Setup All Profiles

Click **"🚀 Setup All Profiles"** to:
1. Create Chrome profile directories
2. Install proxy authentication extension
3. Test proxy connection
4. Login to Gmail automatically
5. Save cookies for future use

### 5. Launch Profiles

Select a profile and click **"▶ Launch Profile"** to open Chrome with:
- Proxy already authenticated
- Gmail already logged in
- All cookies restored

## Import File Format

### Full Format (7 fields):
```
ProfileName:ProxyHost:Port:ProxyUsername:ProxyPassword:Email:EmailPassword
```

### Without Profile Name (6 fields):
```
ProxyHost:Port:ProxyUsername:ProxyPassword:Email:EmailPassword
```

### Proxy Only (4 fields):
```
ProxyHost:Port:ProxyUsername:ProxyPassword
```

### Simple Proxy (2 fields):
```
ProxyHost:Port
```

## Database Schema

The tool uses SQLite with two main tables:

### profiles
- id, name, proxy details, email credentials
- status (pending, ready, failed, etc.)
- proxy_authenticated, email_logged_in flags

### validated_emails
- Stores email validation results
- Prevents using bad emails in profiles

## Status Meanings

- **pending**: New profile, not set up
- **ready**: Fully set up and ready to use
- **proxy_failed**: Proxy authentication failed
- **email_failed**: Gmail login failed
- **email_invalid**: Email marked as bad during validation

## Tips

### For Gmail Success:
1. Use app-specific passwords (not regular passwords)
2. Disable 2FA temporarily during setup
3. Use fresh Gmail accounts or ones without security restrictions
4. Allow "less secure apps" if needed

### For Proxy Success:
1. Ensure proxies are working before import
2. Use HTTP/HTTPS proxies (SOCKS support varies)
3. Check proxy credentials are correct

### Performance:
- The tool can handle 1000+ profiles
- Setup is done sequentially to avoid detection
- Each profile takes 10-15 seconds to fully setup

## Troubleshooting

### Proxy Authentication Fails
- Check proxy credentials
- Ensure proxy supports HTTP/HTTPS
- Try the proxy in a regular browser first

### Gmail Login Fails
- Run email validation first
- Check for 2FA (not supported)
- Use app-specific passwords
- Check account isn't locked

### Chrome Not Found
- Install Google Chrome (not Chromium)
- Check installation path in code

## API Usage (Advanced)

You can use the profiles programmatically:

```python
from chromax_ultimate import ChromeProfileManager

manager = ChromeProfileManager()
profile = {
    'id': 'test_001',
    'profile_dir': '/path/to/profile',
    'proxy_host': 'proxy.example.com',
    'proxy_port': 8080
}

manager.launch_profile(profile)
```

## Security Notes

- Passwords are stored in local SQLite database (not encrypted)
- Use on secure, personal computers only
- Profile data is stored in `chrome_profiles_data/`
- Proxy extensions are stored in `proxy_extensions/`

## File Structure

```
/home/yaman/projects/
├── chromax_ultimate.py          # Main application
├── proxy_profiles_ultimate.db   # SQLite database
├── chrome_profiles_data/        # Chrome profile directories
│   ├── profile_xxxxx/
│   └── ...
└── proxy_extensions/            # Proxy auth extensions
    ├── ext_profile_xxxxx/
    └── ...
```

## License

For educational and personal use only. Respect the terms of service of websites you access.