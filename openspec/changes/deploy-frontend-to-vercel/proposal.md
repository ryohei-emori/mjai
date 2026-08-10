## Why

The frontend is currently deployed as a Terraform-managed `render_static_site` on Render, but the repo has two conflicting build strategies in place at once: `frontend/next.config.js` sets `output: 'export'` (static export, publish dir `out`) while `frontend/Dockerfile` builds and runs a Next.js `standalone` SSR server (`node server.js` on port 8080) that Render's static-site deploy path never uses. This inconsistency, combined with Render static sites lacking native preview deployments and requiring a full `terraform plan`/`apply` cycle (and `RENDER_API_KEY`/`RENDER_OWNER_ID` secrets) for every frontend change, motivates moving the frontend deployment target to Vercel — the platform Next.js is built for, with zero-config git-integrated builds, automatic preview deployments per PR, and no Terraform or Dockerfile required for the frontend.

## What Changes

- **BREAKING**: Frontend deployment target moves from Render (`render_static_site` Terraform resource) to Vercel (git-integrated, Vercel-managed builds). The Render frontend static site is decommissioned.
- Resolve the static-export vs. standalone-server inconsistency: adopt standard Next.js SSR build (remove `output: 'export'`) so Vercel builds and serves the app using its native Next.js runtime (see `design.md` for justification).
- Remove `frontend/Dockerfile` and the `render_static_site` resource from `terraform/main.tf` (and corresponding variables/outputs in `terraform/variables.tf` / `terraform/outputs.tf`) since Vercel does not use either.
- Remove the frontend-related steps from `.github/workflows/deploy.yml` (the `terraform-deploy` job's frontend concerns and the `verify-deployment` job's frontend health check), or scope that workflow to backend/Terraform-only concerns, since Vercel deploys via its own git integration rather than GitHub Actions + Terraform.
- Move frontend build-time environment variables (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_BACKEND_NGROK_URL`, `NEXT_PUBLIC_FRONTEND_NGROK_URL`, etc.) from Terraform `env_vars` / Docker build args into Vercel Project Settings → Environment Variables.
- Update `docs/github-secrets.md` to remove Render-frontend-specific guidance (as it applies to the frontend) and document the new Vercel-related secrets/config (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`) only if a CI step is kept for parity checks; otherwise note that Vercel's own dashboard/git integration handles deployment and no GitHub secret is required for the frontend.
- No changes to backend deployment (Render Web Service `mjai`, `srv-d2f031buibrs738hhe40`), AI generation, authentication, or database persistence — those are covered by sibling, independent change proposals.

## Capabilities

### New Capabilities
- `frontend-deployment`: Defines how the frontend is built, deployed, configured (env vars), and verified against the backend, now that Vercel (not Render/Terraform) is the deployment target.

### Modified Capabilities
- None. No existing `openspec/specs/` capability currently documents frontend deployment behavior; this proposal introduces the first spec for it.

## Impact

- **Affected code**: `frontend/next.config.js` (remove `output: 'export'`, adjust `images.unoptimized`), `frontend/Dockerfile` (removed), `terraform/main.tf` / `terraform/variables.tf` / `terraform/outputs.tf` (remove `render_static_site` resource and frontend-only variables/outputs), `.github/workflows/deploy.yml` (remove or rescope frontend deploy/verify steps).
- **Affected docs**: `docs/github-secrets.md` (Render frontend section becomes obsolete), `README.md` deployment instructions (out of scope for this change's file edits, but flagged as needing a follow-up update).
- **Affected config**: `conf/.env.example` `NEXT_PUBLIC_*` vars conceptually move from Terraform/Docker build-time injection to Vercel Project Settings (no repo file necessarily changes, but the source of truth for these values changes).
- **Dependencies**: The deployed frontend must still be configured to call the backend at its current URL (`https://mjai.onrender.com`), which remains outside Terraform and outside this change's scope. If the backend URL or the auth/DB sibling changes alter the backend's public URL or contract, the Vercel env vars will need updating accordingly — this proposal does not redesign those.
- **Unaffected**: Backend deployment (Render Web Service, unchanged), AI suggestion generation, authentication, database persistence — all covered by independent sibling proposals.
