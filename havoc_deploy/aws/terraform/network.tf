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
