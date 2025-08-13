# Google Calendar Sync

This project automates the synchronization of events from a Google Spreadsheet to Google Calendar. It provides a flexible and powerful toolset, including a web-based UI for interactive syncing and scripts for automated, scheduled updates.

![Screenshot of the web interface](httpss://user-images.githubusercontent.com/12345/67890.png) <!--- Placeholder for a real image -->

## Core Features

- **Web Interface**: An intuitive UI to preview and sync spreadsheet data interactively.
- **Automated Syncing**: Scripts designed to be run on a schedule (e.g., hourly) for hands-off synchronization.
- **Flexible Deployment**: Deploy locally, using Docker, or on cloud platforms like Render and Google Cloud Run.
- **Cross-Account Support**: Sync calendars between different Google accounts using either calendar sharing or a service account.
- **Monitoring**: Track sync history and performance with built-in monitoring tools.

## Getting Started

To get started, clone the repository and set up your environment.

```bash
git clone https://github.com/your-username/google-calendar-sync.git
cd google-calendar-sync

# Set up a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Next, you'll need to configure your environment variables. Create a `.env` file and add your credentials. For a detailed walkthrough, see the [Authentication Guide](./docs/AUTHENTICATION.md).

```env
# .env - Example configuration
SPREADSHEET_ID=your_google_spreadsheet_id
FLASK_SECRET_KEY=a_strong_and_random_secret_key
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## Usage

### Web Interface

For interactive use, run the Flask web application.

```bash
python app.py
```
Navigate to `http://127.0.0.1:5000` in your browser.

### Automated Sync

For scheduled, non-interactive syncs, use the `automated_sync.py` script. This is ideal for running via a cron job or a cloud scheduler.

```bash
python automated_sync.py
```

## Documentation

For more detailed information, please refer to the guides in the `docs/` directory:

- **[Deployment Guide](./docs/DEPLOYMENT.md)**: Comprehensive instructions for deploying the application on various platforms (Local, Render, Google Cloud Run, Docker).
- **[Authentication Guide](./docs/AUTHENTICATION.md)**: Detailed steps for setting up Google OAuth 2.0 and Service Accounts.
- **[Advanced Setup Guide](./docs/ADVANCED_SETUP.md)**: Information on email notifications, monitoring, and other advanced features.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License.
