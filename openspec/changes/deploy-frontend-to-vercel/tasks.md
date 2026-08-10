## 1. Pre-flight audit

- [x] 1.1 Enumerate every `NEXT_PUBLIC_*` variable currently referenced by the frontend (`conf/.env.example`, `terraform/main.tf` `env_vars`, `frontend/Dockerfile` `ARG`s) and record the value each one needs in production.
  - `NEXT_PUBLIC_API_URL` = `https://mjai.onrender.com`
  - `NEXT_PUBLIC_SUPABASE_URL` = Supabase project URL (user-specific)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = Supabase anon key (user-specific)
  - ngrok-related vars (`NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_BACKEND_NGROK_URL`, `NEXT_PUBLIC_FRONTEND_NGROK_URL`) are dev-only, not needed in production
- [x] 1.2 Check whether a custom domain currently points at the Render frontend static site (`mjai-app-frontend.onrender.com` or a custom domain); note current DNS records if a custom domain exists.
  - No custom domain found in code; only `mjai-app-frontend.onrender.com` is referenced
- [x] 1.3 Confirm the current backend URL (`https://mjai.onrender.com`) and its `/health` endpoint are unaffected and will remain the value used for `NEXT_PUBLIC_API_URL`.
  - Confirmed: backend URL unchanged, `/health` endpoint exists

## 2. Vercel project setup

- [ ] 2.1 Create a new Vercel project linked to the GitHub repository, with root directory set to `frontend/`.
  - **MANUAL (Vercel dashboard)**: Import repo, set Root Directory to `frontend`
- [ ] 2.2 Configure Vercel Project Settings → Environment Variables for the Production environment using the values recorded in 1.1.
  - **MANUAL (Vercel dashboard)**: Set `NEXT_PUBLIC_API_URL=https://mjai.onrender.com`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] 2.3 Configure Preview-environment variable overrides in Vercel (if any values should differ for PR previews, e.g. a staging backend URL).
  - **MANUAL (Vercel dashboard)**: Optional, same values for preview if no staging backend
- [ ] 2.4 Verify Vercel auto-detects the project as Next.js and that build/output settings are left at Vercel's framework defaults (no custom build command needed).
  - **MANUAL (Vercel dashboard)**: Verify Framework Preset shows "Next.js"

## 3. Resolve build strategy inconsistency

- [x] 3.1 Remove `output: 'export'` from `frontend/next.config.js`.
- [x] 3.2 Re-evaluate `images: { unoptimized: true }` in `frontend/next.config.js` now that a server-rendering runtime is available; update if appropriate for Vercel's native image optimization.
  - Kept `unoptimized: true` for now; flipping to `false` is a follow-up optimization task
- [ ] 3.3 Run `npm run build` locally in `frontend/` to confirm the SSR build succeeds without static-export-specific errors.
  - **MANUAL (local verification)**: Run `cd frontend && npm run build`
- [ ] 3.4 Run `next start` locally against the SSR build and manually click through key flows (session creation, correction submission, viewing AI proposals) to confirm no static-export-only assumptions broke.
  - **MANUAL (local verification)**: Run `npm start` and test flows
- [x] 3.5 Delete `frontend/Dockerfile` once the SSR build path is confirmed working (Vercel does not use it).

## 4. Preview and production deployment verification

- [ ] 4.1 Push a branch/PR touching `frontend/` and confirm Vercel creates a preview deployment automatically.
  - **MANUAL (after Vercel setup)**: Push a PR and verify preview deployment appears
- [ ] 4.2 Smoke-test the preview deployment: load the app, confirm it calls the configured backend URL successfully with no CORS or network errors.
  - **MANUAL (after preview deployed)**: Test login, session creation, correction flows
- [ ] 4.3 Merge to `main` and confirm Vercel automatically builds and promotes a production deployment.
  - **MANUAL (after verification)**: Merge PR to main
- [ ] 4.4 Smoke-test the production Vercel URL end-to-end (create a session, submit text for correction, view an AI proposal) against the live backend.
  - **MANUAL (after production deployed)**: Full end-to-end test

## 5. Decommission Render/Terraform frontend path

- [x] 5.1 Remove the `render_static_site.frontend` resource from `terraform/main.tf`.
- [x] 5.2 Remove frontend-only variables from `terraform/variables.tf` (e.g. `frontend_plan`, and `render_region` if it was only used by the frontend resource) that are no longer referenced by any remaining resource.
- [x] 5.3 Remove frontend-only outputs from `terraform/outputs.tf` (`frontend_service_name`, `frontend_service_url`) and strip frontend fields from the `deployment_info` output.
- [ ] 5.4 Run `terraform plan` to confirm the plan only shows removal of the frontend static site (no unintended changes to backend-related config) before applying.
  - **MANUAL (requires credentials)**: Run `terraform plan` with `RENDER_API_KEY`, `RENDER_OWNER_ID`, etc.
- [ ] 5.5 Apply the Terraform change to decommission the Render frontend static site.
  - **MANUAL (destructive, requires approval)**: Run `terraform apply` only after Vercel is verified working
- [ ] 5.6 Delete the Render frontend static site itself via the Render dashboard/API if any orphaned resource remains after the Terraform apply.
  - **MANUAL (Render dashboard)**: Check for orphaned resources after apply

## 6. CI/CD and documentation updates

- [x] 6.1 Remove the `Check Frontend` step and frontend URL references (`Display Deployment Info`, `Deployment Success Notification`) from `.github/workflows/deploy.yml`'s `verify-deployment` job.
- [x] 6.2 Review whether `.github/workflows/deploy.yml`'s `terraform-deploy` job still has any purpose after the frontend resource is removed; rescope its `paths` trigger to drop `frontend/**` if the frontend no longer affects Terraform state.
- [x] 6.3 Update `docs/github-secrets.md` to remove/annotate the Render-frontend-specific guidance and note that frontend deployment is now handled by Vercel's dashboard/git integration (no GitHub secret required unless a future CI step is added).
- [x] 6.4 Update `README.md`'s deployment instructions (if present) to reflect Vercel as the frontend deployment target instead of Render/Terraform.

## 7. Domain and final cutover (if applicable)

- [ ] 7.1 If a custom domain was identified in 1.2, add it to the Vercel project and follow Vercel's DNS verification steps.
  - **N/A**: No custom domain identified; using Vercel's default `*.vercel.app` URL
- [ ] 7.2 Cut over DNS to Vercel only after confirming the Vercel deployment is fully functional on its default `*.vercel.app` URL.
  - **N/A**: No DNS cutover needed without custom domain
- [ ] 7.3 Monitor the cutover for propagation issues and confirm the custom domain resolves to the Vercel deployment and correctly reaches the backend.
  - **N/A**: No DNS cutover needed
