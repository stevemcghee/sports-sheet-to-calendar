terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "calendar-json.googleapis.com",
    "sheets.googleapis.com"
  ])
  
  service = each.value
  disable_dependent_services = false
  disable_on_destroy = false
}

# Create Cloud Run service
resource "google_cloud_run_v2_service" "calendar_sync" {
  name     = "calendar-sync"
  location = var.region

  template {
    containers {
      image = "us-central1-docker.pkg.dev/${var.project_id}/cloud-run-source-deploy/calendar-sync"
      
      ports {
        container_port = 5000
      }
      
      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }
      
      env {
        name  = "FLASK_ENV"
        value = "production"
      }
      
      env {
        name  = "SEND_EMAIL"
        value = "true"
      }
      
      env {
        name  = "SMTP_SERVER"
        value = "smtp.gmail.com"
      }
      
      env {
        name  = "SMTP_PORT"
        value = "587"
      }
      
      env {
        name  = "SMTP_USERNAME"
        value = var.smtp_username
      }
      
      env {
        name  = "TO_EMAIL"
        value = var.to_email
      }
      
      env {
        name  = "USE_GEMINI"
        value = "true"
      }
      
      env {
        name  = "SPREADSHEET_ID"
        value = var.spreadsheet_id
      }
      
      env {
        name  = "FLASK_SECRET_KEY"
        value = var.flask_secret_key
      }
      
      env {
        name  = "GEMINI_API_KEY"
        value = var.gemini_api_key
      }
      
      env {
        name  = "SMTP_PASSWORD"
        value = var.smtp_password
      }
      
      env {
        name  = "GOOGLE_CLIENT_ID"
        value = var.google_client_id
      }
      
      env {
        name  = "GOOGLE_CLIENT_SECRET"
        value = var.google_client_secret
      }
    }
    
    timeout = "3600s"
    
    scaling {
      max_instance_count = 10
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Create Cloud Scheduler job
resource "google_cloud_scheduler_job" "calendar_sync_job" {
  name             = "calendar-sync-job"
  description      = "Nightly calendar sync job at 3 AM"
  schedule         = "0 3 * * *"
  time_zone        = "America/Los_Angeles"
  attempt_deadline = "300s"
  
  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.calendar_sync.uri}/trigger-sync"
    
    headers = {
      "Content-Type" = "application/json"
      "User-Agent"   = "Google-Cloud-Scheduler"
    }
  }
  
  depends_on = [google_cloud_run_v2_service.calendar_sync]
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.calendar_sync.location
  service  = google_cloud_run_v2_service.calendar_sync.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow Cloud Scheduler to invoke Cloud Run
resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  location = google_cloud_run_v2_service.calendar_sync.location
  service  = google_cloud_run_v2_service.calendar_sync.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}

# Get current project data
data "google_project" "current" {} 