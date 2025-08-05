variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
  default     = "stevemcghee-slosports"
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "spreadsheet_id" {
  description = "The Google Spreadsheet ID to sync"
  type        = string
  default     = "1DiA6HTQjDiPzEua_kxcw175C-uMWGnIq_PAKICbiMzQ"
}

variable "smtp_username" {
  description = "SMTP username for email notifications"
  type        = string
  default     = "sloswimtiming@gmail.com"
}

variable "smtp_password" {
  description = "SMTP password for email notifications"
  type        = string
  sensitive   = true
}

variable "to_email" {
  description = "Email address to send notifications to"
  type        = string
  default     = "sloswimtiming@gmail.com"
}

variable "flask_secret_key" {
  description = "Flask secret key for session management"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key for AI parsing"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
} 