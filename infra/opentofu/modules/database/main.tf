# Cloud SQL for PostgreSQL, private IP only, with automated backups and
# point-in-time recovery. Deletion protection is on by default; the DR drill
# (docs/operations/disaster-recovery.md) restores from these backups.

variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" { type = string }
variable "network_id" { type = string }
variable "private_vpc_connection" { type = string }
variable "tier" {
  type    = string
  default = "db-custom-1-3840"
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "database_name" {
  type    = string
  default = "crucible"
}

resource "google_sql_database_instance" "main" {
  project             = var.project_id
  name                = "${var.name_prefix}-pg"
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = var.deletion_protection
  # The private-services peering must exist before the instance can take a
  # private IP; the environment wires this dependency explicitly.
  depends_on = [var.private_vpc_connection]

  settings {
    tier              = var.tier
    availability_type = "REGIONAL" # synchronous standby: survives a zone loss
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7
      backup_retention_settings { retained_backups = 30 }
    }

    ip_configuration {
      ipv4_enabled    = false # no public IP
      private_network = var.network_id
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    insights_config { query_insights_enabled = true }
  }
}

resource "google_sql_database" "crucible" {
  project  = var.project_id
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

# The application user's password lives in Secret Manager; Terraform reads it
# from a variable sourced from there, never generating or printing it in plan.
variable "app_user_password" {
  type      = string
  sensitive = true
}

resource "google_sql_user" "app" {
  project  = var.project_id
  name     = "crucible_app"
  instance = google_sql_database_instance.main.name
  password = var.app_user_password
}

output "instance_connection_name" { value = google_sql_database_instance.main.connection_name }
output "private_ip" { value = google_sql_database_instance.main.private_ip_address }
