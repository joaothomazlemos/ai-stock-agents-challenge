terraform {
  required_version = ">= 1.14"

  backend "s3" {
    bucket       = "ai-stock-agent-tfstate"
    key          = "ai-stock-agent/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.18.0"
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = ">= 1.30.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "awscc" {
  region = var.aws_region
}
