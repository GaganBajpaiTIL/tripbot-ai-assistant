output "iam_user_credentials" {
  description = "IAM User credentials"
  value = {
    access_key_id     = aws_iam_access_key.travel_bot.id
    secret_access_key = aws_iam_access_key.travel_bot.secret
  }
  sensitive = true
}

output "iam_role_arn" {
  description = "ARN of the IAM role with Bedrock access"
  value       = aws_iam_role.bedrock_access.arn
}

output "aws_profile_name" {
  description = "Name of the AWS CLI profile to configure"
  value       = var.aws_profile_name
}

output "region" {
  description = "AWS region configured"
  value       = var.region
}
