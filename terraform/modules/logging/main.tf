# This module provides a standardized way to add logging to resources

locals {
  default_log_attributes = {
    creation = {
      log_type    = "creation"
      timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
    }
    destruction = {
      log_type    = "destruction"
      timestamp   = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
      when        = "destroy"
    }
  }
}

resource "null_resource" "log" {
  for_each = var.enabled ? {
    creation = merge(
      local.default_log_attributes["${var.destroy ? "destruction" : "creation"}"],
      var.log_attributes,
      {
        resource_attributes = var.resource_attributes != null ? var.resource_attributes : ""
      }
    )
  } : {}

  triggers = {
    log_entry = templatefile("${path.module}/templates/logging.tpl", each.value)
  }

  provisioner "local-exec" {
    command     = <<-EOT
      cat >> '${var.log_file}'
    EOT
    interpreter = ["bash", "-c"]
    when        = lookup(each.value, "when", "create")
    
    # Pass the log entry through stdin
    environment = {
      LOG_ENTRY = self.triggers.log_entry
    }
  }
}
