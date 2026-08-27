variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "project" {
  type    = string
  default = "tor"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "bucket_prefix" {
  type        = string
  description = "Globally unique prefix for S3 buckets"
}

variable "github_org_repo" {
  type        = string
  default     = ""
  description = "Optional org/repo for OIDC deploy role, e.g. chiraleo2000/tor-generator"
}

variable "enable_managed_data" {
  type        = bool
  default     = false
  description = "Create RDS PostgreSQL 16 + ElastiCache Redis (bills monthly). Leave false until tfvars is reviewed."
}

variable "enable_ecs" {
  type        = bool
  default     = false
  description = "Create ECS cluster, ALB, Cloud Map, and services. Requires enable_managed_data and certificate_arn."
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t3.small"
}

variable "certificate_arn" {
  type        = string
  default     = ""
  description = "ACM certificate in the same region as the ALB (required when enable_ecs)"
}

variable "app_domain" {
  type        = string
  default     = "tor.example.go.th"
  description = "Public hostname for CORS / Host header (ALB HTTPS listener)"
}

variable "backend_desired_count" {
  type        = number
  default     = 1
  description = "Keep 1 until draft jobs leave in-process memory (see Discussions/27)"
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}
