resource "aws_cloudwatch_log_group" "ecs_task_logs" {
  name = "${var.deployment_name}/tasks_cluster"
}

resource "aws_cloudwatch_log_group" "ecs_playbook_operator_logs" {
  name = "${var.deployment_name}/playbook_operator_cluster"
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