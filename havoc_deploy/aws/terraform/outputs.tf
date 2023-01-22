# outputs.tf

output "DEPLOYMENT_NAME" {
  value = var.deployment_name
}

output "DEPLOYMENT_VERSION" {
  value = var.deployment_version
}

output "DEPLOYMENT_ADMIN_EMAIL" {
  value = var.deployment_admin_email
}

output "RESULTS_QUEUE_EXPIRATION" {
  value = var.results_queue_expiration
}

output "API_DOMAIN_NAME" {
  value = var.enable_domain_name ? "${var.deployment_name}-api.${var.domain_name}" : "${aws_api_gateway_rest_api.rest_api.id}.execute-api.${var.aws_region}.amazonaws.com"
}

output "API_REGION" {
  value = var.aws_region
}

output "TERRAFORM_STATE_S3_BUCKET" {
  value = aws_s3_bucket.terraform_state.id
}

output "TERRAFORM_STATE_DYNAMODB_TABLE" {
  value = aws_dynamodb_table.terraform_locks.id
}

output "API_KEY" {
  value = random_string.api_key.id
}

output "SECRET" {
  value = random_string.secret.id
}
