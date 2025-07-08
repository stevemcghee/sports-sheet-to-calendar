#!/usr/bin/env python3
"""
Script to check Gemini API quota and usage.
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def check_gemini_quota():
    """Check Gemini API quota and usage."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return
    
    print(f"🔑 Using API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    try:
        # Try to make a simple API call to test quota
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
        response = model.generate_content("Hello, this is a quota test.")
        
        if response and response.text:
            print("✅ API call successful - quota available")
            print(f"Response: {response.text}")
        else:
            print("⚠️ API call returned empty response")
            
    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        
        # Check if it's a quota error
        if "429" in str(e) or "quota" in str(e).lower():
            print("\n🔍 This appears to be a quota/rate limit issue.")
            print("💡 Solutions:")
            print("   1. Wait for quota reset (usually hourly/daily)")
            print("   2. Check your billing status at https://console.cloud.google.com/")
            print("   3. Upgrade your plan if needed")
            print("   4. Consider using a different API key")

def check_google_cloud_quota():
    """Check quota via Google Cloud API (requires additional setup)."""
    print("\n📊 To check detailed quota information:")
    print("   1. Go to https://console.cloud.google.com/")
    print("   2. Navigate to APIs & Services > Quotas")
    print("   3. Search for 'Generative Language API'")
    print("   4. Or visit: https://makersuite.google.com/app/apikey")

if __name__ == "__main__":
    print("🔍 Checking Gemini API Quota...")
    print("=" * 50)
    
    check_gemini_quota()
    check_google_cloud_quota()
    
    print("\n" + "=" * 50)
    print("💡 Additional Resources:")
    print("   - Gemini API Docs: https://ai.google.dev/docs/")
    print("   - Rate Limits: https://ai.google.dev/gemini-api/docs/rate-limits")
    print("   - Billing: https://console.cloud.google.com/billing") 