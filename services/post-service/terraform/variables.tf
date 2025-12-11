# Region to deploy into
variable "aws_region" {
  type    = string
  default = "us-west-2"
}

# Shared infrastructure values (passed from root terraform)
variable "vpc_id" {
  description = "VPC ID from shared infrastructure"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block from shared infrastructure"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs from shared infrastructure"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs from shared infrastructure"
  type        = list(string)
}

variable "alb_listener_arn" {
  description = "ALB listener ARN from shared infrastructure"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix from shared infrastructure"
  type        = string
}

variable "service_connect_namespace_arn" {
  description = "ARN of the ECS Service Connect namespace for service discovery"
  type        = string
}

# ECR & ECS settings
variable "ecr_repository_name" {
  type    = string
  default = "post-service"
}

variable "service_name" {
  type    = string
  default = "post-service"
}

variable "container_port" {
  type    = number
  default = 8083
}

variable "ecs_count" {
  type    = number
  default = 2
}

# IAM Role for ECS Task Execution (Innovation Sandbox with ISBStudent tag)
variable "execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task role for application permissions"
  type        = string
  default     = ""
}

# ALB settings
variable "alb_priority" {
  description = "Priority for ALB listener rule"
  type        = number
  default     = 300
}

# How long to keep logs
variable "log_retention_days" {
  type    = number
  default = 7
}

# SNS/SQS configuration
variable "environment" {
  type    = string
  default = "dev"
}

# Application configuration
variable "post_strategy" {
  description = "Post strategy: 'push', 'pull', or 'hybrid'"
  type        = string
  default     = "hybrid"
}

variable "dynamo_table" {
  description = "DynamoDB table name for posts"
  type        = string
  default     = "posts-table"
}

variable "social_graph_url" {
  description = "Social graph service URL (gRPC endpoint)"
  type        = string
  default     = "social-graph-service-grpc:50052"
}

variable "hybrid_threshold" {
  description = "Threshold for hybrid strategy"
  type        = number
  default     = 50000
}

# SNS Topic ARN (optional, can be created by this module or passed in)
variable "sns_topic_arn" {
  description = "SNS topic ARN (optional, will create if not provided)"
  type        = string
  default     = ""
}

# Auto-scaling configuration
variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "cpu_target_value" {
  description = "Target CPU utilization percentage for scaling"
  type        = number
  default     = 70.0
}

variable "memory_target_value" {
  description = "Target memory utilization percentage for scaling"
  type        = number
  default     = 80.0
}

variable "enable_request_based_scaling" {
  description = "Enable ALB request count based scaling"
  type        = bool
  default     = false
}

variable "request_count_target_value" {
  description = "Target requests per minute per task for scaling"
  type        = number
  default     = 1000
}
