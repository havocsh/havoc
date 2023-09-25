# variables.tf

variable "aws_region" {
  description = "The AWS region things are created in."
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "The AWS profile to be used by Terraform."
  default     = "default"
}

# This value will be used in the name of several S3 buckets so it must be DNS compliant (https://datatracker.ietf.org/doc/html/rfc952).
variable "deployment_name" {
  description = "The name used for naming AWS resources associated for your ./HAVOC deployment."
}

variable "deployment_version" {
  description = "The deployment version for your ./HAVOC deployment."
}

variable "enable_domain_name" {
  description = "If set to true, the ./HAVOC API endpoint will be deployed with a friendly DNS name as defined by the hosted_zone and domain_name variables."
  type        = bool
}

variable "hosted_zone" {
  description = "The ID of the hosted zone from which your ./HAVOC API endpoint will derive its DNS name."
  default     = null
}

variable "domain_name" {
  description = "The domain name that will be assigned to your ./HAVOC API, i.e. example.com."
  default     = null
}

variable "enable_task_results_logging" {
  description = "If set to true, successful task requests/responses will be logged to CloudWatch Logs."
  type        = bool
}

variable "enable_playbook_results_logging" {
  description = "If set to true, playbook operations will be logged to CloudWatch Logs."
  type        = bool
}

variable "deployment_admin_email" {
  description = "The email address that will be referenced as the deployment admin."
}

variable "results_queue_expiration" {
  description = "The number of days to keep task results in the queue."
  default     = 30
}