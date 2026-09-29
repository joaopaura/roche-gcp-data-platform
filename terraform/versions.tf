terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0, < 8.0"
    }
  }

  # Remote state in GCS (bucket created once with gcloud, see docs/setup.md)
  backend "gcs" {
    bucket = "roche-data-platform-tfstate"
    prefix = "terraform/state"
  }
}
