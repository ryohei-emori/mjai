This terraform directory contains a minimal skeleton to provision Render services and an optional managed Postgres instance.

Quick start (local testing):

1. Install Terraform (>=1.4). 2. Configure the Render API key as an environment variable or pass it as a tfvar.

Example:

```bash
export TF_VAR_render_api_key=RENDER_API_KEY_VALUE
terraform -chdir=terraform init
terraform -chdir=terraform plan
# Review plan, then apply when ready
terraform -chdir=terraform apply
```

Notes:
- The Render Terraform provider resource names/attributes evolve. Inspect the provider documentation and adapt `main.tf` accordingly.
- Sensitive values (DB password, service role keys) should be provided via provider-specific secret resources or repository secrets in CI.
- `frontend_env_vars` and `backend_env_vars` are lists of [key, value] pairs for convenience; set them via `-var='frontend_env_vars=[["NEXT_PUBLIC_SUPABASE_URL","https://..."]]'` if needed.
