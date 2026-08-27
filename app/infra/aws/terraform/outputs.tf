output "vpc_id" {
  value = aws_vpc.tor.id
}

output "private_app_subnet_ids" {
  value = aws_subnet.private_app[*].id
}

output "private_data_subnet_ids" {
  value = aws_subnet.private_data[*].id
}

output "ecr_backend" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend" {
  value = aws_ecr_repository.frontend.repository_url
}

output "s3_exports" {
  value = aws_s3_bucket.exports.bucket
}

output "s3_originals" {
  value = aws_s3_bucket.originals.bucket
}

output "s3_kb_source" {
  value = aws_s3_bucket.kb_source.bucket
}

output "kms_key_arn" {
  value = aws_kms_key.tor.arn
}

output "ecs_execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.task.arn
}

output "secret_arns" {
  value = {
    rds   = aws_secretsmanager_secret.rds.arn
    redis = aws_secretsmanager_secret.redis.arn
    jwt   = aws_secretsmanager_secret.jwt.arn
  }
}

output "alb_dns_name" {
  value       = try(aws_lb.tor[0].dns_name, null)
  description = "Point Route 53 / CloudFront origin here when enable_ecs is true"
}

output "rds_address" {
  value     = try(aws_db_instance.tor[0].address, null)
  sensitive = true
}

output "redis_primary" {
  value     = try(aws_elasticache_replication_group.tor[0].primary_endpoint_address, null)
  sensitive = true
}

output "ecs_cluster_name" {
  value = try(aws_ecs_cluster.tor[0].name, null)
}

output "github_deploy_role_arn" {
  value = try(aws_iam_role.github_deploy[0].arn, null)
}
