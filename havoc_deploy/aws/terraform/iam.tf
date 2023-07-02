# iam.tf

data "template_file" "lambda_policy" {
  template = file("templates/lambda_policy.template")

  vars = {
  authorizer_table            = aws_dynamodb_table.authorizer.arn,
  authorizer_index            = "${aws_dynamodb_table.authorizer.arn}/index/${var.deployment_name}-ApiKeyIndex"
  task_types_table            = aws_dynamodb_table.task_types.arn,
  deployment_table            = aws_dynamodb_table.deployment.arn,
  domains_table               = aws_dynamodb_table.domains.arn,
  listeners_table             = aws_dynamodb_table.listeners.arn,
  playbook_queue_table        = aws_dynamodb_table.playbook_queue.arn,
  playbook_types_table        = aws_dynamodb_table.playbook_types.arn,
  playbooks_table             = aws_dynamodb_table.playbooks.arn,
  portgroups_table            = aws_dynamodb_table.portgroups.arn,
  task_queue_table            = aws_dynamodb_table.task_queue.arn,
  tasks_table                 = aws_dynamodb_table.tasks.arn,
  triggers_table              = aws_dynamodb_table.triggers.arn,
  trigger_queue_table         = aws_dynamodb_table.trigger_queue.arn,
  playbooks_bucket            = "${var.deployment_name}-playbooks",
  playbook_types_bucket       = "${var.deployment_name}-playbook-types",
  workspace_bucket            = "${var.deployment_name}-workspace",
  task_role                   = aws_iam_role.ecs_task_role.arn,
  task_exec_role              = aws_iam_role.ecs_task_execution_role.arn,
  playbook_operator_role      = aws_iam_role.ecs_playbook_operator_role.arn,
  playbook_operator_exec_role = aws_iam_role.ecs_playbook_operator_execution_role.arn,
  trigger_executor_role       = aws_iam_role.trigger_executor_role.arn
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.deployment_name}-lambda-role"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "lambda.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.deployment_name}-lambda-policy"
  path        = "/"
  description = "Policy for ./HAVOC Lambda functions"
  policy = data.template_file.lambda_policy.rendered
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

data "template_file" "ecs_task_policy" {
  template = file("templates/ecs_task_policy.template")

  vars = {
  deployment_name = var.deployment_name
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.deployment_name}-task-role"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

resource "aws_iam_policy" "ecs_task_policy" {
  name        = "${var.deployment_name}-ecs-task-policy"
  path        = "/"
  description = "Policy for ./HAVOC ECS tasks"
  policy = data.template_file.ecs_task_policy.rendered
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.deployment_name}-execution-role"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

data "aws_iam_policy" "ecs_task_execution_policy" {
  name = "AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy_attachment" {
  role = aws_iam_role.ecs_task_execution_role.name
  policy_arn = data.aws_iam_policy.ecs_task_execution_policy.arn
}

data "template_file" "ecs_playbook_operator_policy" {
  template = file("templates/ecs_playbook_operator_policy.template")

  vars = {
  deployment_name = var.deployment_name
  }
}

resource "aws_iam_role" "ecs_playbook_operator_role" {
  name = "${var.deployment_name}-playbook-operator-role"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

resource "aws_iam_policy" "ecs_playbook_operator_policy" {
  name        = "${var.deployment_name}-ecs-playbook-operator-policy"
  path        = "/"
  description = "Policy for ./HAVOC ECS playbook operator"
  policy = data.template_file.ecs_playbook_operator_policy.rendered
}

resource "aws_iam_role_policy_attachment" "ecs_playbook_operator_policy_attachment" {
  role = aws_iam_role.ecs_playbook_operator_role.name
  policy_arn = aws_iam_policy.ecs_playbook_operator_policy.arn
}

resource "aws_iam_role" "ecs_playbook_operator_execution_role" {
  name = "${var.deployment_name}-playbook-operator-execution-role"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

data "aws_iam_policy" "ecs_playbook_operator_execution_policy" {
  name = "AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_playbook_operator_execution_policy_attachment" {
  role = aws_iam_role.ecs_playbook_operator_execution_role.name
  policy_arn = data.aws_iam_policy.ecs_playbook_operator_execution_policy.arn
}

data "template_file" "trigger_executor_policy" {
  template = file("templates/trigger_executor_policy.template")

  vars = {
    authorizer_table      = aws_dynamodb_table.authorizer.arn,
    authorizer_index      = "${aws_dynamodb_table.authorizer.arn}/index/${var.deployment_name}-ApiKeyIndex"
    deployment_table      = aws_dynamodb_table.deployment.arn,
    trigger_queue_table   = aws_dynamodb_table.trigger_queue.arn
    trigger_executor_role = aws_iam_role.trigger_executor_role.arn
  }
}

resource "aws_iam_role" "trigger_executor_role" {
  name = "${var.deployment_name}-trigger-executor-role"
  path = "/"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
            "Service": "events.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
  ]
}
EOF
}

resource "aws_iam_policy" "trigger_executor_policy" {
  name        = "${var.deployment_name}-trigger-executor-policy"
  path        = "/"
  description = "Policy for ./HAVOC trigger_executor Lambda function"
  policy = data.template_file.trigger_executor_policy.rendered
}

resource "aws_iam_role_policy_attachment" "trigger_executor_policy_attachment" {
  role = aws_iam_role.trigger_executor_role.name
  policy_arn = aws_iam_policy.trigger_executor_policy.arn
}

data "template_file" "api_gateway_policy" {
  template = file("templates/api_gateway_policy.template")

  vars = {
  authorizer_arn = aws_lambda_function.authorizer.arn
  }
}

resource "aws_iam_role" "api_gateway_role" {
  name = "${var.deployment_name}-api-gateway-role"
  path = "/"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "api_gateway_policy" {
  name        = "${var.deployment_name}-api-gateway-policy"
  path        = "/"
  description = "Policy for ./HAVOC REST API gateway"
  policy = data.template_file.api_gateway_policy.rendered
}

resource "aws_iam_role_policy_attachment" "api_gateway_policy_attachment" {
  role = aws_iam_role.api_gateway_role.name
  policy_arn = aws_iam_policy.api_gateway_policy.arn
}