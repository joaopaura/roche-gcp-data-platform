locals {
  datasets = {
    raw          = "Bronze layer: data loaded as-is from the lake (Python loaders)"
    staging      = "dbt staging models: cleaned, typed, renamed (1:1 with sources)"
    intermediate = "dbt intermediate models: joins, deduplication, business logic"
    marts        = "dbt marts: star schema consumed by Power BI"
    ops          = "Pipeline observability: run log, dbt test results, Kafka metrics"
  }
}

resource "google_bigquery_dataset" "layers" {
  for_each                   = local.datasets
  dataset_id                 = each.key
  friendly_name              = each.key
  description                = each.value
  location                   = var.region
  max_time_travel_hours      = 48
  delete_contents_on_destroy = false
  labels                     = merge(local.labels, { layer = each.key })

  depends_on = [google_project_service.apis]
}

# Short-lived dataset for dbt CI runs on pull requests (tables expire after 1 day)
resource "google_bigquery_dataset" "dbt_ci" {
  dataset_id                  = "dbt_ci"
  description                 = "dbt CI builds on pull requests (auto-expiring)"
  location                    = var.region
  default_table_expiration_ms = 86400000
  max_time_travel_hours       = 48
  delete_contents_on_destroy  = true
  labels                      = merge(local.labels, { layer = "ci" })

  depends_on = [google_project_service.apis]
}
