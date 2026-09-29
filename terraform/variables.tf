variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the data lake and BigQuery datasets (us-central1 = inside the GCS free tier)"
  type        = string
  default     = "us-central1"
}

variable "developer_email" {
  description = "Google account allowed to impersonate the service accounts locally"
  type        = string
}

variable "environment" {
  description = "Environment label"
  type        = string
  default     = "dev"
}
