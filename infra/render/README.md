# Render Terraform configuration

To avoid provider-version flakiness in CI, run `terraform init` (optionally with
`terraform providers lock -platform=linux_amd64`) locally and commit the
resulting `.terraform.lock.hcl`. This ensures the Render provider version stays
consistent between runners.

Service names are derived from the workspace to avoid collisions with existing
Render services. The rendered service name is `<service_name>-<workspace>`, so
the default workspace deploys to `auto-job-applier-ui-default` while other
workspaces receive their own isolated service names.
