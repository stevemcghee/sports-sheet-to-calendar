#!/usr/bin/env python3
"""
Automated Calendar Sync Script

This script runs the calendar sync process and sends email notifications
with detailed reports about what changed.
"""

import os
import sys
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import pickle

# Import our sync functions
from calendar_sync import (
    get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, update_calendar, get_existing_events,
    events_are_equal, list_available_sheets, get_event_key
)
from gemini_parser import parse_sheet_with_gemini

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SyncReporter:
    """Handles generating reports and sending email notifications."""
    
    def __init__(self):
        self.sync_results = {
            'timestamp': datetime.now().isoformat(),
            'sheets_processed': 0,
            'total_events_processed': 0,
            'total_events_created': 0,
            'total_events_updated': 0,
            'total_events_deleted': 0,
            'errors': [],
            'parsing_errors': [],
            'sheet_details': {},
            'summary': {}
        }
    
    def add_sheet_result(self, sheet_name, result):
        """Add results for a specific sheet."""
        self.sync_results['sheet_details'][sheet_name] = result
        self.sync_results['sheets_processed'] += 1
        
        if result.get('success'):
            self.sync_results['total_events_created'] += result.get('events_created', 0)
            self.sync_results['total_events_updated'] += result.get('events_updated', 0)
            self.sync_results['total_events_deleted'] += result.get('events_deleted', 0)
            self.sync_results['total_events_processed'] += result.get('total_events', 0)
        else:
            self.sync_results['errors'].append({
                'sheet': sheet_name,
                'error': result.get('error', 'Unknown error')
            })
    
    def add_parsing_error(self, sheet_name, error_message, row_data=None):
        """Add a parsing error for a specific sheet."""
        self.sync_results['parsing_errors'].append({
            'sheet': sheet_name,
            'error': error_message,
            'row_data': row_data
        })
    
    def generate_summary(self):
        """Generate a summary of the sync operation."""
        total_changes = (
            self.sync_results['total_events_created'] +
            self.sync_results['total_events_updated'] +
            self.sync_results['total_events_deleted']
        )
        
        self.sync_results['summary'] = {
            'total_changes': total_changes,
            'has_changes': total_changes > 0,
            'has_errors': len(self.sync_results['errors']) > 0,
            'success_rate': (
                (self.sync_results['sheets_processed'] - len(self.sync_results['errors'])) /
                max(self.sync_results['sheets_processed'], 1) * 100
            )
        }
        
        return self.sync_results['summary']
    
    def generate_email_content(self):
        """Generate HTML email content with detailed report."""
        summary = self.sync_results['summary']
        
        # Determine subject line
        if summary['has_errors']:
            subject = f"⚠️ Calendar Sync Report - {summary['total_changes']} changes, {len(self.sync_results['errors'])} errors"
        elif summary['has_changes']:
            subject = f"✅ Calendar Sync Report - {summary['total_changes']} changes"
        else:
            subject = f"📊 Calendar Sync Report - No changes detected"
        
        # Generate HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 15px; }}
                .header {{ background-color: #f0f0f0; padding: 12px; border-radius: 5px; margin-bottom: 15px; }}
                .summary {{ background-color: #e8f5e8; padding: 12px; border-radius: 5px; margin-bottom: 15px; }}
                .error {{ background-color: #ffe8e8; padding: 10px; border-radius: 5px; margin: 8px 0; }}
                .sheet-detail {{ background-color: #f8f8f8; padding: 8px; margin: 8px 0; border-radius: 3px; }}
                .stats {{ display: flex; justify-content: space-between; margin: 12px 0; gap: 8px; }}
                .stat {{ text-align: center; padding: 8px; background-color: #f0f0f0; border-radius: 5px; flex: 1; }}
                .stat h3 {{ margin: 0 0 4px 0; }}
                .stat p {{ margin: 0; }}
                .success {{ color: green; }}
                .error-text {{ color: red; }}
                .warning {{ color: orange; }}
                h1 {{ margin: 0 0 8px 0; }}
                h2 {{ margin: 0 0 8px 0; }}
                h3 {{ margin: 0 0 4px 0; }}
                p {{ margin: 4px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📅 Calendar Sync Report</h1>
                <p><strong>Timestamp:</strong> {datetime.fromisoformat(self.sync_results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Summary</h2>
                <div class="stats">
                    <div class="stat">
                        <h3>{self.sync_results['sheets_processed']}</h3>
                        <p>Sheets Processed</p>
                    </div>
                    <div class="stat">
                        <h3>{self.sync_results['total_events_processed']}</h3>
                        <p>Events Processed</p>
                    </div>
                    <div class="stat">
                        <h3 class="success">{self.sync_results['total_events_created']}</h3>
                        <p>Events Created</p>
                    </div>
                    <div class="stat">
                        <h3 class="warning">{self.sync_results['total_events_updated']}</h3>
                        <p>Events Updated</p>
                    </div>
                    <div class="stat">
                        <h3 class="error-text">{self.sync_results['total_events_deleted']}</h3>
                        <p>Events Deleted</p>
                    </div>
                </div>
                
                <p><strong>Success Rate:</strong> {summary['success_rate']:.1f}%</p>
                <p><strong>Total Changes:</strong> {summary['total_changes']}</p>
            </div>
        """
        
        # Add parsing errors section
        if self.sync_results['parsing_errors']:
            html_content += "<h2>⚠️ Parsing Errors</h2>"
            html_content += "<p><em>These errors occurred while parsing spreadsheet data but didn't prevent the sync from completing:</em></p>"
            for error in self.sync_results['parsing_errors']:
                html_content += f"""
                <div class="error">
                    <p><strong>Sheet:</strong> {error['sheet']}</p>
                    <p><strong>Error:</strong> {error['error']}</p>
                    """
                if error.get('row_data'):
                    html_content += f"<p><strong>Row Data:</strong> {error['row_data']}</p>"
                html_content += "</div>"
        
        # Add sheet details
        if self.sync_results['sheet_details']:
            html_content += "<h2>📋 Sheet Details</h2>"
            for sheet_name, result in self.sync_results['sheet_details'].items():
                status = "✅ Success" if result.get('success') else "❌ Error"
                html_content += f"""
                <div class="sheet-detail">
                    <h3>{sheet_name} - {status}</h3>
                """
                
                if result.get('success'):
                    html_content += f"""
                    <p><strong>Events Created:</strong> {result.get('events_created', 0)}</p>
                    <p><strong>Events Updated:</strong> {result.get('events_updated', 0)}</p>
                    <p><strong>Events Deleted:</strong> {result.get('events_deleted', 0)}</p>
                    <p><strong>Total Events:</strong> {result.get('total_events', 0)}</p>
                    """
                else:
                    html_content += f"""
                    <p class="error"><strong>Error:</strong> {result.get('error', 'Unknown error')}</p>
                    """
                
                html_content += "</div>"
        
        # Add errors section
        if self.sync_results['errors']:
            html_content += "<h2>❌ Errors</h2>"
            for error in self.sync_results['errors']:
                html_content += f"""
                <div class="error">
                    <p><strong>Sheet:</strong> {error['sheet']}</p>
                    <p><strong>Error:</strong> {error['error']}</p>
                </div>
                """
        
        html_content += """
        </body>
        </html>
        """
        
        return subject, html_content

def get_google_credentials():
    """Get Google credentials from token.pickle file or service account."""
    creds = None
    
    # First try to load from token.pickle (for OAuth2)
    if os.path.exists('token.pickle'):
        try:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
            logger.info("Loaded credentials from token.pickle")
        except Exception as e:
            logger.error(f"Error loading token.pickle: {e}")
            creds = None
    
    # If OAuth2 credentials are valid, use them
    if creds and creds.valid:
        return creds
    elif creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the refreshed credentials
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Refreshed and saved credentials")
            return creds
        except RefreshError as e:
            logger.error(f"Failed to refresh credentials: {e}")
    
    # Fallback to default service account (Cloud Run service identity)
    try:
        from google.auth import default
        logger.info("Attempting to use default service account credentials")
        
        creds, project = default(scopes=['https://www.googleapis.com/auth/spreadsheets.readonly',
                                        'https://www.googleapis.com/auth/calendar'])
        logger.info(f"Loaded default service account credentials for project: {project}")
        return creds
    except Exception as e:
        logger.error(f"Error loading default service account credentials: {e}")
        return None

def sync_single_sheet(service, sheets_service, spreadsheet_id, sheet_name, use_gemini=True, reporter=None):
    """Sync a single sheet and return results."""
    try:
        logger.info(f"Processing sheet: {sheet_name}")
        
        # Get sheet data
        values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        if not values:
            return {
                'success': False,
                'error': 'No data found in sheet',
                'events_created': 0,
                'events_updated': 0,
                'events_deleted': 0,
                'total_events': 0
            }
        
        # Set up a custom log handler to capture parsing errors from any logger
        parsing_errors = []
        
        class ParsingErrorHandler(logging.Handler):
            def emit(self, record):
                if record.levelno == logging.ERROR and 'Error parsing row' in record.getMessage():
                    parsing_errors.append(record.getMessage())
        
        # Add the handler to the root logger to catch all parsing errors
        error_handler = ParsingErrorHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(error_handler)
        
        try:
            # Parse events
            if use_gemini:
                try:
                    events = parse_sheet_with_gemini(values)
                    if not events:
                        logger.warning(f"Gemini parser returned no events for {sheet_name}, falling back to traditional parser")
                        events = parse_sports_events(values, sheet_name)
                except Exception as e:
                    logger.error(f"Error using Gemini parser for {sheet_name}: {e}")
                    events = parse_sports_events(values, sheet_name)
            else:
                events = parse_sports_events(values, sheet_name)
        finally:
            # Remove the custom handler
            root_logger.removeHandler(error_handler)
        
        # Add parsing errors to reporter if available
        if reporter and parsing_errors:
            logger.info(f"Captured {len(parsing_errors)} parsing errors for sheet {sheet_name}")
            for error_msg in parsing_errors:
                reporter.add_parsing_error(sheet_name, error_msg)
        elif parsing_errors:
            logger.info(f"Parsing errors captured but no reporter available: {parsing_errors}")
        
        if not events:
            return {
                'success': True,
                'events_created': 0,
                'events_updated': 0,
                'events_deleted': 0,
                'total_events': 0,
                'message': 'No events found in sheet'
            }
        
        # Create or get calendar
        calendar_name = f"SLOHS {sheet_name}"
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        
        # Update calendar
        deleted, inserted, changed = update_calendar(service, events, calendar_id)
        
        logger.info(f"Sheet {sheet_name}: {inserted} created, {changed} updated, {deleted} deleted")
        
        return {
            'success': True,
            'events_created': inserted,
            'events_updated': changed,
            'events_deleted': deleted,
            'total_events': len(events)
        }
        
    except Exception as e:
        logger.error(f"Error processing sheet {sheet_name}: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'events_created': 0,
            'events_updated': 0,
            'events_deleted': 0,
            'total_events': 0
        }

def send_email_notification(subject, html_content, to_email=None):
    """Send email notification with the sync report."""
    # Get email configuration from environment
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL', smtp_username)
    
    if not all([smtp_server, smtp_username, smtp_password]):
        logger.warning("Email configuration incomplete. Skipping email notification.")
        return False
    
    if not to_email:
        to_email = os.getenv('TO_EMAIL')
        if not to_email:
            logger.warning("No recipient email specified. Skipping email notification.")
            return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Create HTML part
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Email notification sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False

def main():
    """Main function to run the automated sync."""
    logger.info("Starting automated calendar sync")
    
    # Get configuration
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        logger.error("SPREADSHEET_ID not found in environment variables")
        return False
    
    # Force use_gemini to False for faster processing
    use_gemini = False
    send_email = os.getenv('SEND_EMAIL', 'true').lower() == 'true'
    to_email = os.getenv('TO_EMAIL')
    
    # Get Google credentials
    creds = get_google_credentials()
    if not creds:
        logger.error("Failed to get Google credentials")
        return False
    
    # Build services
    try:
        service = build('calendar', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        logger.info("Successfully built Google services")
    except Exception as e:
        logger.error(f"Failed to build Google services: {e}")
        return False
    
    # Initialize reporter
    reporter = SyncReporter()
    
    # Get all available sheets
    try:
        available_sheets = list_available_sheets(sheets_service, spreadsheet_id)
        logger.info(f"Found {len(available_sheets)} sheets: {available_sheets}")
    except Exception as e:
        logger.error(f"Failed to get available sheets: {e}")
        return False
    
    # Process each sheet
    for sheet_name in available_sheets:
        result = sync_single_sheet(service, sheets_service, spreadsheet_id, sheet_name, use_gemini, reporter)
        reporter.add_sheet_result(sheet_name, result)
    
    # Generate summary
    summary = reporter.generate_summary()
    logger.info(f"Sync completed. Summary: {summary}")
    
    # Send email notification if configured
    if send_email and (summary['has_changes'] or summary['has_errors'] or summary['total_changes'] == 0):
        subject, html_content = reporter.generate_email_content()
        send_email_notification(subject, html_content, to_email)
    
    # Save report to file
    report_file = f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(reporter.sync_results, f, indent=2)
    logger.info(f"Report saved to {report_file}")
    
    return summary['success_rate'] > 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 