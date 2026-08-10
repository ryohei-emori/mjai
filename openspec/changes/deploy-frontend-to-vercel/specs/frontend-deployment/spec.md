## Purpose

Defines how the MJAI frontend is built, deployed, configured, and verified when Vercel (rather than a Terraform-managed Render static site) is the deployment target for the Next.js application.

## ADDED Requirements

### Requirement: Vercel-based build and deploy on push to main
The system SHALL build and deploy the frontend via Vercel whenever changes are pushed to the `main` branch, without requiring a Terraform plan/apply step or a manually triggered GitHub Actions job for the frontend.

#### Scenario: Push to main triggers a production deployment
- **WHEN** a commit affecting the `frontend/` directory is pushed to the `main` branch
- **THEN** Vercel automatically builds the frontend from that commit and, on success, promotes the build to the production deployment without any manual Terraform or GitHub Actions step being required

#### Scenario: Pull request triggers a preview deployment
- **WHEN** a pull request is opened or updated with changes to the `frontend/` directory
- **THEN** Vercel automatically builds and publishes a preview deployment for that pull request, isolated from the production deployment

### Requirement: Environment variables configured in Vercel project settings
The system SHALL source all frontend build-time and runtime environment variables (including `NEXT_PUBLIC_API_URL` and other `NEXT_PUBLIC_*` values) from Vercel project environment variable configuration, and SHALL NOT rely on values baked into a Docker image or injected via Terraform `env_vars`.

#### Scenario: Production build reads Vercel-configured API URL
- **GIVEN** `NEXT_PUBLIC_API_URL` is set in the Vercel project's Production environment variables to the backend's URL
- **WHEN** Vercel builds the frontend for a production deployment
- **THEN** the built frontend uses that configured value for all backend API calls, with no separate Docker build argument or Terraform `env_vars` block required to supply it

#### Scenario: Preview deployment can use different variable values
- **GIVEN** `NEXT_PUBLIC_API_URL` is set differently for the Vercel project's Preview environment than for Production
- **WHEN** Vercel builds a preview deployment for a pull request
- **THEN** the preview build uses the Preview-scoped value rather than the Production-scoped value

### Requirement: Deployed frontend correctly calls the configured backend API
The system SHALL ensure that the frontend deployed on Vercel successfully communicates with the backend API at its configured URL, regardless of which platform hosts the backend.

#### Scenario: Frontend loads and fetches data from backend after deployment
- **GIVEN** the frontend has been deployed to Vercel with `NEXT_PUBLIC_API_URL` pointing at the live backend
- **WHEN** a user loads the deployed frontend and triggers an action that calls the backend (e.g. creating a session or requesting a correction)
- **THEN** the request reaches the backend at the configured URL and the frontend renders the response without CORS or connectivity errors

#### Scenario: Backend health check remains independent of frontend platform
- **GIVEN** the backend continues to run on its existing hosting platform, unaffected by this change
- **WHEN** the frontend is deployed to Vercel
- **THEN** no change to the backend's deployment, URL, or health-check endpoint is required for the frontend to function correctly

### Requirement: Render static-site deployment path is decommissioned
The system SHALL no longer deploy the frontend to Render once the Vercel deployment is verified, and SHALL remove the Terraform-managed `render_static_site` resource used for that purpose.

#### Scenario: Terraform no longer manages a frontend static site
- **WHEN** Terraform is applied against the `terraform/` configuration after this change is implemented
- **THEN** no `render_static_site` resource for the frontend exists in the plan or state, and only backend-unrelated or non-frontend resources (if any) remain

#### Scenario: CI/CD no longer deploys the frontend to Render
- **WHEN** a commit is pushed to `main`
- **THEN** the GitHub Actions workflow SHALL NOT attempt to build, plan, or apply a Render frontend deployment, and frontend deployment SHALL be handled solely by Vercel's git integration
