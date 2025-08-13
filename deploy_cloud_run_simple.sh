#!/bin/bash

# Simplified Google Cloud Run Deployment Script
# This script deploys the calendar sync app to Google Cloud Run

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

# Get project ID from argument or prompt
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

print_warning "Note: You may need to manually enable APIs in the Google Cloud Console:"
echo "   - Cloud Build API"
echo "   - Cloud Run API"
echo "   - Cloud Scheduler API"
echo "   - Google Sheets API"
echo "   - Google Calendar API"
echo ""

# Build and deploy to Cloud Run
print_status "Building and deploying to Cloud Run..."

# Get the current timestamp for versioning
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
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
    --port 5000 \
    --tag $TIMESTAMP

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

# Create a service account for the scheduler
print_status "Creating service account for scheduler..."
gcloud iam service-accounts create calendar-sync-scheduler \
    --display-name="Calendar Sync Scheduler" \
    --description="Service account for calendar sync scheduler"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:calendar-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

print_success "Service account configured!"

# Update scheduler to use service account
gcloud scheduler jobs update http calendar-sync-job \
    --oidc-service-account-email="calendar-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --location=$REGION

print_success "Scheduler updated with service account!"

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
echo "     - FLASK_SECRET_KEY"
echo "     - SMTP_* (for email notifications)"
echo ""
echo "3. Test the deployment:"
echo "   - Web interface: $SERVICE_URL"
echo "   - Manual sync: $SERVICE_URL/trigger-sync"
echo ""
echo "4. Monitor the scheduler:"
echo "   - Console: https://console.cloud.google.com/cloudscheduler"
echo "   - Logs: gcloud scheduler jobs logs calendar-sync-job"
echo ""
echo "5. Set up monitoring:"
echo "   - Cloud Logging: https://console.cloud.google.com/logs"
echo "   - Cloud Monitoring: https://console.cloud.google.com/monitoring"
echo ""
print_status "Your calendar sync app is now running on Google Cloud Run!" 