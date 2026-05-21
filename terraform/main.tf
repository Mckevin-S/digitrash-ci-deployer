# ==================== TERRAFORM CONFIGURATION ====================
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ==================== PROVIDER ====================
provider "aws" {
  region = "af-south-1"
}

# ==================== VARIABLES ====================
variable "app_name" {
  default = "digitrans-bi"
}

# ==================== DATA SOURCES ====================
data "aws_availability_zones" "available" {}

# ==================== VPC ====================
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = {
    Name = "${var.app_name}-vpc"
  }
}

# ==================== SUBNETS ====================
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.app_name}-subnet-${count.index}"
  }
}

# ==================== INTERNET GATEWAY ====================
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "${var.app_name}-igw"
  }
}

# ==================== ROUTE TABLE ====================
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ==================== SECURITY GROUP ====================
resource "aws_security_group" "app" {
  name        = "${var.app_name}-sg"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "${var.app_name}-sg"
  }
}

# ==================== ECR REPOSITORY ====================
resource "aws_ecr_repository" "app" {
  name = var.app_name
  tags = {
    Name = var.app_name
  }
}

# ==================== ECS CLUSTER ====================
resource "aws_ecs_cluster" "main" {
  name = var.app_name
}

# ==================== IAM ROLE FOR ECS ====================
resource "aws_iam_role" "ecs_execution" {
  name = "${var.app_name}-ecs-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ==================== CLOUDWATCH LOG GROUP ====================
resource "aws_cloudwatch_log_group" "app" {
  name = "/ecs/${var.app_name}"
}

# ==================== ECS TASK DEFINITION ====================
resource "aws_ecs_task_definition" "app" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  container_definitions = jsonencode([
    {
      name  = var.app_name
      image = "${aws_ecr_repository.app.repository_url}:latest"
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 5000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = "af-south-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ==================== ECS SERVICE ====================
resource "aws_ecs_service" "app" {
  name            = var.app_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_execution
  ]
}

# ==================== OUTPUTS ====================
output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "app_url" {
  value = "http://${aws_ecs_service.app.name}"
}

output "update_service_command" {
  value = "aws ecs update-service --cluster ${var.app_name} --service ${var.app_name} --force-new-deployment --region af-south-1"
}