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

############################
# Frontend static site
############################
resource "render_static_site" "frontend" {
  name           = "${var.project_name}-frontend"
  repo_url       = "https://github.com/${var.repo}"
  branch         = var.branch
  root_directory = "frontend"
  build_command  = "npm install && npm run build"
  publish_path   = "out"
  auto_deploy    = true

  env_vars = {
    NEXT_PUBLIC_API_URL = {
      value = "https://mjai.onrender.com"
    }
    NODE_ENV = {
      value = "production"
    }
  }
}
