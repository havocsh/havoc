# s3.tf

resource "aws_s3_bucket" "playbooks" {
  bucket = "${var.deployment_name}-playbooks"

  tags = {
    Name = "${var.deployment_name}-playbooks"
  }
}

resource "aws_s3_bucket_acl" "playbooks" {
  bucket = aws_s3_bucket.playbooks.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "playbooks" {
  bucket                  = aws_s3_bucket.playbooks.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "playbook_types" {
  bucket = "${var.deployment_name}-playbook-types"

  tags = {
    Name = "${var.deployment_name}-playbook-types"
  }
}

resource "aws_s3_bucket_acl" "playbook_types" {
  bucket = aws_s3_bucket.playbook_types.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "playbook_types" {
  bucket                  = aws_s3_bucket.playbook_types.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "conti_ransomware_playbook_template" {
  bucket = aws_s3_bucket.playbook_types.id
  key    = "conti_ransomware.template"
  source = "havoc_deploy/aws/terraform/build/conti_ransomware.template"
}

resource "aws_s3_bucket" "workspace" {
  bucket = "${var.deployment_name}-workspace"

  tags = {
    Name = "${var.deployment_name}-workspace"
  }
}

resource "aws_s3_bucket_acl" "workspace" {
  bucket = aws_s3_bucket.workspace.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "workspace" {
  bucket                  = aws_s3_bucket.workspace.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.deployment_name}-terraform-state"

  tags = {
    Name = "${var.deployment_name}-terraform-state"
  }
}

resource "aws_s3_bucket_acl" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}