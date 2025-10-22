# Staging environment configuration for Render deployment

terraform {
  backend "local" {
    path = "terraform.tfstate.staging"
  }
}

provider "render" {
  api_key = var.render_api_key
}

# Use staging-specific variables
locals {
  environment = "staging"
  project_prefix = "mjai-staging"
}

# Include shared configuration
include {
  path = "../terraform/main.tf"
}