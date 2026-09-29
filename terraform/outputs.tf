output "lake_bucket" {
  value = google_storage_bucket.lake.name
}

output "datasets" {
  value = concat([for d in google_bigquery_dataset.layers : d.dataset_id], [google_bigquery_dataset.dbt_ci.dataset_id])
}

output "service_accounts" {
  value = {
    ingestion = google_service_account.ingestion.email
    dbt       = google_service_account.dbt.email
    powerbi   = google_service_account.powerbi.email
  }
}
