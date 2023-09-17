# acm.tf

resource "aws_acm_certificate" "api_gateway_cert" {
  count             = var.enable_domain_name ? 1 : 0
  domain_name       = "*.${var.domain_name}"
  validation_method = "DNS"

  tags = {
    deployment_name = "${var.deployment_name}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "api_gateway_cert" {
  count                   = var.enable_domain_name ? 1 : 0
  certificate_arn         = aws_acm_certificate.api_gateway_cert[count.index].arn
  validation_record_fqdns = [aws_route53_record.deployment_api_cert_validation[count.index].fqdn]
}