# RDS + ElastiCache — off by default so `terraform apply` does not start billing databases.
# Set enable_managed_data = true after reviewing class sizes in terraform.tfvars.

resource "random_password" "rds" {
  count            = var.enable_managed_data ? 1 : 0
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}"
}

resource "random_password" "redis" {
  count   = var.enable_managed_data ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "jwt" {
  count   = var.enable_managed_data ? 1 : 0
  length  = 48
  special = false
}

resource "aws_db_subnet_group" "tor" {
  count      = var.enable_managed_data ? 1 : 0
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private_data[*].id
  tags       = { Name = "${local.name}-db" }
}

resource "aws_db_instance" "tor" {
  count                     = var.enable_managed_data ? 1 : 0
  identifier                = "${local.name}-pg"
  engine                    = "postgres"
  engine_version            = "16"
  instance_class            = var.db_instance_class
  allocated_storage         = 50
  max_allocated_storage     = 200
  db_name                   = "tor_app"
  username                  = "tor_user"
  password                  = random_password.rds[0].result
  db_subnet_group_name      = aws_db_subnet_group.tor[0].name
  vpc_security_group_ids    = [aws_security_group.rds.id]
  storage_encrypted         = true
  kms_key_id                = aws_kms_key.tor.arn
  multi_az                  = true
  publicly_accessible       = false
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-pg-final"
  backup_retention_period   = 7
  copy_tags_to_snapshot     = true
  apply_immediately         = false
}

resource "aws_elasticache_subnet_group" "tor" {
  count      = var.enable_managed_data ? 1 : 0
  name       = "${local.name}-redis"
  subnet_ids = aws_subnet.private_data[*].id
}

resource "aws_elasticache_replication_group" "tor" {
  count                      = var.enable_managed_data ? 1 : 0
  replication_group_id       = "${local.name}-redis"
  description                = "TOR session and LLM queue"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis[0].result
  kms_key_id                 = aws_kms_key.tor.arn
  subnet_group_name          = aws_elasticache_subnet_group.tor[0].name
  security_group_ids         = [aws_security_group.redis.id]
  snapshot_retention_limit   = 3
}

resource "aws_secretsmanager_secret_version" "rds" {
  count     = var.enable_managed_data ? 1 : 0
  secret_id = aws_secretsmanager_secret.rds.id
  secret_string = jsonencode({
    host     = aws_db_instance.tor[0].address
    port     = aws_db_instance.tor[0].port
    username = aws_db_instance.tor[0].username
    password = random_password.rds[0].result
    dbname   = aws_db_instance.tor[0].db_name
  })
}

resource "aws_secretsmanager_secret_version" "redis" {
  count     = var.enable_managed_data ? 1 : 0
  secret_id = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({
    host       = aws_elasticache_replication_group.tor[0].primary_endpoint_address
    port       = 6379
    auth_token = random_password.redis[0].result
  })
}

resource "aws_secretsmanager_secret_version" "jwt" {
  count     = var.enable_managed_data ? 1 : 0
  secret_id = aws_secretsmanager_secret.jwt.id
  secret_string = jsonencode({
    jwt_secret = random_password.jwt[0].result
  })
}
