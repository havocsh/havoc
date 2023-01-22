# route53.tf

resource "aws_route53_record" "deployment_api_cert_validation" {
  count           = var.enable_domain_name ? 1 : 0
  allow_overwrite = true
  name            = tolist(aws_acm_certificate.api_gateway_cert[count.index].domain_validation_options)[0].resource_record_name
  records         = [tolist(aws_acm_certificate.api_gateway_cert[count.index].domain_validation_options)[0].resource_record_value]
  ttl             = 60
  type            = tolist(aws_acm_certificate.api_gateway_cert[count.index].domain_validation_options)[0].resource_record_type
  zone_id         = var.hosted_zone
}

resource "aws_route53_record" "deployment_api_record" {
  count   = var.enable_domain_name ? 1 : 0
  name    = "${var.deployment_name}-api.${var.domain_name}"
  type    = "A"
  zone_id = var.hosted_zone

  alias {
    evaluate_target_health = true
    name                   = aws_api_gateway_domain_name.rest_api[count.index].regional_domain_name
    zone_id                = aws_api_gateway_domain_name.rest_api[count.index].regional_zone_id
  }
}
