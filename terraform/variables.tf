# Terraform variables for Meridian deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "meridian"
}

variable "api_image_tag" {
  description = "Docker image tag for API service"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for Frontend service"
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  description = "Desired number of API container instances"
  type        = number
  default     = 2
}

variable "neo4j_uri" {
  description = "Neo4j database URI"
  type        = string
  default     = "bolt://localhost:7688"
}

variable "neo4j_user" {
  description = "Neo4j database username"
  type        = string
  default     = "neo4j"
}

variable "neo4j_password" {
  description = "Neo4j database password"
  type        = string
  sensitive   = true
}

variable "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers"
  type        = string
  default     = "localhost:9092"
}

variable "jwt_secret_key" {
  description = "JWT signing secret key (REQUIRED - generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))')"
  type        = string
  sensitive   = true
  # No default — Terraform will fail-fast if not provided.

  validation {
    condition     = length(var.jwt_secret_key) >= 32
    error_message = "jwt_secret_key must be at least 32 characters long."
  }
}
