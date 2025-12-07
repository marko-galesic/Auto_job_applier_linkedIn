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

locals {
  # Ensure service names stay unique across Terraform workspaces to avoid
  # clashes with any manually created Render services using the same base name.
  rendered_service_name = "${var.service_name}-${terraform.workspace}"
}

resource "render_web_service" "auto_job_ui" {
  name   = local.rendered_service_name
  plan   = var.service_plan
  region = var.region

  start_command = "gunicorn app:app --bind 0.0.0.0:$PORT"

  runtime_source = {
    native_runtime = {
      runtime       = "python"
      build_command = "pip install --upgrade pip && pip install -r requirements.txt"
      branch        = var.branch
      repo_url      = var.repo_url
      auto_deploy   = true
    }
  }

  env_vars = {
    FLASK_ENV = {
      value = "production"
    }
    FLASK_DEBUG = {
      value = "false"
    }
    APPLICATION_HISTORY_DIR = {
      value = var.application_history_dir
    }
  }
}
