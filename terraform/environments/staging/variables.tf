# Variables for staging environment

variable "render_api_key" {
  type = string
  description = "Render API key"
  sensitive = true
}

# Override default variables for staging
db_plan = "starter"
frontend_plan = "starter"
backend_plan = "starter"
environment = "staging"

# Source the shared variables
include {
  path = "../../variables.tf"
}