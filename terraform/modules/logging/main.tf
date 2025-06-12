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
    command     = self.triggers.log_entry
    interpreter = ["bash", "-c"]
    
    dynamic "when" {
      for_each = each.value.when != null ? [1] : []
      content {
        destroy = each.value.when == "destroy"
      }
    }
  }
}
