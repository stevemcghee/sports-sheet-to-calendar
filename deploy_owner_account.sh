#!/bin/bash

# Deployment script for sloswimtiming@gmail.com to access its own calendars
# This is the simplest approach - the app owner is the calendar owner

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Setting up deployment for sloswimtiming@gmail.com..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud SDK is not installed!"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warning "You are not authenticated with Google Cloud!"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Get current user
CURRENT_USER=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
print_status "Current authenticated user: $CURRENT_USER"

# Check if user is sloswimtiming@gmail.com
if [[ "$CURRENT_USER" != "sloswimtiming@gmail.com" ]]; then
    print_warning "You are not authenticated as sloswimtiming@gmail.com!"
    echo "Please run: gcloud auth login"
    echo "Then authenticate as sloswimtiming@gmail.com"
    exit 1
fi

# Get project ID
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}

if [ -z "$PROJECT_ID" ]; then
    echo "Please enter your Google Cloud Project ID:"
    read PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required!"
    exit 1
fi

print_status "Using project: $PROJECT_ID"

# Set the project
gcloud config set project $PROJECT_ID

print_status "Setting up OAuth2 credentials for sloswimtiming@gmail.com..."

echo ""
print_warning "IMPORTANT: Manual steps required for OAuth2 setup:"
echo ""
echo "1. Create OAuth2 credentials in Google Cloud Console:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials"
echo "   - Click 'Create Credentials' → 'OAuth 2.0 Client ID'"
echo "   - Application type: 'Web application'"
echo "   - Add authorized redirect URIs:"
echo "     - http://localhost:5000/auth/callback"
echo "     - https://your-cloud-run-url/auth/callback (after deployment)"
echo "   - Add test user: sloswimtiming@gmail.com"
echo ""
echo "2. Enable required APIs:"
echo "   - Go to: https://console.cloud.google.com/apis/library"
echo "   - Enable: Google Calendar API, Google Sheets API"
echo ""

read -p "Press Enter when OAuth2 credentials are configured..."

# Build and deploy to Cloud Run
print_status "Building and deploying to Cloud Run..."

# Get the current timestamp for versioning (use valid format for Cloud Run tags)
TIMESTAMP=$(date +%Y%m%d-%H%M%S | tr -d ' ')
SERVICE_NAME="calendar-sync"
REGION="us-central1"

# Build and deploy
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="FLASK_ENV=production" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10 \
    --port 5000

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

print_success "Deployment completed successfully!"
print_status "Service URL: $SERVICE_URL"

# Set up Cloud Scheduler for automated sync
print_status "Setting up Cloud Scheduler for nightly sync at 3 AM..."

# Create the scheduler job
gcloud scheduler jobs create http calendar-sync-job \
    --schedule="0 3 * * *" \
    --uri="$SERVICE_URL/trigger-sync" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --location=$REGION \
    --description="Nightly calendar sync job at 3 AM" \
    --time-zone="America/Los_Angeles" \
    --attempt-deadline=300s

print_success "Cloud Scheduler job created!"

# Display next steps
echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Enable required APIs in Google Cloud Console:"
echo "   - Go to: https://console.cloud.google.com/apis/library"
echo "   - Enable: Cloud Build, Cloud Run, Cloud Scheduler, Google Sheets, Google Calendar"
echo ""
echo "2. Set environment variables in Cloud Run console:"
echo "   - Go to: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo "   - Click 'Edit & Deploy New Revision'"
echo "   - Add your environment variables:"
echo "     - SPREADSHEET_ID"
echo "     - GEMINI_API_KEY"
echo "     - FLASK_SECRET_KEY"
echo "     - SEND_EMAIL=true"
echo "     - SMTP_SERVER=smtp.gmail.com"
echo "     - SMTP_PORT=587"
echo "     - SMTP_USERNAME=sloswimtiming@gmail.com"
echo "     - SMTP_PASSWORD=your-app-password"
echo "     - TO_EMAIL=sloswimtiming@gmail.com"
echo ""
echo "3. Test the deployment:"
echo "   - Web interface: $SERVICE_URL"
echo "   - Click 'Authenticate with Google'"
echo "   - Sign in as sloswimtiming@gmail.com"
echo "   - Grant permissions to access your own calendars"
echo ""
echo "4. Monitor the scheduler:"
echo "   - Console: https://console.cloud.google.com/cloudscheduler"
echo "   - Logs: gcloud scheduler jobs logs calendar-sync-job"
echo ""
echo "5. Set up monitoring:"
echo "   - Cloud Logging: https://console.cloud.google.com/run/logs"
echo "   - Cloud Monitoring: https://console.cloud.google.com/monitoring"
echo ""
print_status "Your calendar sync app is now running on Google Cloud Run!" 