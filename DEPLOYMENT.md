# Deployment Guide

This guide covers all deployment options for the Google Calendar Sync application.

## Deployment Options Overview

| Platform | Use Case | Complexity | Cost |
|----------|----------|------------|------|
| **Render** | Web interface, easy setup | Low | Free tier available |
| **Google Cloud Platform** | Automated scheduling, enterprise | Medium | Pay per use |
| **Local Development** | Testing, development | Low | Free |
| **Docker** | Containerized deployment | Medium | Varies |

## Option 1: Render (Recommended for Web Interface)

### Prerequisites
- GitHub account
- Google Cloud project with OAuth credentials
- Optional: Gemini API key for AI parsing

### Step-by-Step Deployment

1. **Push to GitHub**:
   ```bash
   ./deploy.sh
   ```

2. **Create Render Account**:
   - Go to [Render](https://render.com)
   - Sign up with GitHub
   - Verify your email

3. **Create Web Service**:
   - Click "New" > "Web Service"
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn app:app`
   - Choose your plan (Free tier available)

4. **Configure Environment Variables**:
   - Go to your service dashboard
   - Click "Environment" tab
   - Add required variables (see `render_env_setup.md`)

5. **Deploy**:
   - Click "Create Web Service"
   - Wait for build to complete
   - Your app will be live at `https://your-app-name.onrender.com`

### Render Configuration

**Build Settings**:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Python Version: 3.9.16 (specified in render.yaml)

**Environment Variables** (see `render_env_setup.md` for details):
```
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_PROJECT_ID=your_google_cloud_project_id
FLASK_SECRET_KEY=your_generated_secret_key
GEMINI_API_KEY=your_gemini_api_key  # Optional
SPREADSHEET_ID=your_default_spreadsheet_id  # Optional
```

## Option 2: Google Cloud Platform (Automated)

### Prerequisites
- Google Cloud SDK installed
- Active Google Cloud project
- Billing enabled

### Automated Deployment

1. **Install and Authenticate**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Run Deployment Script**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh YOUR_PROJECT_ID
   ```

3. **Verify Deployment**:
   - Check Cloud Run service is running
   - Verify Cloud Scheduler job is created
   - Test the web interface

### Manual GCP Deployment

1. **Enable APIs**:
   ```bash
   gcloud services enable calendar-json.googleapis.com
   gcloud services enable sheets.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable cloudscheduler.googleapis.com
   ```

2. **Build and Deploy**:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/calendar-sync
   gcloud run deploy calendar-sync \
     --image gcr.io/YOUR_PROJECT_ID/calendar-sync \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. **Set up Cloud Scheduler**:
   ```bash
   gcloud scheduler jobs create http calendar-sync-job \
     --schedule="0 0 * * *" \
     --uri="https://your-service-url/run-sync" \
     --http-method=POST
   ```

## Option 3: Docker Deployment

### Local Docker

1. **Build Image**:
   ```bash
   docker build -t calendar-sync .
   ```

2. **Run Container**:
   ```bash
   docker run -p 5000:5000 \
     -e GOOGLE_CLIENT_ID=your_client_id \
     -e GOOGLE_CLIENT_SECRET=your_client_secret \
     -e FLASK_SECRET_KEY=your_secret_key \
     calendar-sync
   ```

### Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  calendar-sync:
    build: .
    ports:
      - "5000:5000"
    environment:
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

### Cloud Run with Docker

1. **Build and Push**:
   ```bash
   docker build -t gcr.io/YOUR_PROJECT_ID/calendar-sync .
   docker push gcr.io/YOUR_PROJECT_ID/calendar-sync
   ```

2. **Deploy**:
   ```bash
   gcloud run deploy calendar-sync \
     --image gcr.io/YOUR_PROJECT_ID/calendar-sync \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

## Option 4: Local Development

### Prerequisites
- Python 3.9+
- Virtual environment
- Google OAuth credentials

### Setup

1. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd google_calendar_sync
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Credentials**:
   - Create `credentials.json` with OAuth credentials
   - Or set environment variables

3. **Run Application**:
   ```bash
   # Web interface
   python app.py
   
   # Command line sync
   python calendar_sync.py
   ```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | OAuth client ID | `123456789-abcdef.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | `GOCSPX-abcdefghijklmnop` |
| `FLASK_SECRET_KEY` | Flask session key | `a1b2c3d4e5f6...` |

### Optional Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Gemini AI API key | `AIzaSyC...` |
| `SPREADSHEET_ID` | Default spreadsheet | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `GOOGLE_PROJECT_ID` | GCP project ID | `my-calendar-sync-project` |

### Environment File (.env)

For local development, create a `.env` file:
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
FLASK_SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_key
SPREADSHEET_ID=your_spreadsheet_id
```

## Security Considerations

### OAuth Configuration
- Use environment variables for all secrets
- Never commit credentials to version control
- Rotate keys regularly
- Use least privilege principle

### Network Security
- Use HTTPS in production
- Configure CORS properly
- Implement rate limiting
- Monitor API usage

### Data Protection
- Encrypt sensitive data
- Use secure session management
- Implement proper logging
- Regular security audits

## Monitoring and Maintenance

### Health Checks
- Application health: `GET /health`
- API connectivity: Check Google API status
- Database connectivity: Verify OAuth tokens

### Logging
- Application logs: `app.log`
- Sync logs: `calendar_sync.log`
- Error logs: Check application dashboard

### Performance Monitoring
- API response times
- Memory usage
- CPU utilization
- Error rates

## Troubleshooting Deployment

### Common Issues

**Build Failures**:
- Check Python version compatibility
- Verify all dependencies in requirements.txt
- Review build logs for specific errors

**Runtime Errors**:
- Check environment variables are set correctly
- Verify OAuth credentials are valid
- Review application logs

**Authentication Issues**:
- Ensure redirect URIs match deployment URL
- Check OAuth consent screen configuration
- Verify API scopes are enabled

### Debug Commands

```bash
# Check application status
curl -f http://localhost:5000/health

# Test Google APIs
python -c "from googleapiclient.discovery import build; print('APIs working')"

# Check environment variables
env | grep GOOGLE
env | grep FLASK

# View logs
tail -f app.log
```

## Cost Optimization

### Render
- Use free tier for development
- Upgrade only when needed
- Monitor usage patterns

### Google Cloud Platform
- Use Cloud Run for serverless deployment
- Implement proper resource limits
- Monitor billing and quotas

### General
- Optimize API calls
- Implement caching where possible
- Use efficient data structures

## Support and Resources

### Documentation
- Main README: `README.md`
- Render setup: `render_env_setup.md`
- Troubleshooting: `TROUBLESHOOTING.md`

### Community
- GitHub Issues for bug reports
- Stack Overflow for questions
- Google Cloud support for GCP issues

### Monitoring Tools
- Render dashboard for web service metrics
- Google Cloud Console for GCP monitoring
- Application logs for debugging 