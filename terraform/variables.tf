variable "render_api_key" {
  type        = string
  description = "Render API key with permissions to manage services"
  sensitive   = true
}

variable "render_owner_id" {
  type        = string
  description = "Render owner ID (user or team)"
}

variable "project_name" {
  type        = string
  description = "Project name prefix for resource naming"
  default     = "mjai"
}

variable "repo" {
  type        = string
  description = "GitHub repo in the format owner/repo"
  default     = "ryohei-emori/mjai"
}

variable "branch" {
  type        = string
  description = "Git branch to deploy"
  default     = "main"
}

variable "render_region" {
  type        = string
  description = "Render deployment region"
  default     = "oregon"
}

variable "environment" {
  type        = string
  description = "Environment name (production, staging, etc)"
  default     = "production"
}

variable "frontend_plan" {
  type        = string
  description = "Render plan for frontend service"
  default     = "starter"
}

variable "backend_plan" {
  type        = string
  description = "Render plan for backend service"
  default     = "starter"
}

variable "database_url" {
  type        = string
  description = "Supabase database connection URL"
  sensitive   = true
}

variable "gemini_api_key" {
  type        = string
  description = "Gemini API key for AI functionality"
  sensitive   = true
}

variable "gemini_model" {
  type        = string
  description = "Gemini model identifier"
  default     = "gemini-2.5-flash"
}
