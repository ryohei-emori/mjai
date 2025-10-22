output "backend_service_name" {
  description = "Name of the backend service (existing)"
  value       = "mjai"
}

output "backend_service_url" {
  description = "URL of the deployed backend service (existing)"
  value       = "https://mjai.onrender.com"
}

output "frontend_service_name" {
  description = "Name of the frontend service"
  value       = render_static_site.frontend.name
}

output "frontend_service_url" {
  description = "URL of the deployed frontend service"
  value       = "https://${var.project_name}-frontend.onrender.com"
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    backend_name  = "mjai"
    frontend_name = render_static_site.frontend.name
    backend_url   = "https://mjai.onrender.com"
    frontend_url  = "https://${var.project_name}-frontend.onrender.com"
    region        = var.render_region
    environment   = var.environment
  }
}
