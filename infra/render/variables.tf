variable "render_api_key" {
  description = "API key for the Render account."
  type        = string
  sensitive   = true
}

variable "service_name" {
  description = "Name of the Render web service."
  type        = string
  default     = "auto-job-applier-ui"
}

variable "service_plan" {
  description = "Render plan to use for the service (e.g., starter, standard, pro)."
  type        = string
  default     = "starter"
}

variable "region" {
  description = "Region slug for the Render service."
  type        = string
  default     = "oregon"
}

variable "repo_url" {
  description = "Repository URL Render should deploy from."
  type        = string
  default     = "https://github.com/GodsScion/Auto_job_applier_linkedIn"
}

variable "branch" {
  description = "Branch to deploy from."
  type        = string
  default     = "main"
}
