# ecs.tf

resource "aws_ecs_cluster" "task_cluster" {
  name = "${var.deployment_name}-task-cluster"
}

resource "aws_ecs_cluster" "playbook_operator_cluster" {
  name = "${var.deployment_name}-playbook-operator-cluster"
}

data "template_file" "nmap_task_definition" {
  template = file("templates/nmap_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "nmap" {
  family                   = "${var.deployment_name}-nmap"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.nmap_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-nmap"
    task_version       = var.deployment_version
  }
}

data "template_file" "metasploit_task_definition" {
  template = file("templates/metasploit_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "metasploit" {
  family                   = "${var.deployment_name}-metasploit"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.metasploit_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 2048
  memory                   = 8192
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-metasploit"
    task_version       = var.deployment_version
  }
}

data "template_file" "powershell_empire_task_definition" {
  template = file("templates/powershell_empire_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "powershell_empire" {
  family                   = "${var.deployment_name}-powershell_empire"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.powershell_empire_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 4096
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-powershell_empire"
    task_version = var.deployment_version
  }
}

data "template_file" "http_server_task_definition" {
  template = file("templates/http_server_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "http_server" {
  family                   = "${var.deployment_name}-http_server"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.http_server_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 4096
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-http_server"
    task_version       = var.deployment_version
  }
}

data "template_file" "trainman_task_definition" {
  template = file("templates/trainman_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "trainman" {
  family                   = "${var.deployment_name}-trainman"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.trainman_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 4096
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-trainman"
    task_version       = var.deployment_version
  }
}

data "template_file" "exfilkit_task_definition" {
  template = file("templates/exfilkit_task_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "exfilkit" {
  family                   = "${var.deployment_name}-exfilkit"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.exfilkit_task_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 4096
  tags                     = {
    deployment_name    = var.deployment_name
    name               = "${var.deployment_name}-exfilkit"
    task_version       = var.deployment_version
  }
}

data "template_file" "playbook_operator_definition" {
  template = file("templates/playbook_operator_definition.template")

  vars = {
    deployment_version = var.deployment_version
    deployment_name    = var.deployment_name
    aws_region         = var.aws_region
  }
}

resource "aws_ecs_task_definition" "playbook_operator" {
  family                   = "${var.deployment_name}-playbook_operator"
  execution_role_arn       = aws_iam_role.ecs_playbook_operator_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_playbook_operator_role.arn
  network_mode             = "awsvpc"
  container_definitions    = data.template_file.playbook_operator_definition.rendered
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 4096
  tags                     = {
    deployment_name           = var.deployment_name
    name                      = "${var.deployment_name}-playbook_operator"
    playbook_operator_version = var.deployment_version
  }
}