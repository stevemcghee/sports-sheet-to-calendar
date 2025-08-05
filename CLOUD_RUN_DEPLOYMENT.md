# Google Cloud Run Deployment Guide

This guide shows you how to deploy your calendar sync application to Google Cloud Run alongside your existing Render deployment.

## 🚀 Quick Deployment

### Option 1: Automated Deployment (Recommended)

```bash
# Make sure you have gcloud CLI installed and authenticated
./deploy_cloud_run.sh YOUR_PROJECT_ID
```

### Option 2: Manual Deployment

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com cloudscheduler.googleapis.com

# 3. Deploy to Cloud Run
gcloud run deploy calendar-sync \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 10

# 4. Set up Cloud Scheduler
gcloud scheduler jobs create http calendar-sync-job \
  --schedule="0 * * * *" \
  --uri="YOUR_SERVICE_URL/trigger-sync" \
  --http-method=POST \
  --location=us-central1
```

## 📋 Prerequisites

### 1. Google Cloud SDK
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login
gcloud auth application-default login
```

### 2. Google Cloud Project
- Create a new project or use existing one
- Enable billing
- Note your Project ID

### 3. Required APIs
The deployment script will automatically enable:
- Cloud Build API
- Cloud Run API
- Cloud Scheduler API
- Google Sheets API
- Google Calendar API

## 🔧 Environment Configuration

### Set Environment Variables in Cloud Run Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your `calendar-sync` service
3. Click "Edit & Deploy New Revision"
4. Add these environment variables:

#### Required Variables
```bash
SPREADSHEET_ID=your-spreadsheet-id
GEMINI_API_KEY=your-gemini-api-key
FLASK_SECRET_KEY=your-secret-key
```

#### Email Configuration (Optional)
```bash
SEND_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com
```

#### Sync Configuration (Optional)
```bash
USE_GEMINI=true
LOG_LEVEL=INFO
TIMEZONE=America/Los_Angeles
```

## 🌐 Service URLs

After deployment, you'll have:

- **Web Interface**: `https://calendar-sync-XXXXX-uc.a.run.app`
- **Manual Sync**: `https://calendar-sync-XXXXX-uc.a.run.app/trigger-sync`
- **Health Check**: `https://calendar-sync-XXXXX-uc.a.run.app/`

## ⏰ Automated Scheduling

The deployment creates a Cloud Scheduler job that:

- **Runs every hour** at minute 0
- **Calls the sync endpoint** automatically
- **Sends notifications** when changes are detected
- **Handles errors gracefully** with retries

### Monitor the Scheduler

```bash
# View scheduler jobs
gcloud scheduler jobs list

# Check scheduler logs
gcloud scheduler jobs logs calendar-sync-job

# Test the scheduler manually
gcloud scheduler jobs run calendar-sync-job
```

## 📊 Monitoring & Logging

### Cloud Logging
```bash
# View application logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=calendar-sync" --limit=50

# View scheduler logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit=50
```

### Cloud Monitoring
- Set up alerts for errors
- Monitor request latency
- Track sync success rates

## 🔄 Continuous Deployment

### Option 1: Cloud Build Triggers

1. Connect your GitHub repository
2. Create a Cloud Build trigger
3. Set trigger on push to main branch
4. Use the provided `cloudbuild.yaml`

### Option 2: Manual Deployment

```bash
# Deploy new version
gcloud run deploy calendar-sync --source . --region us-central1

# Update scheduler if needed
gcloud scheduler jobs update http calendar-sync-job --uri="NEW_SERVICE_URL/trigger-sync"
```

## 🆚 Comparison: Render vs Cloud Run

| Feature | Render | Cloud Run |
|---------|--------|-----------|
| **Deployment** | Git-based | Container-based |
| **Scaling** | Automatic | Automatic |
| **Cost** | Free tier | Pay per use |
| **Scheduling** | External | Built-in Cloud Scheduler |
| **Monitoring** | Basic | Advanced (Cloud Logging/Monitoring) |
| **Custom Domain** | Yes | Yes |
| **SSL** | Automatic | Automatic |

## 🔧 Troubleshooting

### Common Issues

1. **"Permission denied"**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **"Service not found"**
   ```bash
   gcloud run services list --region=us-central1
   ```

3. **"Scheduler not working"**
   ```bash
   gcloud scheduler jobs describe calendar-sync-job --location=us-central1
   ```

4. **"Environment variables not set"**
   - Go to Cloud Run console
   - Edit service and add variables
   - Redeploy

### Debug Commands

```bash
# Check service status
gcloud run services describe calendar-sync --region=us-central1

# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=calendar-sync" --limit=10

# Test the service
curl https://calendar-sync-XXXXX-uc.a.run.app/

# Test the sync endpoint
curl -X POST https://calendar-sync-XXXXX-uc.a.run.app/trigger-sync
```

## 💰 Cost Optimization

### Free Tier
- Cloud Run: 2 million requests/month
- Cloud Scheduler: 3 jobs/month
- Cloud Logging: 50 GB/month

### Cost Monitoring
```bash
# View current costs
gcloud billing accounts list
gcloud billing projects describe YOUR_PROJECT_ID
```

## 🔐 Security Best Practices

1. **Use service accounts** for scheduler authentication
2. **Set up IAM roles** properly
3. **Use Secret Manager** for sensitive data
4. **Enable audit logging**
5. **Regular security updates**

## 📈 Performance Optimization

### Cloud Run Configuration
- **Memory**: 1Gi (sufficient for most workloads)
- **CPU**: 1 (can scale to 4 for heavy processing)
- **Concurrency**: 80 (good for web requests)
- **Timeout**: 300s (enough for sync operations)

### Monitoring Metrics
- Request latency
- Error rates
- Memory usage
- CPU utilization
- Sync success rate

## 🎯 Next Steps

1. **Deploy to Cloud Run**: `./deploy_cloud_run.sh`
2. **Configure environment variables** in Cloud Run console
3. **Test the deployment**: Visit your service URL
4. **Monitor the scheduler**: Check Cloud Scheduler console
5. **Set up alerts**: Configure Cloud Monitoring
6. **Set up custom domain** (optional)

Your calendar sync app will now run on both Render (for web interface) and Cloud Run (for automated sync with advanced monitoring)! 