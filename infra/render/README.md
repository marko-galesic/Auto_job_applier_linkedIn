# Render Terraform configuration

To avoid provider-version flakiness in CI, run `terraform init` (optionally with
`terraform providers lock -platform=linux_amd64`) locally and commit the
resulting `.terraform.lock.hcl`. This ensures the Render provider version stays
consistent between runners.
