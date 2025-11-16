# Authentication and Authorization Guide

This guide covers the authentication and authorization methods used in the Google Calendar Sync application.

## Authentication Strategies

The application supports two primary authentication methods for accessing Google APIs:

| Method | Recommended Use Case | Description |
| :--- | :--- | :--- |
| **Google OAuth 2.0** | Web interface and local development | A user-centric flow where the application is granted access to a user's Google account. Requires user consent via a browser. |
| **Service Account** | Automated, backend-only deployments (e.g., Google Cloud Run) | An application-centric flow where the application authenticates as itself, not as a user. Ideal for automated, non-interactive scenarios. |

---

## 1. Google OAuth 2.0 for Web Interface

This method is required for the web interface (`app.py`) and for local development where you are acting on behalf of your own Google account.

### Steps to Create OAuth 2.0 Credentials

1.  **Open the Google Cloud Console**:
    Navigate to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).

2.  **Create Credentials**:
    - Click **+ Create Credentials** and select **OAuth client ID**.
    - **Application type**: Select **Web application**.
    - **Name**: Give it a descriptive name (e.g., `Calendar Sync Web UI`).

3.  **Configure Authorized Redirect URIs**:
    This is a critical security step. You must tell Google which URLs are allowed to receive the authentication token.
    - **For local development**, add: `http://localhost:5000/auth/callback`
    - **For a Google Cloud Run deployment**, add: `https://your-service-name-....run.app/auth/callback`
    - **For a Cloud Run deployment**, add: `https://your-cloud-run-service-url/auth/callback`

4.  **Save and Get Credentials**:
    - Click **Create**.
    - A dialog will show your **Client ID** and **Client Secret**. You will need these for your environment variables (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`).

### Using OAuth 2.0 Credentials

-   **Local Development**: Place the credentials in your `.env` file.
-   **Cloud Run**: Add them as environment variables in the service's settings.

---

## 2. Service Accounts for Automation

A service account is the best practice for automated tasks, like the scheduled sync on Google Cloud Run. It's a special type of Google account that belongs to your application instead of an individual user.

### When to Use a Service Account

- **Automated Syncs**: When the application needs to run on a schedule without user interaction.
- **Headless Environments**: For deployments where a browser-based login is not possible.

### Steps to Use a Service Account

The included deployment script (`deploy_cloud_run.sh`) automates this process, but here is a summary of the steps:

1.  **Create a Service Account**:
    - In the Google Cloud Console, go to **IAM & Admin > Service Accounts**.
    - Click **+ Create Service Account**, give it a name (e.g., `calendar-sync-automation`), and grant it the necessary roles (e.g., `Editor` for simplicity, or more granular roles for production).

2.  **Grant Domain-Wide Delegation (if necessary)**:
    If the service account needs to access calendars belonging to other users within your Google Workspace organization, you must grant it domain-wide delegation.
    - In the service account's settings, enable **Domain-wide Delegation**.
    - In the Google Workspace Admin console, go to **Security > API Controls > Domain-wide Delegation** and authorize the service account's Client ID with the required scopes:
        - `https://www.googleapis.com/auth/calendar`
        - `https://www.googleapis.com/auth/spreadsheets.readonly`

3.  **Using the Service Account in Cloud Run**:
    - When you deploy to Cloud Run, you can specify that the service should run using the identity of your service account.
    - The Cloud Scheduler job will then be invoked with the service account's permissions, allowing it to access the necessary Google APIs without a user-based login.

---

## 3. Cross-Account Access Scenarios

There are two common scenarios for accessing calendars across different Google accounts.

### Scenario A: Sharing Calendars with a User Account

This is the simplest method for cross-account access and works well with the OAuth 2.0 flow.

- **Owner Account** (`account_A@gmail.com`): The account that owns the target Google Calendars.
- **Syncing Account** (`account_B@gmail.com`): The account that runs the application and performs the sync.

**Setup**:
1.  The **Owner Account** shares each Google Calendar with the **Syncing Account**.
    - In Google Calendar, go to `Settings and sharing` for the calendar.
    - Under `Share with specific people`, add `account_B@gmail.com` with `Make changes to events` permissions.
2.  The application is configured to use the **Syncing Account's** OAuth 2.0 credentials.
3.  When the application runs, it authenticates as `account_B@gmail.com` and can access `account_A@gmail.com`'s calendars due to the sharing permissions.

### Scenario B: Using a Service Account with Delegation

This is the recommended approach for automated cross-account access within a Google Workspace.

- **Target User** (`user@yourdomain.com`): The user whose calendars need to be accessed.
- **Service Account**: The application's identity.

**Setup**:
1.  Create a **Service Account** as described above.
2.  Grant it **Domain-Wide Delegation** in the Google Workspace Admin console.
3.  In your application's configuration, specify the `TARGET_USER_EMAIL` (e.g., `user@yourdomain.com`).
4.  The application code will use the service account's credentials to impersonate the target user, granting it access to their calendars without needing explicit sharing. This is handled by the `google-auth` library when correctly configured.
