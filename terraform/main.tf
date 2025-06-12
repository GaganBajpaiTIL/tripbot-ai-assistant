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

# Data source to get current AWS account ID
data "aws_caller_identity" "current" {}

# IAM Role
resource "aws_iam_role" "bedrock_access" {
  name               = var.iam_role_name
  assume_role_policy = templatefile("${path.module}/templates/trust-policy.json.tpl", {
    YOUR_AWS_ACCOUNT_ID_PLACEHOLDER = data.aws_caller_identity.current.account_id
    IAM_USER_NAME_PLACEHOLDER = var.iam_user_name
  })
  
  tags = {
    Name    = var.iam_role_name
    Project = "TravelBot"
  }
}

# IAM Role logging - Creation
module "role_creation_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "IAM Role created"
    resource_type = "aws_iam_role"
    resource_name = aws_iam_role.bedrock_access.name
    resource_id   = aws_iam_role.bedrock_access.id
    resource_arn  = aws_iam_role.bedrock_access.arn
    resource_attributes = jsonencode({
      assume_role_policy = jsondecode(aws_iam_role.bedrock_access.assume_role_policy)
    })
  }
}

# IAM Role logging - Destruction
module "role_destruction_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "IAM Role destroyed"
    resource_type = "aws_iam_role"
    resource_name = aws_iam_role.bedrock_access.name
    resource_id   = aws_iam_role.bedrock_access.id
    resource_arn  = aws_iam_role.bedrock_access.arn
    resource_attributes = jsonencode({
      assume_role_policy = jsondecode(aws_iam_role.bedrock_access.assume_role_policy)
    })
  }
}

# Attach Bedrock Full Access policy to role
resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.bedrock_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# IAM User
resource "aws_iam_user" "travel_bot" {
  name = var.iam_user_name
  
  tags = {
    Name    = var.iam_user_name
    Project = "TravelBot"
  }
}

# IAM User logging - Creation
module "user_creation_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "IAM User created"
    resource_type = "aws_iam_user"
    resource_name = aws_iam_user.travel_bot.name
    resource_id   = aws_iam_user.travel_bot.id
    resource_arn  = aws_iam_user.travel_bot.arn
    resource_attributes = jsonencode({})
  }
}

# IAM User logging - Destruction
module "user_destruction_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "IAM User destroyed"
    resource_type = "aws_iam_user"
    resource_name = aws_iam_user.travel_bot.name
    resource_id   = aws_iam_user.travel_bot.id
    resource_arn  = aws_iam_user.travel_bot.arn
    resource_attributes = jsonencode({})
  }
}

# Create Access Keys
resource "aws_iam_access_key" "travel_bot" {
  user = aws_iam_user.travel_bot.name
}

# Access Key logging - Creation
module "access_key_creation_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "Access Key created"
    resource_type = "aws_iam_access_key"
    resource_name = "Access Key for ${aws_iam_user.travel_bot.name}"
    resource_id   = aws_iam_access_key.travel_bot.id
    resource_arn  = "N/A"
    resource_attributes = jsonencode({
      user            = aws_iam_user.travel_bot.name
      access_key_id   = aws_iam_access_key.travel_bot.id
      secret_key      = aws_iam_access_key.travel_bot.encrypted_secret != "" ? "[REDACTED]" : null
      status          = aws_iam_access_key.travel_bot.status
    })
  }
}

# Access Key logging - Destruction
module "access_key_destruction_logging" {
  source = "./modules/logging"
  enabled = true

  log_attributes = {
    timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    log_message = "Access Key destroyed"
    resource_type = "aws_iam_access_key"
    resource_name = "Access Key for ${aws_iam_user.travel_bot.name}"
    resource_id   = aws_iam_access_key.travel_bot.id
    resource_arn  = "N/A"
    resource_attributes = jsonencode({
      user            = aws_iam_user.travel_bot.name
      access_key_id   = aws_iam_access_key.travel_bot.id
      secret_key      = "[REDACTED]"
      status          = "destroyed"
    })
  }
}

# Attach Bedrock access policy to user
resource "aws_iam_user_policy_attachment" "bedrock_access" {
  user       = aws_iam_user.travel_bot.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}
