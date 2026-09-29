# Data lake: raw/ (original files) and bronze/ (Parquet), partitioned by source and load date
resource "google_storage_bucket" "lake" {
  name                        = "${var.project_id}-lake"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels

  # Temporary files (e.g. Kafka micro-batches before load) are removed after 7 days
  lifecycle_rule {
    condition {
      age            = 7
      matches_prefix = ["tmp/"]
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }

  depends_on = [google_project_service.apis]
}
