# dynamodb.tf

resource "random_string" "api_key" {
  length = 12
  special = false
}

resource "random_string" "secret" {
  length  = 24
  special = true
  override_special = "~#*_-+=,.:"
}

resource "aws_dynamodb_table_item" "deployment_admin" {
  table_name = aws_dynamodb_table.authorizer.name
  hash_key   = aws_dynamodb_table.authorizer.hash_key

  item = <<ITEM
{
  "api_key": {
    "S": "${random_string.api_key.id}"
  },
  "secret_key": {
    "S": "${random_string.secret.id}"
  },
  "user_id": {
    "S": "${var.deployment_admin_email}"
  },
  "admin": {
    "S": "yes"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "domain_name" {
  count      = var.enable_domain_name ? 1 : 0
  table_name = aws_dynamodb_table.domains.name
  hash_key   = aws_dynamodb_table.domains.hash_key

  item = <<ITEM
{
  "domain_name": {
    "S": "${var.domain_name}"
  },
  "hosted_zone": {
    "S": "${var.hosted_zone}"
  },
  "api_domain": {
    "S": "yes"
  },
  "tasks": {
    "SS": ${jsonencode(["None"])}
  },
  "host_names": {
    "SS": ["${var.deployment_name}-api"]
  },
  "user_id": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "nmap_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "nmap"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["run_scan","get_scan_info","get_scan_results","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/nmap:${var.deployment_version}"
  },
  "cpu": {
    "N": "512"
  },
  "memory": {
    "N": "1024"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "metasploit_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "metasploit"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["list_exploits","list_payloads","list_jobs","list_sessions","set_exploit_module","set_exploit_options","set_exploit_target","set_payload_module","set_payload_options","show_exploit","show_exploit_options","show_exploit_option_info","show_exploit_targets","show_exploit_evasion","show_exploit_payloads","show_configured_exploit_options","show_exploit_requirements","show_missing_exploit_requirements","show_last_exploit_results","show_payload","show_payload_options","show_payload_option_info","show_configured_payload_options","show_payload_requirements","show_missing_payload_requirements","show_job_info","show_session_info","execute_exploit","generate_payload","run_session_command","run_session_shell_command","session_tabs","load_session_plugin","session_import_psh","session_run_psh_cmd","run_session_script","get_session_writeable_dir","session_read","detach_session","kill_session","kill_job","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/metasploit:${var.deployment_version}"
  },
  "cpu": {
    "N": "1024"
  },
  "memory": {
    "N": "4096"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "powershell_empire_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "powershell_empire"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["get_listeners","get_listener_options","create_listener","kill_listener","kill_all_listeners","get_stagers","create_stager","get_agents","get_stale_agents","remove_agent","remove_stale_agents","agent_shell_command","get_task_id_list","get_shell_command_results","delete_shell_command_results","clear_queued_shell_commands","rename_agent","kill_agent","kill_all_agents","get_modules","search_modules","execute_module","get_stored_credentials","get_logged_events","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/powershell_empire:${var.deployment_version}"
  },
  "cpu": {
    "N": "1024"
  },
  "memory": {
    "N": "4096"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "http_server_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "http_server"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["start_server","stop_server","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/http_server:${var.deployment_version}"
  },
  "cpu": {
    "N": "512"
  },
  "memory": {
    "N": "1024"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "trainman_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "trainman"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["execute_process","get_process_output","kill_process","run_ad_dc","kill_ad_dc","list_java_versions","start_cve_2021_44228_app","stop_cve_2021_44228_app","exploit_cve_2021_44228","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/trainman:${var.deployment_version}"
  },
  "cpu": {
    "N": "1024"
  },
  "memory": {
    "N": "4096"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "exfilkit_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "exfilkit"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["start_http_exfil_server","stop_http_exfil_server","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
  },
  "source_image": {
    "S": "public.ecr.aws/havoc_sh/exfilkit:${var.deployment_version}"
  },
  "cpu": {
    "N": "1024"
  },
  "memory": {
    "N": "4096"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table" "authorizer" {
  name           = "${var.deployment_name}-authorizer"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"

  attribute {
    name = "api_key"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name               = "${var.deployment_name}-ApiKeyIndex"
    hash_key           = "api_key"
    projection_type    = "ALL"
  }
}

resource "aws_dynamodb_table" "deployment" {
  name           = "${var.deployment_name}-deployment"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "deployment_name"

  attribute {
    name = "deployment_name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "domains" {
  name           = "${var.deployment_name}-domains"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "domain_name"

  attribute {
    name = "domain_name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "portgroups" {
  name           = "${var.deployment_name}-portgroups"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "portgroup_name"

  attribute {
    name = "portgroup_name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "task_types" {
  name           = "${var.deployment_name}-task-types"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "task_type"

  attribute {
  name = "task_type"
  type = "S"
  }
}

resource "aws_dynamodb_table" "tasks" {
  name           = "${var.deployment_name}-tasks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "task_name"

  attribute {
  name = "task_name"
  type = "S"
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "${var.deployment_name}-terraform-state-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

resource "aws_dynamodb_table" "queue" {
  name           = "${var.deployment_name}-queue"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "task_name"
  range_key      = "run_time"

  attribute {
    name = "task_name"
    type = "S"
  }

  attribute {
  name = "run_time"
  type = "N"
  }

  ttl {
  attribute_name = "expire_time"
  enabled        = true
  }
}
