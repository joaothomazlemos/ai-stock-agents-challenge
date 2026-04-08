variable "aws_region" {
  description = "AWS region for all resources. Must support both Bedrock and AgentCore."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used as prefix for all AWS resource names."
  type        = string
  default     = "ai-stock-agent"

  validation {
    condition     = can(regex("^[a-z0-9-]{1,20}$", var.project_name))
    error_message = "project_name must be lowercase alphanumeric with hyphens, max 20 characters."
  }
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for the chat LLM."
  type        = string
  default     = "us.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "embedding_model_id" {
  description = "Bedrock model ID for text embeddings."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dims" {
  description = "Embedding vector dimensions for the embedding model."
  type        = number
  default     = 512
}

variable "langfuse_public_key" {
  description = "Langfuse public API key for observability. Leave empty to disable tracing."
  type        = string
  default     = ""
}

variable "langfuse_secret_key" {
  description = "Langfuse secret API key for observability."
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_host" {
  description = "Langfuse Cloud base URL."
  type        = string
  default     = "https://cloud.langfuse.com"
}

variable "container_image_tag" {
  description = "Docker image tag to deploy to the AgentCore Runtime."
  type        = string
  default     = "latest"
}
