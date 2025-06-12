# This module provides a simple way to log entries to a file

resource "null_resource" "log" {
  count = var.enabled ? 1 : 0

  triggers = {
    # Always re-run when the log attributes change
    log_attributes = jsonencode(var.log_attributes)
  }

  
  # Generate the log entry from the template
  provisioner "local-exec" {
    command = <<-EOT
      cat >> '${var.log_file}'
    EOT
    interpreter = ["bash", "-c"]
    environment = {
      LOG_ENTRY = templatefile("${path.module}/templates/logging.tpl", 
        merge(
          var.log_attributes,
          {
            resource_attributes = var.resource_attributes != null ? var.resource_attributes : "",
            timestamp = formatdate("YYYY-MM-DD hh:mm:ss", timestamp())
          }
        )
      )
    }
  }
}
