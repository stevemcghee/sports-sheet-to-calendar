#!/bin/bash

# Google Cloud Run Deployment Script
# This script deploys the calendar sync app to Google Cloud Run.
# It can be used for both initial deployment and redeployment.

set -e  # Exit on any error

# --- Configuration ---
DEFAULT_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
DEFAULT_REGION="us-central1"
DEFAULT_SERVICE_NAME="calendar-sync"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Functions ---
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

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --project <project_id>   Google Cloud project ID (default: current gcloud config)"
    echo "  -r, --region <region>        Google Cloud region (default: $DEFAULT_REGION)"
    echo "  -n, --name <service_name>    Cloud Run service name (default: $DEFAULT_SERVICE_NAME)"
    echo "  --redeploy                   Redeploy the service without setting up scheduler and service accounts"
    echo "  --simple                     Skip automatic API enablement"
    echo "  -h, --help                   Display this help message"
}

# --- Parse arguments ---
REDEPLOY=false
SIMPLE=false
PROJECT_ID=$DEFAULT_PROJECT_ID
REGION=$DEFAULT_REGION
SERVICE_NAME=$DEFAULT_SERVICE_NAME

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -p|--project) PROJECT_ID="$2"; shift ;;
        -r|--region) REGION="$2"; shift ;;
        -n|--name) SERVICE_NAME="$2"; shift ;;
        --redeploy) REDEPLOY=true ;;
        --simple) SIMPLE=true ;;
        -h|--help) usage; exit 0 ;;
        *) print_error "Unknown parameter passed: $1"; usage; exit 1 ;;
    esac
    shift
done

# --- Pre-flight checks ---
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud SDK is not installed!"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warning "You are not authenticated with Google Cloud!"
    echo "Please run: gcloud auth login"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Please enter your Google Cloud Project ID:"
    read PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required!"
    exit 1
fi

print_status "Using project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# --- Main logic ---
if [ "$REDEPLOY" = true ]; then
    print_status "Redeploying service with unique image tag..."
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:$TIMESTAMP"

    print_status "Building and pushing image: $IMAGE_NAME"
    gcloud builds submit --tag "$IMAGE_NAME" --project="$PROJECT_ID"
    if [ $? -ne 0 ]; then
        print_error "Docker image build failed."
        exit 1
    fi

    print_status "Updating cloud_run.yaml with new image tag..."
    # Use sed to replace the image tag. The | separator is used to avoid issues with slashes in the image name.
    # This works on both GNU and macOS sed.
    sed -i.bak "s|image: gcr.io/$PROJECT_ID/$SERVICE_NAME:.*|image: $IMAGE_NAME|" cloud_run.yaml

    print_status "Deploying updated service configuration..."
    gcloud run services replace cloud_run.yaml --region="$REGION" --project="$PROJECT_ID"
    if [ $? -ne 0 ]; then
        print_error "Service deployment failed."
        exit 1
    fi
    print_success "Service redeployed successfully."
    exit 0
fi

# --- Initial Deployment ---
if [ "$SIMPLE" = false ]; then
    print_status "Enabling required APIs..."
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        cloudscheduler.googleapis.com \
        sheets.googleapis.com \
        calendar.googleapis.com \
        --quiet
    print_success "APIs enabled successfully!"
else
    print_warning "Skipping API enablement. Please ensure APIs are enabled manually."
fi

print_status "Building and deploying to Cloud Run..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
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

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
print_success "Deployment completed successfully!"
print_status "Service URL: $SERVICE_URL"

print_status "Setting up Cloud Scheduler for hourly sync..."
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

print_status "Creating service account for scheduler..."
gcloud iam service-accounts create calendar-sync-scheduler \
    --display-name="Calendar Sync Scheduler" \
    --description="Service account for calendar sync scheduler"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:calendar-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
print_success "Service account configured!"

gcloud scheduler jobs update http calendar-sync-job \
    --oidc-service-account-email="calendar-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --location=$REGION
print_success "Scheduler updated with service account!"

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Cloud Run console:"
echo "   - Go to: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo "   - Click 'Edit & Deploy New Revision'"
echo "   - Add your environment variables:"
echo "     - SPREADSHEET_ID"
echo "     - FLASK_SECRET_KEY"
echo "     - SMTP_* (for email notifications)"
echo ""
echo "2. Test the deployment:"
echo "   - Web interface: $SERVICE_URL"
echo "   - Manual sync: $SERVICE_URL/trigger-sync"
echo ""
echo "3. Monitor the scheduler:"
echo "   - Console: https://console.cloud.google.com/cloudscheduler"
echo "   - Logs: gcloud scheduler jobs logs calendar-sync-job"
echo ""
echo "4. Set up monitoring:"
echo "   - Cloud Logging: https://console.cloud.google.com/logs"
echo "   - Cloud Monitoring: https://console.cloud.google.com/monitoring"
echo ""
print_status "Your calendar sync app is now running on Google Cloud Run!"
