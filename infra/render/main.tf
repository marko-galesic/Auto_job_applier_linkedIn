terraform {
  required_version = ">= 1.5.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.4"
    }
  }
}

provider "render" {
  api_key = var.render_api_key
}

resource "render_web_service" "auto_job_ui" {
  name   = var.service_name
  plan   = var.service_plan
  region = var.region

  repo {
    branch      = var.branch
    repo        = var.repo_url
    auto_deploy = true
  }

  service_details {
    env           = "python"
    build_command = "pip install --upgrade pip && pip install -r requirements.txt"
    start_command = "gunicorn app:app --bind 0.0.0.0:$PORT"
  }

  env_vars {
    key   = "FLASK_ENV"
    value = "production"
  }

  env_vars {
    key   = "FLASK_DEBUG"
    value = "false"
  }

  env_vars {
    key   = "APPLICATION_HISTORY_DIR"
    value = var.application_history_dir
  }
}
