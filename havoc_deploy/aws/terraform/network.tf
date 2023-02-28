# network.tf

resource "aws_vpc" "deployment_vpc" {
  cidr_block = "172.16.0.0/16"

  tags = {
    Name = var.deployment_name
  }
}

resource "aws_subnet" "deployment_subnet" {
  vpc_id            = aws_vpc.deployment_vpc.id
  cidr_block        = "172.16.10.0/24"

  tags = {
    Name = var.deployment_name
  }
}

resource "aws_security_group" "listener_lb_default" {
  name        = "${var.deployment_name}-listener-lb-default"
  description = "Allow traffic from LB to ECS"
  vpc_id      = aws_vpc.deployment_vpc.id

  tags = {
    Name = var.deployment_name
  }
}

resource "aws_security_group" "tasks_default" {
  name        = "${var.deployment_name}-tasks-default"
  description = "Allow traffic from LB to ECS"
  vpc_id      = aws_vpc.deployment_vpc.id

  tags = {
    Name = var.deployment_name
  }
}

resource "aws_vpc_security_group_ingress_rule" "tasks_ingress" {
  security_group_id = aws_security_group.tasks_default.id

  referenced_security_group_id = aws_security_group.listener_lb_default.id
  ip_protocol                  = "-1"
}

resource "aws_vpc_security_group_egress_rule" "tasks_egress" {
  security_group_id = aws_security_group.tasks_default.id

  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "-1"
}

# Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.deployment_vpc.id
}

# Route the subnet traffic through the IGW
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.deployment_vpc.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}
