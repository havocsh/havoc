# lambdas.tf

resource "aws_lambda_function" "authorizer" {
  function_name    = "${var.deployment_name}-authorizer"
  filename         = "build/authorizer.zip"
  source_code_hash = "build/authorizer.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME = var.deployment_name
      API_DOMAIN_NAME = var.enable_domain_name ? "${var.deployment_name}-api.${var.domain_name}" : null
    }
  }
}

resource "aws_lambda_function" "manage" {
  function_name    = "${var.deployment_name}-manage"
  filename         = "build/manage.zip"
  source_code_hash = "build/manage.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME = var.deployment_name
      VPC_ID          = aws_vpc.deployment_vpc.id
      SUBNET          = aws_subnet.deployment_subnet.id
      SECURITY_GROUP  = aws_security_group.listener_lb_default.id
    }
  }
}

resource "aws_lambda_permission" "apigw_manage_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.manage.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_function" "remote_task" {
  function_name    = "${var.deployment_name}-remote-task"
  filename         = "build/remote_task.zip"
  source_code_hash = "build/remote_task.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME          = var.deployment_name
      RESULTS_QUEUE_EXPIRATION = var.results_queue_expiration
    }
  }
}

resource "aws_lambda_permission" "apigw_remote_task_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remote_task.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_function" "task_control" {
  function_name    = "${var.deployment_name}-task-control"
  filename         = "build/task_control.zip"
  source_code_hash = "build/task_control.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME = var.deployment_name
      SUBNET          = aws_subnet.deployment_subnet.id
      SECURITY_GROUP  = aws_security_group.tasks_default.id
    }
  }
}

resource "aws_lambda_permission" "apigw_task_control_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.task_control.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_function" "playbook_operator_control" {
  function_name    = "${var.deployment_name}-playbook-operator-control"
  filename         = "build/playbook_operator_control.zip"
  source_code_hash = "build/playbook_operator_control.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 300
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME = var.deployment_name
      SUBNET          = aws_subnet.deployment_subnet.id
    }
  }
}

resource "aws_lambda_permission" "apigw_playbook_operator_control_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.playbook_operator_control.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_function" "task_result" {
  function_name    = "${var.deployment_name}-task-result"
  filename         = "build/task_result.zip"
  source_code_hash = "build/task_result.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60

  role = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME          = var.deployment_name
      RESULTS_QUEUE_EXPIRATION = var.results_queue_expiration
    }
  }
}

resource "aws_lambda_permission" "cwlogs_task_result_lambda" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.task_result.function_name
  principal     = "logs.${var.aws_region}.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.ecs_task_logs.arn}:*"
}

resource "aws_lambda_function" "playbook_operator_result" {
  function_name    = "${var.deployment_name}-playbook-operator-result"
  filename         = "build/playbook_operator_result.zip"
  source_code_hash = "build/playbook_operator_result.zip.base64sha256"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      DEPLOYMENT_NAME          = var.deployment_name
      RESULTS_QUEUE_EXPIRATION = var.results_queue_expiration
    }
  }
}

resource "aws_lambda_permission" "cwlogs_playbook_operator_result_lambda" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.playbook_operator_result.function_name
  principal     = "logs.${var.aws_region}.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.ecs_playbook_operator_logs.arn}:*"
}