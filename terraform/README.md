# Calendar Sync Terraform Configuration

This Terraform configuration deploys the calendar sync application to Google Cloud Run with Cloud Scheduler for automated execution.

## Prerequisites

1. **Terraform** installed (version >= 1.0)
2. **Google Cloud SDK** installed and authenticated
3. **Docker** installed (for building the container image)

## Configuration

### 1. Set up variables

Copy the example variables file and fill in the sensitive values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and provide the following sensitive values:
- `smtp_password` - Your Gmail app password
- `flask_secret_key` - A secure random string for Flask sessions
- `google_client_secret` - Your Google OAuth client secret

### 2. Build and push the Docker image

Before running Terraform, you need to build and push the Docker image:

```bash
# From the project root directory
gcloud builds submit --tag us-central1-docker.pkg.dev/stevemcghee-slosports/cloud-run-source-deploy/calendar-sync
```

## Deployment

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Plan the deployment

```bash
terraform plan
```

### 3. Apply the configuration

```bash
terraform apply
```

## What gets created

- **Google Cloud APIs** enabled (Cloud Run, Cloud Scheduler, Cloud Build, Calendar API, Sheets API)
- **Cloud Run service** with the calendar sync application
- **Cloud Scheduler job** that runs nightly at 3 AM
- **IAM permissions** for Cloud Scheduler to invoke Cloud Run

## Configuration Details

### Cloud Run Service
- **Name**: `calendar-sync`
- **Region**: `us-central1`
- **Memory**: 1GB
- **CPU**: 1000m
- **Timeout**: 1 hour (3600 seconds)
- **Max instances**: 10

### Cloud Scheduler Job
- **Name**: `calendar-sync-job`
- **Schedule**: `0 3 * * *` (3 AM daily)
- **Timezone**: America/Los_Angeles
- **Target**: HTTP POST to `/trigger-sync` endpoint

### Environment Variables
All environment variables are configured in the Terraform configuration, including:
- SMTP settings for email notifications
- Google OAuth credentials
- Spreadsheet ID
- Flask secret key

## Updating the deployment

To update the deployment with new code:

1. Build and push a new Docker image
2. Run `terraform apply` to update the Cloud Run service

## Destroying the deployment

To remove all resources:

```bash
terraform destroy
```

**Warning**: This will delete the Cloud Run service and Cloud Scheduler job.

## Troubleshooting

### Common Issues

1. **Image not found**: Make sure you've built and pushed the Docker image before running Terraform
2. **Permission errors**: Ensure your Google Cloud account has the necessary permissions
3. **API not enabled**: The Terraform configuration automatically enables required APIs

### Manual verification

After deployment, you can verify the setup:

```bash
# Check Cloud Run service
gcloud run services describe calendar-sync --region=us-central1

# Check Cloud Scheduler job
gcloud scheduler jobs describe calendar-sync-job --location=us-central1

# Test the sync manually
curl -X POST https://calendar-sync-927659207918.us-central1.run.app/trigger-sync
```

## Security Notes

- Sensitive values (passwords, API keys) are marked as `sensitive` in Terraform
- The Cloud Run service allows unauthenticated access for the web interface
- Cloud Scheduler has specific IAM permissions to invoke the service
- All environment variables are encrypted at rest in Cloud Run 