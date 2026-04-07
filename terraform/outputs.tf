output "runtime_endpoint_arn" {
  description = "ARN of the AgentCore Runtime Endpoint for SDK invocations."
  value       = module.agentcore.endpoint_arns["ai_stock_agent"]
}

output "gateway_url" {
  description = "URL of the AgentCore Gateway (CUSTOM_JWT authenticated)."
  value       = module.agentcore.gateway_urls["agent-gateway"]
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID for authentication."
  value       = aws_cognito_user_pool.this.id
}

output "cognito_client_id" {
  description = "Cognito App Client ID for authentication flows."
  value       = aws_cognito_user_pool_client.this.id
}

output "cognito_issuer_url" {
  description = "Cognito OIDC issuer URL used by the Gateway CUSTOM_JWT authorizer."
  value       = local.cognito_issuer_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images."
  value       = aws_ecr_repository.this.repository_url
}

output "memory_arn" {
  description = "ARN of the AgentCore Memory resource for AgentCoreMemorySaver."
  value       = module.agentcore.memory_arns["agent_memory"]
}
