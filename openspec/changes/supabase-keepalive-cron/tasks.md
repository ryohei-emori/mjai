## 1. Backend Keep-alive Endpoint

- [x] 1.1 Add `/keepalive` endpoint to `backend/app/main.py` that executes `SELECT 1` via db_helper
- [x] 1.2 Handle DB connection errors and return appropriate HTTP status codes (200 success, 503 failure)

## 2. GitHub Actions Workflow

- [x] 2.1 Create `.github/workflows/supabase-keepalive.yml` with cron schedule (every 3 days)
- [x] 2.2 Configure workflow to use `KEEPALIVE_URL` variable with fallback to default production URL
- [x] 2.3 Add soft retry on failure and fail workflow on non-2xx response

## 3. Documentation

- [x] 3.1 Update `AGENTS.md` with Supabase free-tier pause information and keep-alive workflow details
