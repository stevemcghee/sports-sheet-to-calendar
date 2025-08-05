#!/usr/bin/env python3
"""
Environment Check Script

This script checks your current environment configuration and provides
recommendations for missing or incorrect settings.
"""

import os
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists and load it."""
    if os.path.exists('.env'):
        load_dotenv()
        return True
    else:
        print("❌ .env file not found!")
        print("   Run: python setup_env.py")
        return False

def check_required_vars():
    """Check required environment variables."""
    required_vars = {
        'SPREADSHEET_ID': 'Your Google Spreadsheet ID',
        'GEMINI_API_KEY': 'Your Gemini API key',
        'FLASK_SECRET_KEY': 'Flask secret key for web sessions'
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
        else:
            print(f"✅ {var}")
    
    if missing:
        print("\n❌ Missing required variables:")
        for var in missing:
            print(f"   - {var}")
        return False
    
    return True

def check_email_config():
    """Check email notification configuration."""
    email_vars = {
        'SMTP_SERVER': 'SMTP server (e.g., smtp.gmail.com)',
        'SMTP_USERNAME': 'Email username',
        'SMTP_PASSWORD': 'Email app password',
        'TO_EMAIL': 'Recipient email address'
    }
    
    print("\n📧 Email Configuration:")
    configured = True
    
    for var, description in email_vars.items():
        if os.getenv(var):
            print(f"✅ {var}")
        else:
            print(f"⚠️  {var} ({description})")
            configured = False
    
    if not configured:
        print("\n💡 Email notifications are optional but recommended for monitoring")
        print("   Run: python setup_env.py to configure email settings")
    
    return configured

def check_optional_vars():
    """Check optional environment variables."""
    optional_vars = {
        'USE_GEMINI': 'Use Gemini AI parser (default: true)',
        'SEND_EMAIL': 'Enable email notifications (default: true)',
        'LOG_LEVEL': 'Logging level (default: INFO)',
        'TIMEZONE': 'Timezone (default: America/Los_Angeles)'
    }
    
    print("\n⚙️  Optional Configuration:")
    for var, description in optional_vars.items():
        value = os.getenv(var, 'Not set (using default)')
        print(f"   {var}: {value}")

def main():
    """Main function."""
    print("🔍 Environment Configuration Check")
    print("=" * 40)
    
    # Check if .env file exists
    if not check_env_file():
        return
    
    print("\n📋 Required Variables:")
    
    # Check required variables
    required_ok = check_required_vars()
    
    # Check email configuration
    email_ok = check_email_config()
    
    # Check optional variables
    check_optional_vars()
    
    print("\n" + "=" * 40)
    
    if required_ok:
        print("✅ All required variables are configured!")
        print("\n🚀 You can now:")
        print("   - Run: python setup_automation.py")
        print("   - Test: python automated_sync.py")
        print("   - Monitor: python monitor_changes.py")
    else:
        print("❌ Some required variables are missing!")
        print("\n🔧 To fix this:")
        print("   - Run: python setup_env.py")
        print("   - Or edit .env file manually")
    
    if not email_ok:
        print("\n📧 Email notifications are not configured")
        print("   This is optional but recommended for monitoring")

if __name__ == '__main__':
    main() 