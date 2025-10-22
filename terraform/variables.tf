variable "render_api_key" {
  type        = string
  description = "Render API key with permissions to manage services and databases"
  sensitive   = true
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

# Supabase configuration
variable "supabase_access_token" {
  type        = string
  description = "Supabase access token for management API"
  sensitive   = true
}

variable "supabase_project_ref" {
  type        = string
  description = "Supabase project reference ID"
}

variable "supabase_org_id" {
  type        = string
  description = "Supabase organization ID"
}

variable "supabase_region" {
  type        = string
  description = "Supabase project region"
  default     = "ap-northeast-1"  # Tokyo region
}

variable "supabase_db_plan" {
  type        = string
  description = "Supabase database plan"
  default     = "free"  # or "pro" for production
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

variable "gemini_api_key" {
  type        = string
  description = "Gemini API key for AI functionality"
  sensitive   = true
}

variable "gemini_model" {
  type        = string
  description = "Gemini model identifier"
  default     = "gemini-2.5-pro"
}
