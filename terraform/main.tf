terraform {
  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.3.0"
    }
  }
  required_version = ">= 1.0.0"
}

provider "render" {
  api_key  = var.render_api_key
  owner_id = var.render_owner_id
}

# Backend service (existing service - managed outside Terraform)
# Service ID: srv-d2f031buibrs738hhe40
# URL: https://mjai.onrender.com

# Frontend deployment has been migrated to Vercel (git-integrated, dashboard-configured).
# The former render_static_site.frontend resource has been removed.
# See openspec/changes/deploy-frontend-to-vercel/ for migration details.
