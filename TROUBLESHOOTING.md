# Troubleshooting Guide

This guide covers common issues and their solutions for the Google Calendar Sync application.

## Port Issues

### Port 5000 Already in Use (macOS)

**Problem**: You see "Address already in use" when starting the application.

**Solution**:
1. **Option 1**: Disable AirPlay Receiver
   - Go to System Preferences > General > AirDrop & Handoff
   - Turn off "AirPlay Receiver"

2. **Option 2**: Use a different port
   ```bash
   python app.py --port 5001
   ```

3. **Option 3**: Find and stop the process using port 5000
   ```bash
   lsof -ti:5000 | xargs kill -9
   ```

### Port Already in Use (Other Systems)

**Solution**:
```bash
# Find what's using the port
netstat -tulpn | grep :5000

# Kill the process
kill -9 <PID>

# Or use a different port
python app.py --port 5001
```

## Authentication Issues

### OAuth Credentials Not Working

**Symptoms**:
- "Invalid credentials" error
- Redirect loops
- Authentication fails

**Solutions**:

1. **Check OAuth Configuration**:
   - Verify redirect URIs include both localhost and production domain
   - Ensure credentials.json is in the project root
   - Check that environment variables are set correctly

2. **Clear Browser Data**:
   - Clear cookies for localhost and your domain
   - Try incognito/private browsing mode

3. **Regenerate Credentials**:
   - Delete `token.pickle` file
   - Create new OAuth credentials in Google Cloud Console
   - Update environment variables

### Environment Variables Not Loading

**Symptoms**:
- App redirects to `/setup`
- "No credentials found" error

**Solutions**:

1. **Check Environment Variables**:
   ```bash
   echo $GOOGLE_CLIENT_ID
   echo $GOOGLE_CLIENT_SECRET
   echo $FLASK_SECRET_KEY
   ```

2. **Set Variables Correctly**:
   ```bash
   export GOOGLE_CLIENT_ID=your_client_id
   export GOOGLE_CLIENT_SECRET=your_client_secret
   export FLASK_SECRET_KEY=your_secret_key
   ```

3. **Create .env File** (for local development):
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   FLASK_SECRET_KEY=your_secret_key
   GEMINI_API_KEY=your_gemini_key
   ```

## Parser Issues

### Gemini AI Parser Fails

**Symptoms**:
- "Gemini API error" messages
- Events not parsed correctly
- Empty results

**Solutions**:

1. **Check API Key**:
   ```bash
   echo $GEMINI_API_KEY
   ```

2. **Verify API Key**:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Check if your key is valid
   - Create a new key if needed

3. **Try Traditional Parser**:
   - Switch to traditional parser in the web interface
   - Check if your spreadsheet format matches requirements

### Traditional Parser Fails

**Symptoms**:
- "Invalid date format" errors
- Missing events
- Incorrect event times

**Solutions**:

1. **Check Spreadsheet Format**:
   - Ensure first row contains sport name
   - Verify second row has headers
   - Check required columns are present

2. **Validate Date Formats**:
   - Use MM/DD or MM/DD/YYYY format
   - Avoid ambiguous formats like "week of"
   - Check for extra spaces or characters

3. **Review Error Logs**:
   - Check `app.log` for specific error messages
   - Look for parsing failures in the web interface

## API Rate Limits

### Google API Quota Exceeded

**Symptoms**:
- "Quota exceeded" errors
- Slow response times
- Failed API calls

**Solutions**:

1. **Check Current Usage**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services > Quotas
   - Check current usage vs limits

2. **Implement Rate Limiting**:
   - Add delays between API calls
   - Process smaller batches
   - Use exponential backoff

3. **Request Quota Increase**:
   - Go to Google Cloud Console
   - Request quota increase for Calendar and Sheets APIs

## Deployment Issues

### Render Deployment Fails

**Symptoms**:
- Build fails
- App doesn't start
- Environment variables not found

**Solutions**:

1. **Check Build Logs**:
   - Review Render build logs
   - Verify requirements.txt is correct
   - Check Python version compatibility

2. **Verify Environment Variables**:
   - Ensure all required variables are set
   - Check variable names match exactly
   - Verify no extra spaces or quotes

3. **Test Locally First**:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

### Google Cloud Deployment Issues

**Symptoms**:
- Cloud Build fails
- Cloud Run deployment errors
- Scheduler job not working

**Solutions**:

1. **Check Permissions**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Enable Required APIs**:
   ```bash
   gcloud services enable calendar-json.googleapis.com
   gcloud services enable sheets.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

3. **Verify Service Account**:
   - Check if service account has necessary permissions
   - Grant additional roles if needed

## Performance Issues

### Slow Processing

**Symptoms**:
- Long loading times
- Timeout errors
- Unresponsive interface

**Solutions**:

1. **Optimize Spreadsheet Size**:
   - Process smaller sheets individually
   - Remove unnecessary data
   - Use efficient date formats

2. **Check Network Connection**:
   - Verify internet connectivity
   - Check for firewall issues
   - Test with smaller datasets

3. **Monitor Resource Usage**:
   - Check CPU and memory usage
   - Monitor API call frequency
   - Implement caching if needed

## Log Files

### Understanding Logs

**Main Log Files**:
- `app.log`: Web application logs
- `calendar_sync.log`: Command-line sync logs
- `out.log`: General output logs

**Common Log Levels**:
- `DEBUG`: Detailed debugging information
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Debugging Steps

1. **Enable Debug Logging**:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check Specific Logs**:
   ```bash
   tail -f app.log
   tail -f calendar_sync.log
   ```

3. **Search for Errors**:
   ```bash
   grep -i error app.log
   grep -i exception app.log
   ```

## Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Review the main README.md**
3. **Check application logs**
4. **Test with a simple spreadsheet**
5. **Verify all setup steps are completed**

### Useful Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Test Google APIs
python -c "from googleapiclient.discovery import build; print('APIs working')"

# Check environment variables
env | grep GOOGLE
env | grep FLASK

# Test Flask app
python app.py --debug
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Address already in use" | Port 5000 occupied | Use different port or disable AirPlay |
| "Invalid credentials" | OAuth setup issue | Check credentials and environment variables |
| "API quota exceeded" | Rate limit reached | Wait or request quota increase |
| "No module named" | Missing dependency | Run `pip install -r requirements.txt` |
| "Permission denied" | File permissions | Check file ownership and permissions | 