terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Create IAM Role with Bedrock access
resource "aws_iam_role" "bedrock_access" {
  name               = var.iam_role_name
  assume_role_policy = templatefile("${path.module}/templates/trust-policy.json.tpl", {
    account_id = data.aws_caller_identity.current.account_id
  })
}

# Attach Bedrock Full Access policy
resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.bedrock_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# Create IAM User
resource "aws_iam_user" "travel_bot" {
  name = var.iam_user_name
}

# Create Access Keys
resource "aws_iam_access_key" "travel_bot" {
  user = aws_iam_user.travel_bot.name
}

# Output the credentials and role ARN
output "iam_user_access_key_id" {
  value = aws_iam_access_key.travel_bot.id
  sensitive = true
}

output "iam_user_secret_access_key" {
  value = aws_iam_access_key.travel_bot.secret
  sensitive = true
}

output "iam_role_arn" {
  value = aws_iam_role.bedrock_access.arn
}

# Get AWS Account ID
data "aws_caller_identity" "current" {}
