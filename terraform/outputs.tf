output "backend_service_name" {
  description = "Name of the backend service (existing, managed outside Terraform)"
  value       = "mjai"
}

output "backend_service_url" {
  description = "URL of the deployed backend service (existing)"
  value       = "https://mjai.onrender.com"
}

# Frontend outputs removed - frontend is now deployed via Vercel (git-integrated).
# Frontend URL is managed in Vercel dashboard, not Terraform.

output "deployment_info" {
  description = "Deployment information"
  value = {
    backend_name = "mjai"
    backend_url  = "https://mjai.onrender.com"
    environment  = var.environment
    note         = "Frontend deployed via Vercel (not managed by Terraform)"
  }
}
