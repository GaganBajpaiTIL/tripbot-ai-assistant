terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Local file for logging
resource "local_file" "tf_log" {
  filename = "${path.module}/terraform_creation_logs.txt"
  content  = ""
}

# Function to append logs
locals {
  log_creation = <<-EOT
    echo '${formatdate("YYYY-MM-DD hh:mm:ss", timestamp())} - Resource created: ${self.id}' >> ${path.module}/terraform_creation_logs.txt
    echo '  Type: ${self.resource_type}' >> ${path.module}/terraform_creation_logs.txt
    echo '  Name: ${self.tags.Name != null ? self.tags.Name : "Not specified"}' >> ${path.module}/terraform_creation_logs.txt
    echo '  ARN: ${self.arn != null ? self.arn : "N/A"}' >> ${path.module}/terraform_creation_logs.txt
    echo '  ID: ${self.id}' >> ${path.module}/terraform_creation_logs.txt
    echo '  All attributes:' >> ${path.module}/terraform_creation_logs.txt
    echo '  ${jsonencode(self)}' >> ${path.module}/terraform_creation_logs.txt
    echo '' >> ${path.module}/terraform_creation_logs.txt
  EOT
  
  log_destruction = <<-EOT
    echo '${formatdate("YYYY-MM-DD hh:mm:ss", timestamp())} - Resource destroyed: ${self.id}' >> ${path.module}/terraform_destruction_logs.txt
    echo '  Type: ${self.resource_type}' >> ${path.module}/terraform_destruction_logs.txt
    echo '  Name: ${self.tags.Name != null ? self.tags.Name : "Not specified"}' >> ${path.module}/terraform_destruction_logs.txt
    echo '  ARN: ${self.arn != null ? self.arn : "N/A"}' >> ${path.module}/terraform_destruction_logs.txt
    echo '  ID: ${self.id}' >> ${path.module}/terraform_destruction_logs.txt
    echo '' >> ${path.module}/terraform_destruction_logs.txt
  EOT
}

provider "aws" {
  region = var.region
}

# Create IAM Role with Bedrock access
resource "aws_iam_role" "bedrock_access" {
  name               = var.iam_role_name
  assume_role_policy = templatefile("${path.module}/templates/trust-policy.json.tpl", {
    YOUR_AWS_ACCOUNT_ID_PLACEHOLDER = data.aws_caller_identity.current.account_id
    IAM_USER_NAME_PLACEHOLDER = var.iam_user_name
  })
  # Add tags for better identification
  tags = {
    Name = var.iam_role_name
    Project = "TravelBot"
  }

  # Log creation
  provisioner "local-exec" {
    command     = local.log_creation
    interpreter = ["bash", "-c"]
  }
}

# Attach Bedrock Full Access policy
resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.bedrock_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  
  # Log creation
  provisioner "local-exec" {
    command     = local.log_creation
    interpreter = ["bash", "-c"]
  }
}

# Create IAM User
resource "aws_iam_user" "travel_bot" {
  name = var.iam_user_name
  
  # Add tags for better identification
  tags = {
    Name = var.iam_user_name
    Project = "TravelBot"
  }
  
  # Log creation
  provisioner "local-exec" {
    command     = local.log_creation
    interpreter = ["bash", "-c"]
  }
}

# Create Access Keys
resource "aws_iam_access_key" "travel_bot" {
  user = aws_iam_user.travel_bot.name
  
  # Log creation and destruction for access key
  provisioner "local-exec" {
    command     = <<-EOT
      echo '${formatdate("YYYY-MM-DD hh:mm:ss", timestamp())} - Resource created: ${self.id}' >> ${path.module}/terraform_creation_logs.txt
      echo '  Type: ${self.resource_type}' >> ${path.module}/terraform_creation_logs.txt
      echo '  User: ${self.user}' >> ${path.module}/terraform_creation_logs.txt
      echo '  ID: ${self.id}' >> ${path.module}/terraform_creation_logs.txt
      echo '  Access Key ID: ${self.id}' >> ${path.module}/terraform_creation_logs.txt
      echo '  Secret Access Key: [REDACTED]' >> ${path.module}/terraform_creation_logs.txt
      echo '' >> ${path.module}/terraform_creation_logs.txt
    EOT
    interpreter = ["bash", "-c"]
  }
  
  provisioner "local-exec" {
    when        = destroy
    command     = <<-EOT
      echo '${formatdate("YYYY-MM-DD hh:mm:ss", timestamp())} - Resource destroyed: ${self.id}' >> ${path.module}/terraform_destruction_logs.txt
      echo '  Type: ${self.resource_type}' >> ${path.module}/terraform_destruction_logs.txt
      echo '  User: ${self.user}' >> ${path.module}/terraform_destruction_logs.txt
      echo '  ID: ${self.id}' >> ${path.module}/terraform_destruction_logs.txt
      echo '  Access Key ID: ${self.id}' >> ${path.module}/terraform_destruction_logs.txt
      echo '  Secret Access Key: [REDACTED]' >> ${path.module}/terraform_destruction_logs.txt
      echo '' >> ${path.module}/terraform_destruction_logs.txt
    EOT
    interpreter = ["bash", "-c"]
  }
}

# Get AWS Account ID
data "aws_caller_identity" "current" {}
