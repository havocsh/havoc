# provider.tf

terraform {
  required_version = "> 0.13"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "> 3.0"
    }
  }
}

# Specify the provider and access details
provider "aws" {
  shared_credentials_files = ["$HOME/.aws/credentials"]
  profile                 = var.aws_profile
  region                  = var.aws_region
}