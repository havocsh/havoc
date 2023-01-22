# api_gateway.tf

resource "aws_api_gateway_rest_api" "rest_api" {
  name        = "${var.deployment_name}-rest-api"
  description = "The ./HAVOC deployment REST API"
}

resource "aws_api_gateway_deployment" "rest_api" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  depends_on = [
    aws_api_gateway_method.manage_post,
    aws_api_gateway_method.remote_task_post,
    aws_api_gateway_method.task_control_post,
    aws_api_gateway_integration.manage_lambda_integration,
    aws_api_gateway_integration.remote_task_lambda_integration,
    aws_api_gateway_integration.task_control_lambda_integration
  ]

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.rest_api.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "primary_stage" {
  deployment_id = aws_api_gateway_deployment.rest_api.id
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  stage_name    = "havoc"
}

resource "aws_api_gateway_domain_name" "rest_api" {
  count                    = var.enable_domain_name ? 1 : 0
  domain_name              = "${var.deployment_name}-api.${var.domain_name}"
  regional_certificate_arn = aws_acm_certificate_validation.api_gateway_cert[count.index].certificate_arn

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_base_path_mapping" "rest_api" {
  count       = var.enable_domain_name ? 1 : 0
  api_id      = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_stage.primary_stage.stage_name
  domain_name = aws_api_gateway_domain_name.rest_api[count.index].domain_name
}

resource "aws_api_gateway_authorizer" "authorizer" {
  type                   = "REQUEST"
  name                   = "${var.deployment_name}-authorizer"
  rest_api_id            = aws_api_gateway_rest_api.rest_api.id
  authorizer_uri         = aws_lambda_function.authorizer.invoke_arn
  authorizer_credentials = aws_iam_role.api_gateway_role.arn
  identity_source        = "method.request.header.x-api-key,method.request.header.x-signature,method.request.header.x-sig-date"
}

resource "aws_api_gateway_resource" "manage_resource" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  parent_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  path_part   = "manage"
}

resource "aws_api_gateway_resource" "remote_task_resource" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  parent_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  path_part   = "remote-task"
}

resource "aws_api_gateway_resource" "task_control_resource" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  parent_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  path_part   = "task-control"
}

resource "aws_api_gateway_method" "manage_post" {
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  resource_id   = aws_api_gateway_resource.manage_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.authorizer.id

  request_parameters = {
    "method.request.header.x-api-key" = true
    "method.request.header.x-signature" = true
    "method.request.header.x-sig-date" = true
  }
}

resource "aws_api_gateway_method" "remote_task_post" {
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  resource_id   = aws_api_gateway_resource.remote_task_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.authorizer.id

  request_parameters = {
    "method.request.header.x-api-key" = true
    "method.request.header.x-signature" = true
    "method.request.header.x-sig-date" = true
  }
}

resource "aws_api_gateway_method" "task_control_post" {
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  resource_id   = aws_api_gateway_resource.task_control_resource.id
  http_method   = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.authorizer.id

  request_parameters = {
    "method.request.header.x-api-key" = true
    "method.request.header.x-signature" = true
    "method.request.header.x-sig-date" = true
  }
}

resource "aws_api_gateway_integration" "manage_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.rest_api.id
  resource_id             = aws_api_gateway_resource.manage_resource.id
  http_method             = aws_api_gateway_method.manage_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.manage.invoke_arn
}

resource "aws_api_gateway_integration" "remote_task_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.rest_api.id
  resource_id             = aws_api_gateway_resource.remote_task_resource.id
  http_method             = aws_api_gateway_method.remote_task_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.remote_task.invoke_arn
}

resource "aws_api_gateway_integration" "task_control_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.rest_api.id
  resource_id             = aws_api_gateway_resource.task_control_resource.id
  http_method             = aws_api_gateway_method.task_control_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.task_control.invoke_arn
}