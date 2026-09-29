# Roche | GCP Data Platform (Pharma Analytics)

> End-to-end data engineering portfolio project on Google Cloud: batch + streaming ingestion of **real public data** about Roche / Genentech products, a layered BigQuery warehouse built with dbt, infrastructure as code with Terraform, and an executive Power BI report.
>
> **Disclaimer:** independent portfolio project, not affiliated with or endorsed by Roche. Adverse event reports (FAERS) do not establish causality.

## Stack
Python | Apache Kafka | Docker | Google Cloud Storage | BigQuery | dbt Core | Terraform | GitHub Actions | Power BI

## Repository layout
| Folder | Content |
|---|---|
| `terraform/` | Infrastructure as code: lake bucket, BigQuery datasets, service accounts, IAM |
| `ingestion/` | Python batch loaders and Kafka producer/consumer |
| `kafka/` | Local Kafka (KRaft) + Kafka UI via Docker Compose |
| `dbt/` | Transformations: staging, intermediate, marts, tests, docs |
| `powerbi/` | Power BI project (PBIP) and design assets |
| `.github/workflows/` | Scheduled pipelines and dbt CI |
| `docs/` | Architecture, setup and data dictionary |

*Work in progress.*
