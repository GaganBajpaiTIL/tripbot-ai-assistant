variable "iam_user_name" {
  description = "Name of the IAM user to create"
  type        = string
  default     = "TravelBotUserDev"
}

variable "iam_role_name" {
  description = "Name of the IAM role to create"
  type        = string
  default     = "BedrockAccessRole"
}

variable "region" {
  description = "AWS region to use"
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile_name" {
  description = "Name of the AWS CLI profile to configure"
  type        = string
  default     = "travelBot"
}
