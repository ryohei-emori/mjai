terraform {
  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.3.0"
    }
    supabase = {
      source  = "supabase/supabase"
      version = "~> 1.0"
    }
  }
  required_version = ">= 1.0.0"
}

provider "render" {
  api_key = var.render_api_key
}

provider "supabase" {
  access_token = var.supabase_access_token
  project_ref  = var.supabase_project_ref
}

############################
# Supabase Configuration
############################

# プロジェクト設定
resource "supabase_project" "mjai" {
  name           = "${var.project_name}-db"
  database_name  = var.project_name
  region        = var.supabase_region
  db_plan       = var.supabase_db_plan

  # プロジェクト設定
  organization_id = var.supabase_org_id
}

# データベーススキーマの設定
resource "supabase_database_schema" "mjai" {
  project_ref = supabase_project.mjai.id
  name        = "public"

  depends_on = [supabase_project.mjai]
}

# テーブル定義
resource "supabase_database_table" "sessions" {
  project_ref = supabase_project.mjai.id
  schema      = supabase_database_schema.mjai.name
  name        = "sessions"

  columns {
    name = "id"
    type = "serial"
    primary_key = true
  }

  columns {
    name = "created_at"
    type = "timestamp with time zone"
    default = "now()"
  }

  columns {
    name = "updated_at"
    type = "timestamp with time zone"
    default = "now()"
  }

  columns {
    name = "metadata"
    type = "jsonb"
    default = "'{}'::jsonb"
  }
}

resource "supabase_database_table" "histories" {
  project_ref = supabase_project.mjai.id
  schema      = supabase_database_schema.mjai.name
  name        = "histories"

  columns {
    name = "id"
    type = "serial"
    primary_key = true
  }

  columns {
    name = "session_id"
    type = "integer"
    references {
      table = "sessions"
      column = "id"
      on_delete = "CASCADE"
    }
  }

  columns {
    name = "created_at"
    type = "timestamp with time zone"
    default = "now()"
  }

  columns {
    name = "role"
    type = "text"
    is_nullable = false
  }

  columns {
    name = "content"
    type = "text"
    is_nullable = false
  }

  columns {
    name = "metadata"
    type = "jsonb"
    default = "'{}'::jsonb"
  }
}

resource "supabase_database_table" "proposals" {
  project_ref = supabase_project.mjai.id
  schema      = supabase_database_schema.mjai.name
  name        = "proposals"

  columns {
    name = "id"
    type = "serial"
    primary_key = true
  }

  columns {
    name = "history_id"
    type = "integer"
    references {
      table = "histories"
      column = "id"
      on_delete = "CASCADE"
    }
  }

  columns {
    name = "created_at"
    type = "timestamp with time zone"
    default = "now()"
  }

  columns {
    name = "content"
    type = "text"
    is_nullable = false
  }

  columns {
    name = "metadata"
    type = "jsonb"
    default = "'{}'::jsonb"
  }
}

############################
# Backend service
############################
resource "render_service" "backend" {
  name            = "${var.project_name}-backend"
  region          = var.render_region
  repo_url        = "https://github.com/${var.repo}"
  branch          = var.branch
  service_type    = "web_service"
  plan            = var.backend_plan
  root_directory  = "backend"

  # These are non-sensitive env vars
  env = {
    "ENVIRONMENT"    = var.environment
    "USE_POSTGRESQL" = "true"
    "APP_ROOT"       = "/app"
    "PYTHONPATH"     = "/app"
  }

  # Secret env vars via provider
  secret_files {
    name = "app-secrets"
    value = jsonencode({
      DATABASE_URL = "postgresql://postgres:${supabase_project.mjai.database_password}@${supabase_project.mjai.database_host}:5432/postgres"
      GEMINI_API_KEY = var.gemini_api_key
      GEMINI_MODEL = var.gemini_model
    })
  }

  # Health check for backend
  healthcheck_path = "/health"
  auto_deploy = true
}
}

############################
# Frontend service
############################
resource "render_service" "frontend" {
  name            = "${var.project_name}-frontend"
  region          = var.render_region
  repo_url        = "https://github.com/${var.repo}"
  branch          = var.branch
  service_type    = "web_service"
  plan            = var.frontend_plan
  root_directory  = "frontend"

  # Non-sensitive env vars including build-time NEXT_PUBLIC_*
  env = {
    "NODE_VERSION" = "18"
    "NODE_ENV"     = "production"
    "NEXT_PUBLIC_API_URL" = render_service.backend.service_url
  }

  # No secrets needed for frontend (uses backend APIs)
  auto_deploy = true

  # Ensure backend is available first
  depends_on = [render_service.backend]
}
