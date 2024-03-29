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
  },
  "remote_task": {
    "S": "no"
  },
  "task_name": {
    "S": "None"
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
  "certificate_arn": {
    "S": "${aws_acm_certificate.api_gateway_cert[count.index].arn}"
  },
  "tasks": {
    "SS": ${jsonencode(["None"])}
  },
  "listeners": {
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
    "SS": ${jsonencode(["list_auxiliary","list_exploits","list_payloads","list_jobs","list_metasploit_sessions","modify_routes","run_auxiliary","run_exploit","set_auxiliary_module","set_auxiliary_options","set_exploit_module","set_exploit_options","set_exploit_target","set_payload_module","set_payload_options","show_auxiliary","show_auxiliary_options","show_auxiliary_option_info","show_auxiliary_evasion","show_configured_auxiliary_options","show_auxiliary_requirements","show_missing_auxiliary_requirements","show_last_auxiliary_results","show_exploit","show_exploit_options","show_exploit_option_info","show_exploit_targets","show_exploit_evasion","show_exploit_payloads","show_configured_exploit_options","show_exploit_requirements","show_missing_exploit_requirements","show_last_exploit_results","show_payload","show_payload_options","show_payload_option_info","show_configured_payload_options","show_payload_requirements","show_missing_payload_requirements","show_job_info","show_metasploit_session_info","execute_auxiliary","execute_exploit","generate_payload","run_metasploit_session_command","send_command","run_metasploit_session_shell_command","send_shell_command","metasploit_session_tabs","load_metasploit_session_plugin","metasploit_session_import_psh","metasploit_session_run_psh_cmd","run_metasploit_session_script","get_metasploit_session_writeable_dir","metasploit_session_read","detach_metasploit_session","kill_metasploit_session","kill_job","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
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
    "SS": ${jsonencode(["get_listeners","get_listener_options","create_listener","kill_listener","kill_all_listeners","get_stagers","create_stager","list_empire_agents","list_stale_empire_agents","remove_empire_agent","remove_stale_empire_agents","execute_empire_agent_shell_command","get_empire_agent_results","list_empire_agent_task_ids","rename_empire_agent","kill_empire_agent","kill_all_empire_agents","list_empire_modules","search_empire_modules","execute_empire_agent_module","download_file_from_empire_agent","upload_file_to_empire_agent","sync_downloads","get_stored_credentials","get_logged_events","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
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
    "SS": ${jsonencode(["create_listener","kill_listener","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
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
    "SS": ${jsonencode(["create_listener","kill_listener","cert_gen","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","ls","del","terminate"])}
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

resource "aws_dynamodb_table_item" "remote_operator_task_type" {
  table_name = aws_dynamodb_table.task_types.name
  hash_key   = aws_dynamodb_table.task_types.hash_key

  item = <<ITEM
{
  "task_type": {
    "S": "remote_operator"
  },
  "task_version": {
    "S": "${var.deployment_version}"
  },
  "capabilities": {
    "SS": ${jsonencode(["task_execute_command","task_get_command_output","task_kill_command","task_download_file","task_create_file","ls","task_delete_file","task_create_share_with_data","task_delete_share_with_data","task_list_shares_with_data","task_run_container","task_get_container_logs","task_stop_container","task_list_containers","task_scp_file","echo","sync_from_workspace","sync_to_workspace","upload_to_workspace","download_from_workspace","terminate"])}
  },
  "source_image": {
    "S": "None"
  },
  "cpu": {
    "N": "0"
  },
  "memory": {
    "N": "0"
  },
  "created_by": {
    "S": "${var.deployment_admin_email}"
  }
}
ITEM
}

resource "aws_dynamodb_table_item" "conti_ransomware_playbook_type" {
  table_name = aws_dynamodb_table.playbook_types.name
  hash_key   = aws_dynamodb_table.playbook_types.hash_key

  item = <<ITEM
{
  "playbook_type": {
    "S": "conti_ransomware"
  },
  "playbook_version": {
    "S": "${var.deployment_version}"
  },
  "template_pointer": {
    "S": "conti_ransomware.template"
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

resource "aws_dynamodb_table" "playbooks" {
  name           = "${var.deployment_name}-playbooks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "playbook_name"

  attribute {
    name = "playbook_name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "playbook_types" {
  name           = "${var.deployment_name}-playbook-types"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "playbook_type"

  attribute {
    name = "playbook_type"
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

resource "aws_dynamodb_table" "triggers" {
  name           = "${var.deployment_name}-triggers"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "trigger_name"

  attribute {
  name = "trigger_name"
  type = "S"
  }
}

resource "aws_dynamodb_table" "listeners" {
  name           = "${var.deployment_name}-listeners"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "listener_name"

  attribute {
    name = "listener_name"
    type = "S"
  }
}

resource "aws_dynamodb_table" "workspace_access" {
  name           = "${var.deployment_name}-workspace-access"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "object_access"
  range_key      = "create_time"

  attribute {
    name = "object_access"
    type = "S"
  }

  attribute {
  name = "create_time"
  type = "N"
  }

  ttl {
  attribute_name = "expire_time"
  enabled        = true
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

resource "aws_dynamodb_table" "task_queue" {
  name           = "${var.deployment_name}-task-queue"
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

resource "aws_dynamodb_table" "playbook_queue" {
  name           = "${var.deployment_name}-playbook-queue"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "playbook_name"
  range_key      = "run_time"

  attribute {
    name = "playbook_name"
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

resource "aws_dynamodb_table" "trigger_queue" {
  name           = "${var.deployment_name}-trigger-queue"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "trigger_name"
  range_key      = "run_time"

  attribute {
    name = "trigger_name"
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