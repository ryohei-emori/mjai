## Purpose

Defines how the MJAI FastAPI backend is deployed, configured, and served when Vercel Python runtime (rather than Render Web Service) is the hosting platform.

## ADDED Requirements

### Requirement: Vercel-based deploy on push to main
The system SHALL deploy the FastAPI backend via Vercel whenever changes are pushed to the `main` branch, without requiring a separate Render deployment or manual infrastructure changes.

#### Scenario: Push to main triggers a production deployment
- **WHEN** a commit affecting backend code is pushed to the `main` branch
- **THEN** Vercel automatically builds and deploys the FastAPI app as a serverless function, making it accessible at the Vercel production URL

#### Scenario: Pull request triggers a preview deployment
- **WHEN** a pull request is opened or updated with changes to backend code
- **THEN** Vercel automatically builds and publishes a preview deployment for that pull request

### Requirement: FastAPI entrypoint follows Vercel Python runtime conventions
The system SHALL expose a FastAPI instance named `app` at a Vercel-detected entrypoint location so that Vercel's build system can discover and serve the application without manual configuration.

#### Scenario: Vercel detects FastAPI app automatically
- **GIVEN** a Python file exists at a recognized entrypoint location (e.g., `api/index.py` or `app/main.py`)
- **AND** that file exports a FastAPI instance named `app`
- **WHEN** Vercel builds the project
- **THEN** Vercel detects FastAPI from dependencies and serves the entire app as a single Vercel Function

### Requirement: Environment variables configured in Vercel project settings
The system SHALL source all backend runtime environment variables (`DATABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOWED_USER_EMAIL`, `FRONTEND_URL`) from Vercel project environment variable configuration.

#### Scenario: Production deployment reads Vercel-configured secrets
- **GIVEN** `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOWED_USER_EMAIL` are set in the Vercel project's Production environment variables
- **WHEN** Vercel deploys the backend for production
- **THEN** the running function uses those configured values for database connections and auth verification

#### Scenario: Preview deployment can use different variable values
- **GIVEN** environment variables are scoped differently for Preview vs Production in Vercel
- **WHEN** Vercel builds a preview deployment for a pull request
- **THEN** the preview deployment uses the Preview-scoped values

### Requirement: CORS allows Vercel frontend origin
The system SHALL include the Vercel-hosted frontend origin in its CORS allow-list so that browser requests from the frontend are accepted.

#### Scenario: Frontend on same Vercel project can call backend
- **GIVEN** the frontend and backend are deployed to the same Vercel project
- **WHEN** the frontend makes an API request to a relative `/api/*` path
- **THEN** the request succeeds without CORS errors because it is same-origin

#### Scenario: Frontend on separate Vercel project can call backend
- **GIVEN** the frontend is deployed to a different Vercel project with a distinct domain
- **WHEN** the frontend makes a cross-origin API request
- **THEN** the request succeeds because the backend CORS allow-list includes the frontend's Vercel origin via `FRONTEND_URL` or regex

### Requirement: Health endpoint remains accessible
The system SHALL continue to expose an unauthenticated `/health` endpoint that returns a 200 response for liveness checks.

#### Scenario: Health check succeeds after Vercel deployment
- **WHEN** an HTTP GET request is made to `/api/health` (or the equivalent Vercel function path)
- **THEN** the response is HTTP 200 with JSON `{"status": "healthy", ...}`

### Requirement: Render backend deployment path is retired
The system SHALL no longer deploy the backend to Render once the Vercel deployment is verified, and documentation SHALL reflect the new deployment target.

#### Scenario: Documentation references Vercel, not Render
- **WHEN** a user reads `AGENTS.md` or `docs/DESIGN.md` after this change is implemented
- **THEN** backend deployment documentation references Vercel (not Render) as the production host

#### Scenario: Render Web Service is suspended or deleted
- **GIVEN** the Vercel backend deployment is verified working
- **WHEN** the operator retires the Render infrastructure
- **THEN** the Render Web Service (`mjai` / `srv-d2f031buibrs738hhe40`) is suspended or deleted manually, with no automated Terraform or CI/CD action required
