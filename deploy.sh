#!/bin/bash

# Exit on error
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if project ID is provided or available in environment
if [ -z "$1" ]; then
    if [ -z "$PROJECT_ID" ]; then
        echo "Usage: ./deploy.sh <PROJECT_ID> or set PROJECT_ID in .env"
        exit 1
    fi
    PROJECT_ID=$PROJECT_ID
else
    PROJECT_ID=$1
fi

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    --project=$PROJECT_ID

# Set up environment variables
echo "Setting up environment variables..."
gcloud secrets create calendar-credentials --project=$PROJECT_ID --data-file=credentials.json

# Deploy using Cloud Build
echo "Deploying to Cloud Run..."
gcloud builds submit \
    --project=$PROJECT_ID \
    --config=cloudbuild.yaml \
    --substitutions=_SPREADSHEET_ID="$SPREADSHEET_ID",_CALENDAR_NAME="$CALENDAR_NAME",_PROJECT_ID=$PROJECT_ID,_REGION="$REGION",_TIMEZONE="$TIMEZONE"

# Create Cloud Scheduler job
echo "Setting up Cloud Scheduler job..."
gcloud scheduler jobs create http calendar-sync-job \
    --project=$PROJECT_ID \
    --schedule="0 0 * * *" \
    --time-zone="$TIMEZONE" \
    --uri="https://calendar-sync-$PROJECT_ID.run.app" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --body="{}"

echo "Deployment complete!"
echo "The calendar sync will run daily at midnight $TIMEZONE time." 