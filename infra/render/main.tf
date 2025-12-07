terraform {
  required_version = ">= 1.5.0"

  required_providers {
    # Pin to the exact provider version that matches this configuration to
    # avoid Terraform downloading a different schema on new runners. The CI
    # flakiness we were seeing (alternating "unsupported block" vs "unsupported
    # argument" errors) is consistent with Terraform grabbing different
    # versions of the Render provider on different runs.
    render = {
      source  = "render-oss/render"
      version = "1.4.0"
    }
  }
}

provider "render" {
  api_key = var.render_api_key
}
