locals {
  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  cognito_issuer_url = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  runtime_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-runtime"
}

module "agentcore" {
  source  = "aws-ia/agentcore/aws"
  version = "~> 1.0"

  project_prefix = var.project_name

  runtimes = {
    ai_stock_agent = {
      source_type          = "CONTAINER"
      container_image_uri  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}:${var.container_image_tag}"
      execution_role_arn   = local.runtime_role_arn
      description          = "AI Stock Agent — LangGraph ReAct agent with yfinance and RAG tools"
      create_endpoint      = true
      endpoint_description = "Invocation endpoint for the AI Stock Agent runtime"

      environment_variables = {
        AWS_REGION          = var.aws_region
        BEDROCK_MODEL_ID    = var.bedrock_model_id
        EMBEDDING_MODEL_ID  = var.embedding_model_id
        EMBEDDING_DIMS      = tostring(var.embedding_dims)
        AGENTCORE_MEMORY_ID = module.agentcore.memory_arns["agent_memory"]
        LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
        LANGFUSE_SECRET_KEY = var.langfuse_secret_key
        LANGFUSE_HOST       = var.langfuse_host
      }
    }
  }

  depends_on = [aws_iam_role.runtime, aws_iam_role_policy.runtime]

  memories = {
    agent_memory = {
      description           = "Conversation memory for AI Stock Agent"
      event_expiry_duration = 90

      strategies = [{
        semantic_memory_strategy = {
          name        = "conversation_context"
          description = "Persist conversation context across sessions"
          namespaces  = ["/strategies/{memoryStrategyId}/actors/{actorId}"]
        }
      }]
    }
  }

  gateways = {
    agent-gateway = {
      description     = "JWT-authenticated gateway for AI Stock Agent"
      authorizer_type = "CUSTOM_JWT"
      protocol_type   = "MCP"

      authorizer_configuration = {
        custom_jwt_authorizer = {
          allowed_audience = [aws_cognito_user_pool_client.this.id]
          discovery_url    = local.cognito_issuer_url
        }
      }

      protocol_configuration = {
        mcp = {
          instructions       = "AI Stock Agent gateway for authenticated access"
          search_type        = "SEMANTIC"
          supported_versions = ["2025-11-25"]
        }
      }
    }
  }

  tags = local.tags
}
