#!/usr/bin/env python3
"""
Calendar Sync Change Monitor

This script monitors and analyzes changes over time, providing insights
into sync patterns and trends.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# Load environment variables
load_dotenv()

# Define project root (assuming script is in utils/ or project root)
PROJECT_ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == 'utils' else Path(__file__).resolve().parent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChangeMonitor:
    """Monitors and analyzes calendar sync changes over time."""
    
    def __init__(self, db_path=PROJECT_ROOT / 'sync_history.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database for storing sync history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create sync_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sheets_processed INTEGER,
                events_created INTEGER,
                events_updated INTEGER,
                events_deleted INTEGER,
                total_changes INTEGER,
                success_rate REAL,
                has_errors BOOLEAN,
                error_count INTEGER,
                sync_duration REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sheet_details table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sheet_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id INTEGER,
                sheet_name TEXT,
                events_created INTEGER,
                events_updated INTEGER,
                events_deleted INTEGER,
                total_events INTEGER,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (sync_id) REFERENCES sync_history (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def record_sync_result(self, sync_results):
        """Record a sync result in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert main sync record
            cursor.execute('''
                INSERT INTO sync_history (
                    timestamp, sheets_processed, events_created, events_updated,
                    events_deleted, total_changes, success_rate, has_errors,
                    error_count, sync_duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sync_results['timestamp'],
                sync_results['sheets_processed'],
                sync_results['total_events_created'],
                sync_results['total_events_updated'],
                sync_results['total_events_deleted'],
                sync_results['summary']['total_changes'],
                sync_results['summary']['success_rate'],
                sync_results['summary']['has_errors'],
                len(sync_results['errors']),
                sync_results.get('sync_duration', 0)
            ))
            
            sync_id = cursor.lastrowid
            
            # Insert sheet details
            for sheet_name, details in sync_results['sheet_details'].items():
                cursor.execute('''
                    INSERT INTO sheet_details (
                        sync_id, sheet_name, events_created, events_updated,
                        events_deleted, total_events, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sync_id,
                    sheet_name,
                    details.get('events_created', 0),
                    details.get('events_updated', 0),
                    details.get('events_deleted', 0),
                    details.get('total_events', 0),
                    details.get('success', False),
                    details.get('error', '')
                ))
            
            conn.commit()
            logger.info(f"Recorded sync result with ID: {sync_id}")
            return sync_id
            
        except Exception as e:
            logger.error(f"Error recording sync result: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_recent_syncs(self, hours=24):
        """Get sync results from the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT * FROM sync_history 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        ''', (cutoff_time,))
        
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_sheet_statistics(self, days=7):
        """Get statistics for each sheet over the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                sd.sheet_name,
                COUNT(*) as sync_count,
                SUM(sd.events_created) as total_created,
                SUM(sd.events_updated) as total_updated,
                SUM(sd.events_deleted) as total_deleted,
                AVG(sd.total_events) as avg_total_events,
                SUM(CASE WHEN sd.success THEN 1 ELSE 0 END) as success_count
            FROM sheet_details sd
            JOIN sync_history sh ON sd.sync_id = sh.id
            WHERE sh.timestamp > ?
            GROUP BY sd.sheet_name
            ORDER BY total_created DESC
        ''', (cutoff_time,))
        
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def generate_change_report(self, days=7):
        """Generate a comprehensive change report."""
        recent_syncs = self.get_recent_syncs(hours=days*24)
        sheet_stats = self.get_sheet_statistics(days)
        
        if not recent_syncs:
            return {
                'message': f'No sync data found for the last {days} days',
                'period': f'{days} days',
                'total_syncs': 0
            }
        
        # Calculate overall statistics
        total_syncs = len(recent_syncs)
        total_created = sum(s['events_created'] for s in recent_syncs)
        total_updated = sum(s['events_updated'] for s in recent_syncs)
        total_deleted = sum(s['events_deleted'] for s in recent_syncs)
        total_changes = sum(s['total_changes'] for s in recent_syncs)
        avg_success_rate = sum(s['success_rate'] for s in recent_syncs) / total_syncs
        
        # Find most active sheets
        active_sheets = sorted(sheet_stats, key=lambda x: x['total_created'], reverse=True)[:5]
        
        # Calculate sync frequency
        if len(recent_syncs) > 1:
            sync_times = [datetime.fromisoformat(s['timestamp']) for s in recent_syncs]
            sync_times.sort()
            avg_interval = sum((sync_times[i+1] - sync_times[i]).total_seconds() 
                             for i in range(len(sync_times)-1)) / (len(sync_times)-1) / 3600  # hours
        else:
            avg_interval = None
        
        return {
            'period': f'{days} days',
            'total_syncs': total_syncs,
            'total_created': total_created,
            'total_updated': total_updated,
            'total_deleted': total_deleted,
            'total_changes': total_changes,
            'avg_success_rate': round(avg_success_rate, 1),
            'avg_sync_interval_hours': round(avg_interval, 1) if avg_interval else None,
            'most_active_sheets': active_sheets,
            'recent_syncs': recent_syncs[:10],  # Last 10 syncs
            'sheet_statistics': sheet_stats
        }
    
    def create_charts(self, days=7, output_dir=PROJECT_ROOT / 'charts'):
        """Create visual charts of sync activity."""
        Path(output_dir).mkdir(exist_ok=True)
        
        # Get data
        recent_syncs = self.get_recent_syncs(hours=days*24)
        sheet_stats = self.get_sheet_statistics(days)
        
        if not recent_syncs:
            logger.warning("No data available for charts")
            return
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(recent_syncs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create charts
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Calendar Sync Activity - Last {days} Days', fontsize=16)
        
        # Chart 1: Changes over time
        axes[0, 0].plot(df['timestamp'], df['events_created'], label='Created', marker='o')
        axes[0, 0].plot(df['timestamp'], df['events_updated'], label='Updated', marker='s')
        axes[0, 0].plot(df['timestamp'], df['events_deleted'], label='Deleted', marker='^')
        axes[0, 0].set_title('Changes Over Time')
        axes[0, 0].set_ylabel('Number of Events')
        axes[0, 0].legend()
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Chart 2: Success rate over time
        axes[0, 1].plot(df['timestamp'], df['success_rate'], marker='o', color='green')
        axes[0, 1].set_title('Success Rate Over Time')
        axes[0, 1].set_ylabel('Success Rate (%)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Chart 3: Sheet activity (bar chart)
        if sheet_stats:
            sheet_names = [s['sheet_name'] for s in sheet_stats[:10]]
            total_created = [s['total_created'] for s in sheet_stats[:10]]
            
            axes[1, 0].barh(sheet_names, total_created)
            axes[1, 0].set_title('Most Active Sheets')
            axes[1, 0].set_xlabel('Total Events Created')
        
        # Chart 4: Sync frequency
        if len(df) > 1:
            intervals = df['timestamp'].diff().dt.total_seconds() / 3600  # hours
            axes[1, 1].hist(intervals.dropna(), bins=10, alpha=0.7)
            axes[1, 1].set_title('Sync Intervals Distribution')
            axes[1, 1].set_xlabel('Hours Between Syncs')
            axes[1, 1].set_ylabel('Frequency')
        
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f'sync_charts_{datetime.now().strftime("%Y%m%d")}.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Charts saved to: {chart_path}")
        return chart_path

def main():
    """Main function to run the monitor."""
    monitor = ChangeMonitor()
    
    # Check for recent sync report files
    report_files = sorted(PROJECT_ROOT.glob('sync_report_*.json'), reverse=True)
    
    if report_files:
        # Load the most recent report
        with open(report_files[0], 'r') as f:
            sync_results = json.load(f)
        
        # Record in database
        sync_id = monitor.record_sync_result(sync_results)
        if sync_id:
            logger.info(f"Recorded sync result with ID: {sync_id}")
    
    # Generate report
    report = monitor.generate_change_report(days=7)
    
    # Print report
    print("\n" + "="*50)
    print("CALENDAR SYNC CHANGE REPORT")
    print("="*50)
    print(f"Period: {report['period']}")
    print(f"Total Syncs: {report['total_syncs']}")
    print(f"Total Changes: {report['total_changes']}")
    print(f"  - Created: {report['total_created']}")
    print(f"  - Updated: {report['total_updated']}")
    print(f"  - Deleted: {report['total_deleted']}")
    print(f"Average Success Rate: {report['avg_success_rate']}%")
    
    if report['avg_sync_interval_hours']:
        print(f"Average Sync Interval: {report['avg_sync_interval_hours']} hours")
    
    if report['most_active_sheets']:
        print("\nMost Active Sheets:")
        for sheet in report['most_active_sheets'][:5]:
            print(f"  - {sheet['sheet_name']}: {sheet['total_created']} events created")
    
    # Create charts
    try:
        chart_path = monitor.create_charts(days=7)
        print(f"\nCharts saved to: {chart_path}")
    except Exception as e:
        logger.error(f"Error creating charts: {e}")
    
    print("="*50)

if __name__ == '__main__':
    main() 