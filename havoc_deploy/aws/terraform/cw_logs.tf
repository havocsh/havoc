resource "aws_cloudwatch_log_group" "ecs_task_logs" {
  name              = "${var.deployment_name}/tasks_cluster"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "ecs_playbook_operator_logs" {
  name              = "${var.deployment_name}/playbook_operator_cluster"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "task_results_logging" {
  name              = "${var.deployment_name}/task_results_logging"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "playbook_results_logging" {
  name              = "${var.deployment_name}/playbook_results_logging"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "authorizer" {
  name              = "/aws/lambda/${var.deployment_name}-authorizer"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "trigger_executor" {
  name              = "/aws/lambda/${var.deployment_name}-trigger-executor"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "manage" {
  name              = "/aws/lambda/${var.deployment_name}-manage"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "remote_task" {
  name              = "/aws/lambda/${var.deployment_name}-remote-task"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "task_control" {
  name              = "/aws/lambda/${var.deployment_name}-task-control"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "playbook_operator_control" {
  name              = "/aws/lambda/${var.deployment_name}-playbook-operator-control"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "task_result" {
  name              = "/aws/lambda/${var.deployment_name}-task-result"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_group" "playbook_operator_result" {
  name              = "/aws/lambda/${var.deployment_name}-playbook-operator-result"
  retention_in_days = var.results_queue_expiration
}

resource "aws_cloudwatch_log_subscription_filter" "task_result_lambdafunction_logfilter" {
  name            = "task_result_lambdafunction_logfilter"
  log_group_name  = aws_cloudwatch_log_group.ecs_task_logs.name
  filter_pattern  = "instruct_command_output user_id task_name"
  destination_arn = aws_lambda_function.task_result.arn
}

resource "aws_cloudwatch_log_subscription_filter" "playbook_operator_result_lambdafunction_logfilter" {
  name            = "playbook_operator_result_lambdafunction_logfilter"
  log_group_name  = aws_cloudwatch_log_group.ecs_playbook_operator_logs.name
  filter_pattern  = "user_id"
  destination_arn = aws_lambda_function.playbook_operator_result.arn
}
