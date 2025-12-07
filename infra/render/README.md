# Render Terraform configuration

To avoid provider-version flakiness in CI, run `terraform init` (optionally with
`terraform providers lock -platform=linux_amd64`) locally and commit the
resulting `.terraform.lock.hcl`. This ensures the Render provider version stays
consistent between runners.

Service provisioning has been removed from this configuration to avoid
attempting to recreate an existing Render service. Manage the Render web
service directly in the Render dashboard and use Terraform only for any future
read-only interactions or data sources that rely on the Render provider.
