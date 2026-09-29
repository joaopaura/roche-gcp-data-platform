# Lakehouse pattern: FAERS (~135M rows) stays as Parquet in the lake (cheap GCS storage).
# BigQuery reads it through external tables with Hive partitioning (quarter=YYYYQn),
# and dbt materialises only the curated Roche subset and aggregates.

locals {
  faers_tables = {
    demo = "Patient demographics and report metadata (one row per report version)"
    drug = "Drugs reported per case, with role (PS primary suspect, SS, C, I)"
    reac = "Adverse reactions (MedDRA preferred terms)"
    outc = "Patient outcomes (death, hospitalisation, ...)"
    rpsr = "Report sources"
    ther = "Therapy start/end dates"
    indi = "Indications (why the drug was used)"
  }
}

resource "google_bigquery_table" "faers_external" {
  for_each            = local.faers_tables
  dataset_id          = google_bigquery_dataset.layers["raw"].dataset_id
  table_id            = "faers_${each.key}"
  description         = "FAERS ${upper(each.key)} | ${each.value} | external table over bronze Parquet"
  deletion_protection = false
  labels              = merge(local.labels, { layer = "raw", source = "faers" })

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"
    source_uris   = ["gs://${google_storage_bucket.lake.name}/bronze/faers/${each.key}/*"]

    hive_partitioning_options {
      mode              = "AUTO"
      source_uri_prefix = "gs://${google_storage_bucket.lake.name}/bronze/faers/${each.key}/"
    }
  }

  lifecycle {
    ignore_changes = [schema]
  }
}
