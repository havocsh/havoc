# s3.tf

resource "aws_s3_bucket" "playbooks" {
  bucket = "${var.deployment_name}-playbooks"

  tags = {
    Name = "${var.deployment_name}-playbooks"
  }
}

resource "aws_s3_bucket" "playbook_types" {
  bucket = "${var.deployment_name}-playbook-types"

  tags = {
    Name = "${var.deployment_name}-playbook-types"
  }
}

resource "aws_s3_object" "conti_ransomware_playbook_template" {
  bucket = aws_s3_bucket.playbook_types.id
  key    = "conti_ransomware.template"
  source = "build/conti_ransomware.template"
  etag = filemd5("build/conti_ransomware.template")
}

resource "aws_s3_bucket" "workspace" {
  bucket = "${var.deployment_name}-workspace"

  tags = {
    Name = "${var.deployment_name}-workspace"
  }
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.deployment_name}-terraform-state"

  tags = {
    Name = "${var.deployment_name}-terraform-state"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  depends_on = [aws_s3_bucket_versioning.terraform_state]

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}