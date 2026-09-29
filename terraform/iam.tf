# Least-privilege service accounts, one per workload (no JSON keys: local use via impersonation)

resource "google_service_account" "ingestion" {
  account_id   = "sa-ingestion"
  display_name = "Ingestion jobs (Python batch + Kafka consumer)"
}

resource "google_service_account" "dbt" {
  account_id   = "sa-dbt"
  display_name = "dbt transformations"
}

resource "google_service_account" "powerbi" {
  account_id   = "sa-powerbi"
  display_name = "Power BI read-only access to marts"
}

# Every workload needs to run BigQuery jobs in the project
resource "google_project_iam_member" "job_user" {
  for_each = {
    ingestion = google_service_account.ingestion.email
    dbt       = google_service_account.dbt.email
    powerbi   = google_service_account.powerbi.email
  }
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "powerbi_read_session" {
  project = var.project_id
  role    = "roles/bigquery.readSessionUser"
  member  = "serviceAccount:${google_service_account.powerbi.email}"
}

# Ingestion: write to the lake and to the raw dataset
resource "google_storage_bucket_iam_member" "ingestion_lake" {
  bucket = google_storage_bucket.lake.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_bigquery_dataset_iam_member" "ingestion_raw" {
  dataset_id = google_bigquery_dataset.layers["raw"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_bigquery_dataset_iam_member" "ingestion_ops" {
  dataset_id = google_bigquery_dataset.layers["ops"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

# dbt: read raw + lake, write the transformation layers
resource "google_storage_bucket_iam_member" "dbt_lake" {
  bucket = google_storage_bucket.lake.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.dbt.email}"
}

resource "google_bigquery_dataset_iam_member" "dbt_raw" {
  dataset_id = google_bigquery_dataset.layers["raw"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.dbt.email}"
}

resource "google_bigquery_dataset_iam_member" "dbt_write" {
  for_each = {
    staging      = google_bigquery_dataset.layers["staging"].dataset_id
    intermediate = google_bigquery_dataset.layers["intermediate"].dataset_id
    marts        = google_bigquery_dataset.layers["marts"].dataset_id
    ops          = google_bigquery_dataset.layers["ops"].dataset_id
    dbt_ci       = google_bigquery_dataset.dbt_ci.dataset_id
  }
  dataset_id = each.value
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dbt.email}"
}

# Power BI: read-only on marts and ops
resource "google_bigquery_dataset_iam_member" "powerbi_read" {
  for_each = {
    marts = google_bigquery_dataset.layers["marts"].dataset_id
    ops   = google_bigquery_dataset.layers["ops"].dataset_id
  }
  dataset_id = each.value
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.powerbi.email}"
}

# Developer can impersonate the service accounts locally (keyless auth)
resource "google_service_account_iam_member" "developer_impersonation" {
  for_each = {
    ingestion = google_service_account.ingestion.name
    dbt       = google_service_account.dbt.name
    powerbi   = google_service_account.powerbi.name
  }
  service_account_id = each.value
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "user:${var.developer_email}"
}
