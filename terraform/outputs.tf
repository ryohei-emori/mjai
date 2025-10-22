output "supabase_project_id" {
  description = "Supabase project ID"
  value       = supabase_project.mjai.id
}

output "supabase_api_url" {
  description = "Supabase API URL"
  value       = supabase_project.mjai.api_url
}

output "supabase_db_host" {
  description = "Supabase database host"
  value       = supabase_project.mjai.database_host
}

# 注意: パスワードなどの機密情報は出力しません

output "backend_service_name" {
  description = "Name of the backend service"
  value       = render_service.backend.name
}

output "backend_service_url" {
  description = "URL of the deployed backend service"
  value       = render_service.backend.service_url
}

output "frontend_service_name" {
  description = "Name of the frontend service"
  value       = render_service.frontend.name
}

output "frontend_service_url" {
  description = "URL of the deployed frontend service"
  value       = render_service.frontend.service_url
}

output "backend_status" {
  description = "Deployment status of the backend service"
  value       = render_service.backend.status
}

output "frontend_status" {
  description = "Deployment status of the frontend service"
  value       = render_service.frontend.status
}
