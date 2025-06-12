variable "enabled" {
  description = "Whether to enable logging"
  type        = bool
  default     = true
}

variable "destroy" {
  description = "Whether this is a destroy-time provisioner"
  type        = bool
  default     = false
}

variable "log_attributes" {
  description = "Log attributes to include in the log entry"
  type = object({
    log_type           = string
    timestamp          = string
    log_message        = string
    resource_type      = string
    resource_name      = string
    resource_id        = string
    resource_arn       = string
    resource_attributes = string
  })
}

variable "resource_attributes" {
  description = "Additional resource attributes to include in the log"
  type        = string
  default     = null
}

variable "log_file" {
  description = "Path to the log file where entries should be written"
  type        = string
  default     = "terraform_dev.log"
}
