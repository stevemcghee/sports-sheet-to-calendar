# Deployment Guide

This guide provides comprehensive instructions for deploying the Google Calendar Sync application.

## Deployment Options

You can deploy this application using several methods, each suited for different needs:

| Platform | Recommended Use Case | Key Features |
| :--- | :--- | :--- |
| **Local Development** | Testing, debugging, and direct control | Full access to code, immediate feedback |
| **Render** | Easy web interface hosting | Free tier, simple Git-based deployment |
| **Google Cloud Run** | Robust, scalable automated sync | Pay-per-use, integrated scheduling, monitoring |
| **Docker** | Containerized and portable deployments | Consistent environment, platform-agnostic |

---

## 1. Local Development Setup

Running the application on your local machine is ideal for development and testing.

### Prerequisites
- Python 3.9+
- A Google account with Google Calendar and Sheets enabled

### Steps

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/google-calendar-sync.git
    cd google-calendar-sync
    ```

2.  **Set Up a Virtual Environment**:
    This isolates project dependencies.
    ```bash
    # Create and activate the virtual environment
    python3 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the project root and add the following, replacing the placeholder values:
    ```env
    # .env
    SPREADSHEET_ID=your_google_spreadsheet_id
    GEMINI_API_KEY=your_gemini_api_key
    FLASK_SECRET_KEY=a_strong_and_random_secret_key

    # Optional: For the web UI, you also need Google OAuth credentials
    GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    ```
    - For help generating credentials, see the [Authentication Setup Guide](./AUTHENTICATION.md).
    - To generate a `FLASK_SECRET_KEY`, run: `python -c 'import secrets; print(secrets.token_hex(16))'`

5.  **Run the Application**:
    -   **Web Interface**:
        ```bash
        python app.py
        ```
        Access the UI at `http://127.0.0.1:5000`.
    -   **Command-Line Sync**:
        ```bash
        python calendar_sync.py
        ```

---

## 2. Render Deployment

Render is a great choice for deploying the web interface with minimal setup.

### Prerequisites
- A GitHub account with the project repository.
- A Render account.

### Steps

1.  **Push Code to GitHub**:
    Ensure your latest code is on a GitHub repository.

2.  **Create a New Web Service on Render**:
    - Log in to Render and click **New > Web Service**.
    - Connect your GitHub repository.

3.  **Configure Render Settings**:
    - **Name**: A unique name for your service (e.g., `google-calendar-sync`).
    - **Region**: Choose a region.
    - **Branch**: Your main branch.
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `gunicorn app:app`
    - **Instance Type**: `Free` is sufficient for testing.

4.  **Add Environment Variables**:
    - In the Render dashboard, go to **Environment**.
    - Add the same environment variables as listed in the local setup, including `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
    - **Important**: Update your Google OAuth credentials to include the Render URL (`https://your-app-name.onrender.com/auth/callback`) as an authorized redirect URI.

5.  **Deploy**:
    - Click **Create Web Service**. Render will automatically build and deploy your application.

---

## 3. Google Cloud Run Deployment

Google Cloud Run is the recommended platform for running the automated, scheduled sync. Deployments are automated via a Cloud Build trigger that deploys the application whenever a pull request is merged into the `main` branch.

### Prerequisites
- A Google Cloud project with billing enabled.
- A GitHub repository for the project.

### Steps

1.  **Enable Google Cloud APIs**:
    Run the following command to ensure all necessary services are enabled:
    ```bash
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com
    ```

2.  **Set Up Cloud Build Trigger**:
    - In the Google Cloud Console, go to **Cloud Build > Triggers**.
    - Connect your GitHub repository.
    - Create a new trigger with the following settings:
        - **Name**: A descriptive name (e.g., `deploy-on-pr-merge`).
        - **Event**: **Pull request**.
        - **Repository**: Your project's repository.
        - **Base branch**: `^main$`
        - **Configuration**: **Cloud Build configuration file (yaml or json)**.
        - **Location**: `/cloudbuild.yaml`.

3.  **Configure Environment Variables**:
    - In the Cloud Build trigger settings, under **Advanced > Substitution variables**, add the required environment variables for your application (e.g., `_FLASK_SECRET_KEY`, `_GEMINI_API_KEY`, `_SMTP_PASSWORD`).
    - The variable names must match those in `cloudbuild.yaml` (e.g., `_SPREADSHEET_ID`).
    - **Important**: For sensitive values, it is highly recommended to store them in **Secret Manager** and grant the Cloud Build service account access to them.

4.  **Set Up Cloud Scheduler**:
    The `cloudbuild.yaml` file includes a step to create a Cloud Scheduler job. You can modify the schedule in the `cloudbuild.yaml` file as needed. The default is to trigger the sync every hour.

---

## 4. Docker Deployment

Docker provides a consistent and portable environment for the application.

### Prerequisites
- Docker installed on your machine.

### Steps

1.  **Build the Docker Image**:
    From the project root, run:
    ```bash
    docker build -t google-calendar-sync .
    ```

2.  **Run the Docker Container**:
    -   **Using `docker run`**:
        Create a `.env` file with your secrets, then run the container:
        ```bash
        docker run --env-file .env -p 5000:5000 google-calendar-sync
        ```
    -   **Using Docker Compose**:
        A `docker-compose.yml` file can simplify this process, especially if you have multiple services.

3.  **Deploying to a Cloud Provider**:
    You can push the Docker image to a container registry (like Google Container Registry or Docker Hub) and deploy it to any cloud provider that supports containers, including Google Cloud Run, AWS Fargate, or Azure Container Instances.
    ```bash
    # Example for Google Cloud Registry
    docker tag google-calendar-sync gcr.io/YOUR_PROJECT_ID/google-calendar-sync
    docker push gcr.io/YOUR_PROJECT_ID/google-calendar-sync
    ```
    From there, you can deploy the image from the registry.

---

## 5. Deploying Updates

After making code changes, you'll need to redeploy the application. The process varies depending on your deployment method.

### Local Development

1.  **Pull the latest code**:
    ```bash
    git pull origin main
    ```
2.  **Update dependencies** (if `requirements.txt` has changed):
    ```bash
    pip install -r requirements.txt
    ```
3.  **Restart the application**:
    Stop the running `app.py` or `calendar_sync.py` script and start it again.

### Render

Render makes updates simple. If you connected your GitHub repository, Render automatically redeploys your application whenever you push changes to the configured branch (e.g., `main`).

1.  **Commit and push your changes** to GitHub:
    ```bash
    git commit -am "Add new feature"
    git push origin main
    ```
2.  Render will detect the push, start a new build, and deploy the new version automatically. You can monitor the progress in your Render dashboard.

### Google Cloud Run

Deployments to Google Cloud Run are handled automatically by a Cloud Build trigger when a pull request is merged into the `main` branch.

### Docker

Updating a Docker deployment involves rebuilding the image and restarting the container.

1.  **Stop the old container**:
    ```bash
    docker stop <container_id>
    ```
2.  **Rebuild the image** with your code changes:
    ```bash
    docker build -t google-calendar-sync .
    ```
3.  **Run the new container**:
    ```bash
    docker run --env-file .env -p 5000:5000 google-calendar-sync
    ```
4.  **If using a registry**, you also need to push the new image and update the service running it:
    ```bash
    docker tag google-calendar-sync gcr.io/YOUR_PROJECT_ID/google-calendar-sync:latest
    docker push gcr.io/YOUR_PROJECT_ID/google-calendar-sync:latest
    # Then, update your cloud service to pull the 'latest' tag.
    ```