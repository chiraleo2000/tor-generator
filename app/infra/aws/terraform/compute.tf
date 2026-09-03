# ECS + ALB — off until enable_managed_data and an ACM certificate are set.

resource "aws_service_discovery_private_dns_namespace" "tor" {
  count       = var.enable_ecs ? 1 : 0
  name        = "tor.local"
  description = "Internal names for Next.js → FastAPI"
  vpc         = aws_vpc.tor.id

  lifecycle {
    precondition {
      condition     = var.enable_managed_data && var.certificate_arn != ""
      error_message = "enable_ecs requires enable_managed_data = true and certificate_arn."
    }
  }
}

resource "aws_service_discovery_service" "backend" {
  count = var.enable_ecs ? 1 : 0
  name  = "backend"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.tor[0].id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_ecs_cluster" "tor" {
  count = var.enable_ecs ? 1 : 0
  name  = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_lb" "tor" {
  count              = var.enable_ecs ? 1 : 0
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  idle_timeout       = 900

  access_logs {
    bucket  = aws_s3_bucket.logs.id
    prefix  = "alb"
    enabled = true
  }
}

resource "aws_lb_target_group" "frontend" {
  count       = var.enable_ecs ? 1 : 0
  name        = "${local.name}-fe"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.tor.id
  target_type = "ip"

  health_check {
    path                = "/"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
}

resource "aws_lb_target_group" "backend" {
  count       = var.enable_ecs ? 1 : 0
  name        = "${local.name}-be"
  port        = 4000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.tor.id
  target_type = "ip"

  health_check {
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
}

resource "aws_lb_listener" "http_redirect" {
  count             = var.enable_ecs ? 1 : 0
  load_balancer_arn = aws_lb.tor[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = var.enable_ecs ? 1 : 0
  load_balancer_arn = aws_lb.tor[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend[0].arn
  }
}

resource "aws_lb_listener_rule" "api" {
  count        = var.enable_ecs ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend[0].arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/health", "/docs", "/openapi.json"]
    }
  }
}

resource "aws_ecs_task_definition" "backend" {
  count                    = var.enable_ecs ? 1 : 0
  family                   = "${local.name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name         = "backend"
      image        = "${aws_ecr_repository.backend.repository_url}:prod"
      essential    = true
      portMappings = [{ containerPort = 4000, protocol = "tcp" }]
      environment = [
        { name = "DEPLOYMENT_MODE", value = "cloud" },
        { name = "LLM_PROVIDER", value = "bedrock" },
        { name = "EMBEDDING_PROVIDER", value = "bedrock" },
        { name = "VECTOR_STORE_PROVIDER", value = "pgvector" },
        { name = "BEDROCK_REGION", value = var.aws_region },
        { name = "MINIO_ENDPOINT", value = "s3.${var.aws_region}.amazonaws.com" },
        { name = "MINIO_BUCKET", value = aws_s3_bucket.exports.bucket },
        { name = "MINIO_SECURE", value = "true" },
        { name = "MINIO_REGION", value = var.aws_region },
        { name = "MINIO_USE_IAM", value = "true" },
        { name = "REDIS_TLS", value = "true" },
        { name = "COOKIE_SECURE", value = "true" },
        { name = "MCP_RAG_ENABLED", value = "false" },
        { name = "CUSTOM_RAG_ENABLED", value = "false" },
        { name = "RAG_SOURCES", value = "both" },
        { name = "CLOUD_LLM_TIMEOUT", value = "300" },
        { name = "CORS_ORIGINS", value = "https://${var.app_domain}" },
        { name = "POSTGRES_PORT", value = "5432" },
        { name = "REDIS_PORT", value = "6379" },
      ]
      secrets = [
        { name = "POSTGRES_HOST", valueFrom = "${aws_secretsmanager_secret.rds.arn}:host::" },
        { name = "POSTGRES_PASSWORD", valueFrom = "${aws_secretsmanager_secret.rds.arn}:password::" },
        { name = "POSTGRES_USER", valueFrom = "${aws_secretsmanager_secret.rds.arn}:username::" },
        { name = "POSTGRES_DB", valueFrom = "${aws_secretsmanager_secret.rds.arn}:dbname::" },
        { name = "REDIS_HOST", valueFrom = "${aws_secretsmanager_secret.redis.arn}:host::" },
        { name = "REDIS_PASSWORD", valueFrom = "${aws_secretsmanager_secret.redis.arn}:auth_token::" },
        { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.jwt.arn}:jwt_secret::" },
        { name = "MCP_RAG_SERVERS_JSON", valueFrom = "${aws_secretsmanager_secret.mcp.arn}:MCP_RAG_SERVERS_JSON::" },
        { name = "MCP_RAG_AUTH_VALUE", valueFrom = "${aws_secretsmanager_secret.mcp.arn}:MCP_RAG_AUTH_VALUE::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:4000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_task_definition" "frontend" {
  count                    = var.enable_ecs ? 1 : 0
  family                   = "${local.name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name         = "frontend"
      image        = "${aws_ecr_repository.frontend.repository_url}:prod"
      essential    = true
      portMappings = [{ containerPort = 3000, protocol = "tcp" }]
      environment = [
        { name = "NEXT_PUBLIC_API_URL", value = "/api/v1" },
        { name = "BACKEND_INTERNAL_URL", value = "http://backend.tor.local:4000/api/v1" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  count           = var.enable_ecs ? 1 : 0
  name            = "backend"
  cluster         = aws_ecs_cluster.tor[0].id
  task_definition = aws_ecs_task_definition.backend[0].arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_app[*].id
    security_groups  = [aws_security_group.ecs_be.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend[0].arn
    container_name   = "backend"
    container_port   = 4000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend[0].arn
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_service" "frontend" {
  count           = var.enable_ecs ? 1 : 0
  name            = "frontend"
  cluster         = aws_ecs_cluster.tor[0].id
  task_definition = aws_ecs_task_definition.frontend[0].arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_app[*].id
    security_groups  = [aws_security_group.ecs_fe.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend[0].arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.https]
}
