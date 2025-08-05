# Automated Calendar Sync System

This system automatically syncs your Google Spreadsheet data to Google Calendar every hour and sends detailed email notifications about what changed.

## 🚀 Quick Start

1. **Set up virtual environment:**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run the setup script:**
   ```bash
   python setup_automation.py
   ```

3. **Configure your environment:**
   - Run: `python setup_env.py` (interactive setup)
   - Or edit `.env` file with your settings
   - Set up email notifications (optional)

4. **Test the automation:**
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate  # On macOS/Linux
   # venv\Scripts\activate   # On Windows
   
   python automated_sync.py
   ```

5. **Deploy to Google Cloud Run:**
   ```bash
   gcloud run deploy calendar-sync --source . --platform managed --region us-central1 --allow-unauthenticated
   ```

6. **Set up hourly scheduling:**
   ```bash
   gcloud scheduler jobs create http calendar-sync-job --schedule='0 * * * *' --uri='YOUR_CLOUD_RUN_URL/trigger-sync' --http-method=POST
   ```

## 📧 Email Notifications

The system sends beautiful HTML emails with:

- **Summary statistics** (events created, updated, deleted)
- **Detailed breakdown** by sheet
- **Error reports** if issues occur
- **Success rates** and performance metrics

### Email Configuration

Add these to your `.env` file:

```bash
# Email Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com
SEND_EMAIL=true
```

### Gmail Setup

1. Enable 2-Factor Authentication
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this as `SMTP_PASSWORD`

## 📊 Monitoring & Analytics

### Change Monitoring

Track changes over time with the monitoring script:

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

python monitor_changes.py
```

This creates:
- **SQLite database** with sync history
- **Visual charts** showing trends
- **Detailed reports** with statistics
- **Performance analysis**

### Sample Report Output

```
==================================================
CALENDAR SYNC CHANGE REPORT
==================================================
Period: 7 days
Total Syncs: 168
Total Changes: 45
  - Created: 23
  - Updated: 18
  - Deleted: 4
Average Success Rate: 98.2%
Average Sync Interval: 1.0 hours

Most Active Sheets:
  - Football: 12 events created
  - Basketball: 8 events created
  - Soccer: 3 events created
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SPREADSHEET_ID` | Yes | Your Google Spreadsheet ID |
| `GEMINI_API_KEY` | Yes | Your Gemini API key |
| `SEND_EMAIL` | No | Enable email notifications (true/false) |
| `USE_GEMINI` | No | Use Gemini parser (true/false) |
| `SMTP_*` | No | Email server configuration |
| `TO_EMAIL` | No | Email recipient |

### Sync Behavior

- **Runs every hour** via Cloud Scheduler
- **Processes all sheets** in your spreadsheet
- **Creates separate calendars** for each sheet
- **Sends emails only when changes occur** (or errors)
- **Falls back to traditional parser** if Gemini fails

## 📁 File Structure

```
google_calendar_sync/
├── automated_sync.py          # Main automation script
├── monitor_changes.py         # Change monitoring & analytics
├── setup_automation.py        # Setup and configuration helper
├── scheduler.yaml             # Cloud Scheduler configuration
├── email_config.md           # Email setup guide
├── AUTOMATION_README.md      # This file
├── sync_history.db           # SQLite database (created automatically)
├── charts/                   # Generated charts (created automatically)
└── sync_report_*.json       # Individual sync reports
```

## 🛠️ Troubleshooting

### Common Issues

1. **"No valid credentials found"**
   - Make sure virtual environment is activated: `source venv/bin/activate`
   - Run the web app first: `python app.py`
   - Authenticate with Google
   - The `token.pickle` file will be created

2. **"ModuleNotFoundError"**
   - Activate virtual environment: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`
   - Verify installation: `pip list | grep python-dotenv`

3. **Email not sending**
   - Check SMTP settings in `.env`
   - Verify Gmail app password
   - Test with: `python automated_sync.py`

4. **Scheduler not running**
   - Check Cloud Scheduler job status
   - Verify Cloud Run URL is correct
   - Check logs: `gcloud scheduler jobs describe calendar-sync-job`

5. **Parser errors**
   - Set `USE_GEMINI=false` to use traditional parser
   - Check spreadsheet format
   - Review logs in `automated_sync.log`

### Debug Mode

Run with verbose logging:

```bash
python automated_sync.py 2>&1 | tee debug.log
```

## 📈 Advanced Features

### Custom Scheduling

Modify `scheduler.yaml` for different schedules:

```yaml
# Every 30 minutes
schedule: "*/30 * * * *"

# Every 2 hours
schedule: "0 */2 * * *"

# Weekdays only
schedule: "0 9-17 * * 1-5"
```

### Multiple Recipients

Add multiple email addresses:

```bash
TO_EMAIL=admin@school.com,coach@school.com,athletic@school.com
```

### Custom Email Templates

Modify the `SyncReporter.generate_email_content()` method in `automated_sync.py` to customize email formatting.

### Database Queries

Query the SQLite database directly:

```sql
-- Recent syncs
SELECT * FROM sync_history ORDER BY timestamp DESC LIMIT 10;

-- Sheet statistics
SELECT sheet_name, SUM(events_created) as total_created 
FROM sheet_details 
GROUP BY sheet_name 
ORDER BY total_created DESC;
```

## 🔒 Security Considerations

- **App passwords** are more secure than regular passwords
- **Environment variables** keep secrets out of code
- **Cloud Run** provides secure execution environment
- **HTTPS endpoints** for scheduler triggers
- **Token refresh** handles expired credentials automatically

## 📞 Support

For issues or questions:

1. Check the logs: `automated_sync.log`
2. Run the monitor: `python monitor_changes.py`
3. Test manually: `python automated_sync.py`
4. Review configuration: `python setup_automation.py`

## 🎯 Success Metrics

The system tracks:

- **Sync frequency** and reliability
- **Change volume** by sheet and time period
- **Error rates** and resolution times
- **Parser performance** (Gemini vs traditional)
- **Email delivery** success rates

Monitor these metrics to optimize your automation setup! 