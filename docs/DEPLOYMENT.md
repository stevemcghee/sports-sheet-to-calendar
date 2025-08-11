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

Google Cloud Run is the recommended platform for running the automated, scheduled sync.

### Prerequisites
- A Google Cloud project with billing enabled.
- Google Cloud SDK (`gcloud`) installed and authenticated.

### Steps

1.  **Enable Google Cloud APIs**:
    Run the following command to ensure all necessary services are enabled:
    ```bash
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com
    ```

2.  **Deploy to Cloud Run**:
    The provided script handles the entire deployment process.
    ```bash
    # From the project root
    ./deploy_cloud_run.sh YOUR_PROJECT_ID
    ```
    This script will:
    - Build a container image using Cloud Build.
    - Deploy the image to Cloud Run.
    - Create a service account with appropriate permissions.
    - Set up a Cloud Scheduler job to trigger the sync hourly.

3.  **Configure Environment Variables**:
    After deployment, you must add your environment variables in the Google Cloud Console:
    - Navigate to your service in Cloud Run.
    - Click **Edit & Deploy New Revision**.
    - Under the **Variables & Secrets** tab, add your secrets (`SPREADSHEET_ID`, `GEMINI_API_KEY`, etc.).

4.  **Set Up Cloud Scheduler**:
    The script creates a scheduler job, but you can modify it as needed:
    - **Schedule**: The default is hourly (`0 * * * *`).
    - **Target**: It triggers the `/trigger-sync` endpoint of your Cloud Run service.
    - **Authentication**: It uses the created service account to securely invoke your service.

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

To update your Cloud Run service, you can simply re-run the deployment script.

1.  **Re-run the deployment script**:
    ```bash
    ./deploy_cloud_run.sh YOUR_PROJECT_ID
    ```
    This will build a new container image with your changes and deploy it as a new revision to your existing Cloud Run service.

2.  **Automated CI/CD (Advanced)**:
    For a more advanced workflow, you can set up a **Cloud Build Trigger**. This will automatically build and deploy your application to Cloud Run whenever you push changes to your Git repository, similar to how Render works.

    **To set up the trigger**:

    1.  **Connect your Git repository**:
        - In the Google Cloud Console, go to **Cloud Build > Triggers**.
        - Click **Connect repository** and follow the prompts to connect your GitHub or other Git repository.

    2.  **Create a Trigger**:
        - Click **Create trigger**.
        - **Name**: Give it a name like `deploy-on-push-main`.
        - **Event**: Select **Push to a branch**.
        - **Repository**: Select your newly connected repository.
        - **Branch**: `^main# Deployment Guide

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

Google Cloud Run is the recommended platform for running the automated, scheduled sync.

### Prerequisites
- A Google Cloud project with billing enabled.
- Google Cloud SDK (`gcloud`) installed and authenticated.

### Steps

1.  **Enable Google Cloud APIs**:
    Run the following command to ensure all necessary services are enabled:
    ```bash
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com
    ```

2.  **Deploy to Cloud Run**:
    The provided script handles the entire deployment process.
    ```bash
    # From the project root
    ./deploy_cloud_run.sh YOUR_PROJECT_ID
    ```
    This script will:
    - Build a container image using Cloud Build.
    - Deploy the image to Cloud Run.
    - Create a service account with appropriate permissions.
    - Set up a Cloud Scheduler job to trigger the sync hourly.

3.  **Configure Environment Variables**:
    After deployment, you must add your environment variables in the Google Cloud Console:
    - Navigate to your service in Cloud Run.
    - Click **Edit & Deploy New Revision**.
    - Under the **Variables & Secrets** tab, add your secrets (`SPREADSHEET_ID`, `GEMINI_API_KEY`, etc.).

4.  **Set Up Cloud Scheduler**:
    The script creates a scheduler job, but you can modify it as needed:
    - **Schedule**: The default is hourly (`0 * * * *`).
    - **Target**: It triggers the `/trigger-sync` endpoint of your Cloud Run service.
    - **Authentication**: It uses the created service account to securely invoke your service.

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

To update your Cloud Run service, you can simply re-run the deployment script.

1.  **Re-run the deployment script**:
    ```bash
    ./deploy_cloud_run.sh YOUR_PROJECT_ID
    ```
    This will build a new container image with your changes and deploy it as a new revision to your existing Cloud Run service.

 (or your primary branch).
        - **Configuration**: **Cloud Build configuration file (yaml or json)**.
        - **Location**: `/cloudbuild.yaml`.

    3.  **Set Substitution Variables**:
        - Under **Advanced > Substitution variables**, you must add all the required environment variables for your application (e.g., `_FLASK_SECRET_KEY`, `_GEMINI_API_KEY`, `_SMTP_PASSWORD`).
        - The variable names must match those in `cloudbuild.yaml` (e.g., `_SPREADSHEET_ID`).
        - **Important**: For sensitive values like API keys and passwords, it is highly recommended to store them in **Secret Manager** and grant the Cloud Build service account access to them. You can then reference the secrets in your trigger.

    4.  **Save and Activate**:
        - Click **Create**.

    Now, every time you merge a pull request or push to the `main` branch, this trigger will automatically build and deploy the new version of your application to Cloud Run.


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
