variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "aws_account_id" {
  description = "AWS Account ID (will be auto-detected if not provided)"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cs6650-project"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
}

# RDS Configuration
variable "rds_master_username" {
  description = "Master username for RDS PostgreSQL instance"
  type        = string
  default     = "postgres"
}

variable "rds_master_password" {
  description = "Master password for RDS PostgreSQL instance (must be at least 8 characters)"
  type        = string
  sensitive   = true
  # No default value - must be provided via environment variable or tfvars file
  
  validation {
    condition     = length(var.rds_master_password) >= 8
    error_message = "RDS master password must be at least 8 characters long to meet AWS requirements."
  }
}

variable "rds_instance_class" {
  description = "RDS PostgreSQL instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

# User Service Configuration
variable "user_service_database_name" {
  description = "Database name for user service"
  type        = string
  default     = "userdb"
}

variable "user_service_ecs_count" {
  description = "Number of ECS tasks for user service"
  type        = number
  default     = 2
}

variable "user_service_min_capacity" {
  description = "Minimum number of tasks for user service auto-scaling"
  type        = number
  default     = 1
}

variable "user_service_max_capacity" {
  description = "Maximum number of tasks for user service auto-scaling"
  type        = number
  default     = 10
}

variable "user_service_cpu_target_value" {
  description = "Target CPU utilization percentage for user service scaling"
  type        = number
  default     = 70
}

variable "user_service_memory_target_value" {
  description = "Target memory utilization percentage for user service scaling"
  type        = number
  default     = 80
}

variable "user_service_enable_request_based_scaling" {
  description = "Enable request-based auto-scaling for user service"
  type        = bool
  default     = true
}

variable "user_service_request_count_target_value" {
  description = "Target request count per task for user service scaling"
  type        = number
  default     = 1000
}

# Web Service Configuration
variable "web_service_ecs_count" {
  description = "Number of ECS tasks for web service"
  type        = number
  default     = 3
}

variable "web_service_user_service_url" {
  description = "URL of the user service for web service to connect to"
  type        = string
  default     = "http://user-service:8080"
}

variable "web_service_min_capacity" {
  description = "Minimum number of tasks for web service auto-scaling"
  type        = number
  default     = 1
}

variable "web_service_max_capacity" {
  description = "Maximum number of tasks for web service auto-scaling"
  type        = number
  default     = 99
}

variable "web_service_cpu_target_value" {
  description = "Target CPU utilization percentage for web service scaling"
  type        = number
  default     = 70
}

variable "web_service_memory_target_value" {
  description = "Target memory utilization percentage for web service scaling"
  type        = number
  default     = 80
}

variable "web_service_enable_request_based_scaling" {
  description = "Enable request-based auto-scaling for web service"
  type        = bool
  default     = true
}

variable "web_service_request_count_target_value" {
  description = "Target request count per task for web service scaling"
  type        = number
  default     = 1000
}

# Timeline Service Configuration
variable "timeline_service_ecs_count" {
  description = "Number of ECS tasks for timeline service"
  type        = number
  default     = 3
}

variable "timeline_service_fanout_strategy" {
  description = "Timeline fanout strategy: push, pull, or hybrid"
  type        = string
  default     = "hybrid"
}

variable "timeline_service_celebrity_threshold" {
  description = "Follower count threshold for hybrid strategy (P99 ~1200 for 1500 users)"
  type        = number
  default     = 1200
}

variable "timeline_service_enable_pitr" {
  description = "Enable Point-In-Time Recovery for DynamoDB"
  type        = bool
  default     = false
}

variable "timeline_service_min_capacity" {
  description = "Minimum number of tasks for timeline service auto-scaling"
  type        = number
  default     = 1
}

variable "timeline_service_max_capacity" {
  description = "Maximum number of tasks for timeline service auto-scaling"
  type        = number
  default     = 10
}

variable "timeline_service_cpu_target_value" {
  description = "Target CPU utilization percentage for timeline service scaling"
  type        = number
  default     = 70
}

variable "timeline_service_memory_target_value" {
  description = "Target memory utilization percentage for timeline service scaling"
  type        = number
  default     = 80
}

variable "timeline_service_enable_request_based_scaling" {
  description = "Enable request-based auto-scaling for timeline service"
  type        = bool
  default     = true
}

variable "timeline_service_request_count_target_value" {
  description = "Target request count per task for timeline service scaling"
  type        = number
  default     = 1000
}

variable "timeline_service_ecs_desired_count" {
  description = "Desired number of ECS tasks for timeline service"
  type        = number
  default     = 1
}

# Post Service Configuration
variable "post_service_ecs_count" {
  description = "Number of ECS tasks for post service"
  type        = number
  default     = 1
}

variable "post_service_post_strategy" {
  description = "Post strategy: push, pull, or hybrid"
  type        = string
  default     = "hybrid"
}


variable "post_service_hybrid_threshold" {
  description = "Threshold for hybrid strategy (must match timeline_service_celebrity_threshold)"
  type        = number
  default     = 1200
}

variable "post_service_min_capacity" {
  description = "Minimum number of tasks for post service auto-scaling"
  type        = number
  default     = 1
}

variable "post_service_max_capacity" {
  description = "Maximum number of tasks for post service auto-scaling"
  type        = number
  default     = 10
}

variable "post_service_cpu_target_value" {
  description = "Target CPU utilization percentage for post service scaling"
  type        = number
  default     = 70
}

variable "post_service_memory_target_value" {
  description = "Target memory utilization percentage for post service scaling"
  type        = number
  default     = 80
}

variable "post_service_enable_request_based_scaling" {
  description = "Enable request-based auto-scaling for post service"
  type        = bool
  default     = true
}

variable "post_service_request_count_target_value" {
  description = "Target request count per task for post service scaling"
  type        = number
  default     = 1000
}

variable "post_service_ecs_desired_count" {
  description = "Desired number of ECS tasks for post service"
  type        = number
  default     = 1
}


# Social Graph Service Configuration
variable "social_graph_service_ecs_count" {
  description = "Number of ECS tasks for social graph service"
  type        = number
  default     = 2
}

variable "social_graph_service_min_capacity" {
  description = "Minimum number of tasks for social graph service auto-scaling"
  type        = number
  default     = 1
}

variable "social_graph_service_max_capacity" {
  description = "Maximum number of tasks for social graph service auto-scaling"
  type        = number
  default     = 10
}

variable "social_graph_service_cpu_target_value" {
  description = "Target CPU utilization percentage for social graph service scaling"
  type        = number
  default     = 70
}

variable "social_graph_service_memory_target_value" {
  description = "Target memory utilization percentage for social graph service scaling"
  type        = number
  default     = 80
}

variable "social_graph_service_enable_request_based_scaling" {
  description = "Enable request-based auto-scaling for social graph service"
  type        = bool
  default     = true
}

variable "social_graph_service_request_count_target_value" {
  description = "Target request count per task for social graph service scaling"
  type        = number
  default     = 1000
}