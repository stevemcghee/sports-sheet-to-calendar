#!/bin/bash

echo "🚀 Deploying Google Calendar Sync App..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
fi

# Check if remote exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "❌ No remote repository found!"
    echo "Please create a GitHub repository and add it as origin:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    exit 1
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git add .
git commit -m "Update for deployment"
git push origin main

echo "✅ Code pushed to GitHub!"
echo ""
echo "🌐 To deploy on Render:"
echo "1. Go to https://render.com"
echo "2. Sign up/Login with GitHub"
echo "3. Click 'New Web Service'"
echo "4. Connect your GitHub repository"
echo "5. Set build command: pip install -r requirements.txt"
echo "6. Set start command: gunicorn app:app"
echo "7. Click 'Create Web Service'"
echo ""
echo "🔧 Environment Variables to set in Render:"
echo "- GOOGLE_CLIENT_ID: Your Google OAuth client ID"
echo "- GOOGLE_CLIENT_SECRET: Your Google OAuth client secret"
echo "- FLASK_SECRET_KEY: A random secret key for Flask"
echo ""
echo "🎉 Your app will be live at: https://your-app-name.onrender.com" 