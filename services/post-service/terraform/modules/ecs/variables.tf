variable "service_name" {
  type        = string
  description = "Base name for ECS resources"
}

variable "image" {
  type        = string
  description = "ECR image URI (with tag)"
}

variable "container_port" {
  type        = number
  description = "Port your app listens on"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets for FARGATE tasks"
}

variable "security_group_ids" {
  type        = list(string)
  description = "SGs for FARGATE tasks"
}

variable "execution_role_arn" {
  type        = string
  description = "ECS Task Execution Role ARN (Innovation Sandbox with ISBStudent=true tag)"
}

variable "task_role_arn" {
  type        = string
  description = "ECS Task Role ARN for application permissions (DynamoDB, SNS)"
  default     = ""
}

variable "log_group_name" {
  type        = string
  description = "CloudWatch log group name"
}

variable "target_group_arn" {
  type        = string
  description = "ALB target group ARN for load balancer integration"
}

variable "ecs_count" {
  type        = number
  default     = 1
  description = "Desired Fargate task count"
}

variable "region" {
  type        = string
  description = "AWS region (for awslogs driver)"
}

variable "cpu" {
  type        = string
  default     = "256"
  description = "vCPU units"
}

variable "memory" {
  type        = string
  default     = "1024"
  description = "Memory (MiB)"
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type        = list(object({
    name  = string
    value = string
  }))
  default = []
}

# Auto Scaling Variables
variable "min_capacity" {
  type        = number
  default     = 1
  description = "Minimum number of tasks"
}

variable "max_capacity" {
  type        = number
  default     = 10
  description = "Maximum number of tasks"
}

variable "cpu_target_value" {
  type        = number
  default     = 70.0
  description = "Target CPU utilization percentage for auto-scaling"
}

variable "memory_target_value" {
  type        = number
  default     = 80.0
  description = "Target memory utilization percentage for auto-scaling"
}

variable "scale_in_cooldown" {
  type        = number
  default     = 300
  description = "Cooldown period (in seconds) after a scale-in activity"
}

variable "scale_out_cooldown" {
  type        = number
  default     = 300
  description = "Cooldown period (in seconds) after a scale-out activity"
}

variable "enable_request_based_scaling" {
  type        = bool
  default     = false
  description = "Enable ALB request count based scaling"
}

variable "request_count_target_value" {
  type        = number
  default     = 1000
  description = "Target number of requests per target for auto-scaling"
}

variable "alb_resource_label" {
  type        = string
  default     = ""
  description = "ALB resource label for request-based scaling (format: loadbalancer/app/my-load-balancer/50dc6c495c0c9188/targetgroup/my-targets/73e2d6bc24d8a067)"
}

variable "service_connect_namespace_arn" {
  description = "ARN of the ECS Service Connect namespace for service discovery"
  type        = string
}
