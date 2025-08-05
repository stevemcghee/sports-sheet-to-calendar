output "cloud_run_service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.calendar_sync.uri
}

output "cloud_run_service_name" {
  description = "The name of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.calendar_sync.name
}

output "scheduler_job_name" {
  description = "The name of the Cloud Scheduler job"
  value       = google_cloud_scheduler_job.calendar_sync_job.name
}

output "scheduler_job_schedule" {
  description = "The schedule of the Cloud Scheduler job"
  value       = google_cloud_scheduler_job.calendar_sync_job.schedule
}

output "project_id" {
  description = "The Google Cloud project ID"
  value       = var.project_id
}

output "region" {
  description = "The Google Cloud region"
  value       = var.region
} 