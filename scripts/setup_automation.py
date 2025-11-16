#!/usr/bin/env python3
"""
Setup script for automated calendar sync

This script helps you configure and test the automated sync system.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """Check if all required environment variables are set."""
    load_dotenv()
    
    required_vars = [
        'SPREADSHEET_ID',
    ]
    
    optional_vars = [
        'SMTP_SERVER',
        'SMTP_USERNAME', 
        'SMTP_PASSWORD',
        'TO_EMAIL',
        'SEND_EMAIL',
    ]
    
    print("🔍 Checking environment configuration...")
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        print("   Run: python setup_env.py to configure environment")
        return False
    
    print("✅ All required environment variables are set")
    
    # Check optional email variables
    email_vars = [var for var in optional_vars if var.startswith('SMTP') or var == 'TO_EMAIL']
    email_configured = all(os.getenv(var) for var in email_vars)
    
    if email_configured:
        print("✅ Email notifications are configured")
    else:
        print("⚠️  Email notifications are not configured (optional)")
        print("   Run: python setup_env.py to configure email settings")
    
    return True

def check_google_auth():
    """Check if Google authentication is set up."""
    print("\n🔍 Checking Google authentication...")
    
    if os.path.exists('token.pickle'):
        print("✅ Google authentication token found")
        return True
    elif os.path.exists('credentials.json'):
        print("✅ Google credentials file found")
        print("⚠️  You need to authenticate via the web app first")
        return False
    else:
        print("❌ No Google authentication found")
        print("   Please run the web app and authenticate first")
        return False

def test_sync():
    """Test the sync functionality."""
    print("\n🧪 Testing sync functionality...")
    
    try:
        from automated_sync import main as test_sync
        print("Running test sync...")
        success = test_sync()
        
        if success:
            print("✅ Sync test completed successfully")
        else:
            print("❌ Sync test failed")
        
        return success
    except Exception as e:
        print(f"❌ Error during sync test: {e}")
        return False

def create_sample_env():
    """Create a sample .env file."""
    sample_env = """# Google Calendar Sync Configuration

# Required: Your Google Spreadsheet ID
SPREADSHEET_ID=your-spreadsheet-id-here

# Optional: Email notification settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com

# Sync configuration
SEND_EMAIL=true

# Flask secret key (for web app)
FLASK_SECRET_KEY=your-secret-key-here
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(sample_env)
        print("📝 Created sample .env file")
        print("   Please edit .env with your actual values")
    else:
        print("📝 .env file already exists")

def show_deployment_instructions():
    """Show deployment instructions."""
    print("\n🚀 DEPLOYMENT INSTRUCTIONS")
    print("="*50)
    
    print("\n1. **Set up environment variables:**")
    print("   - Run: python setup_env.py")
    print("   - Or edit .env file with your configuration")
    print("   - Or set environment variables in your deployment platform")
    
    print("\n2. **Deploy to Google Cloud Run:**")
    print("   gcloud run deploy calendar-sync \\")
    print("     --source . \\")
    print("     --platform managed \\")
    print("     --region us-central1 \\")
    print("     --allow-unauthenticated")
    
    print("\n3. **Set up Cloud Scheduler:**")
    print("   gcloud scheduler jobs create http calendar-sync-job \\")
    print("     --schedule='0 * * * *' \\")
    print("     --uri='YOUR_CLOUD_RUN_URL/trigger-sync' \\")
    print("     --http-method=POST \\")
    print("     --headers='Content-Type=application/json'")
    
    print("\n4. **Test the automation:**")
    print("   python automated_sync.py")
    
    print("\n5. **Monitor changes:**")
    print("   python monitor_changes.py")

def check_virtual_environment():
    """Check if virtual environment is activated."""
    print("🔍 Checking virtual environment...")
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is activated")
        return True
    else:
        print("⚠️  Virtual environment is not activated")
        print("   Please run: source venv/bin/activate")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = ['dotenv', 'flask', 'google', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("   Please run: pip install -r requirements.txt")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def main():
    """Main setup function."""
    print("🔧 Calendar Sync Automation Setup")
    print("="*40)
    
    # Check virtual environment
    venv_ok = check_virtual_environment()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check environment
    env_ok = check_environment()
    
    # Check Google auth
    auth_ok = check_google_auth()
    
    # Create sample .env if needed
    if not env_ok:
        create_sample_env()
        print("\n⚠️  Please configure your .env file and run this script again")
        return
    
    # Test sync if everything is configured
    if env_ok and auth_ok and venv_ok and deps_ok:
        print("\n🧪 Running sync test...")
        test_sync()
    
    # Show deployment instructions
    show_deployment_instructions()
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Configure your .env file with actual values")
    print("2. Deploy to Google Cloud Run")
    print("3. Set up Cloud Scheduler for hourly execution")
    print("4. Test the automation")

if __name__ == '__main__':
    main() 