data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "runtime_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  name               = "${var.project_name}-runtime"
  assume_role_policy = data.aws_iam_policy_document.runtime_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "runtime_policy" {
  statement {
    sid    = "AllowBedrockModelInvocation"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowAgentCoreMemory"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:CreateEvent",
      "bedrock-agentcore:ListEvents",
      "bedrock-agentcore:RetrieveMemories",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowECRPull"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock/agentcore/*"]
  }

  statement {
    sid    = "AllowXRayTracing"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowWorkloadIdentityToken"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:GetWorkloadIdentityToken",
      "bedrock-agentcore:RefreshWorkloadIdentityToken",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "${var.project_name}-runtime-policy"
  role   = aws_iam_role.runtime.name
  policy = data.aws_iam_policy_document.runtime_policy.json
}
