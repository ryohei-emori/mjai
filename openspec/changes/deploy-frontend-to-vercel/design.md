## Context

See `proposal.md` - Why for the motivation. Relevant current state:

- `terraform/main.tf` manages a single `render_static_site.frontend` resource (repo-linked, `root_directory = "frontend"`, `build_command = "npm install && npm run build"`, `publish_path = "out"`, `auto_deploy = true`), plus two hardcoded `env_vars` (`NEXT_PUBLIC_API_URL`, `NODE_ENV`). `terraform/variables.tf` and `terraform/outputs.tf` reference this resource (`frontend_plan`, `render_region` partially, `frontend_service_name`/`frontend_service_url` outputs, the `deployment_info` output). The backend Render Web Service is explicitly out of Terraform's management and out of scope for this change.
- `.github/workflows/deploy.yml` runs a single `terraform-deploy` job (init/validate/plan/apply against the whole `terraform/` dir, so it currently plans/applies backend-irrelevant vars alongside the frontend resource) and a `verify-deployment` job that curls both the backend health endpoint and the Render frontend URL.
- `frontend/next.config.js` sets `output: 'export'` with `images: { unoptimized: true }` — required for a static site publish (`out/`) but incompatible with any Next.js SSR/ISR/Image Optimization feature.
- `frontend/Dockerfile` builds a `standalone` Next.js server (`node server.js` on port 8080) — this output mode is never actually consumed by the current Render **static site** deploy (which only reads `next.config.js`'s `output: 'export'` → `out/`), so the Dockerfile is presently dead weight for the Render path, but it does still work as a local/manual "run frontend like a real Next.js server" option.
- `docs/deployment-plan.md` and `docs/github-secrets.md` document the Render+Terraform frontend flow and reference secrets (`RENDER_API_KEY`, etc.) that this change scopes down to backend-only concerns.

## Goals / Non-Goals

**Goals:**
- Define the target Vercel-based deploy mechanism (git integration vs. Terraform-managed) and justify the choice.
- Resolve the `output: 'export'` vs. `standalone` Dockerfile inconsistency now that the deploy target no longer needs a static-export publish directory.
- Specify what happens to the now-unused `render_static_site` Terraform resource and `frontend/Dockerfile`.
- Specify where frontend env vars now live and how Preview vs. Production values are scoped.
- Specify what changes in `.github/workflows/deploy.yml` so it doesn't try to plan/apply a Terraform resource that no longer exists.

**Non-Goals:**
- Redesigning backend deployment (Render Web Service `mjai` stays as-is, unmanaged by Terraform, same as today).
- Choosing a custom domain / DNS strategy for the Vercel deployment (left as a follow-up, not required to reach parity with the current `*.onrender.com` frontend URL).
- Migrating backend Terraform/CI concerns (database, Gemini secrets) — those remain untouched.
- Re-architecting the Next.js app itself (routing, data fetching) beyond the build-output-mode change needed for Vercel compatibility.

## Decisions

### Decision 1: Use Vercel's native Git integration, not the community Terraform provider

**Chosen approach**: Connect the GitHub repo directly in the Vercel dashboard (or via `vercel link` + `vercel --prod` from the CLI for one-time setup), configure the project's root directory (`frontend`) and env vars in Vercel's own project settings, and let Vercel's git integration handle all subsequent build/deploy/preview lifecycle. No `vercel.json` is required for a standard Next.js app (Vercel auto-detects the framework and default build/output settings); add one later only if custom headers, redirects, or cron/build overrides become necessary.

**Alternatives considered**:
- *Community Terraform provider for Vercel* (e.g. `vercel/terraform-provider-vercel`, unofficial/community-maintained): would keep infra-as-code consistency with the existing `terraform/` directory and let a single `terraform apply` manage both the (existing, out-of-scope) backend reference outputs and the frontend project. Rejected because: (a) it adds a second Terraform provider and state surface for a resource type (Vercel project + env vars) that Vercel's own git integration already manages declaratively and for free; (b) Vercel's preview-deployment-per-PR behavior, which is a primary motivation for this migration, is a first-class dashboard/git-integration feature — replicating it via Terraform would still require Vercel's own webhook/git-integration plumbing underneath, so Terraform would add a management layer without adding capability; (c) the existing Terraform setup here has already drifted from docs once (`docs/deployment-plan.md` describes a `render_service` config that doesn't match the actual `render_static_site` in `main.tf`) — adding a second, less-mature provider increases the same class of drift risk for marginal benefit.
- *Keep Terraform, drop static site, add nothing for frontend*: rejected because frontend deploys would then require fully manual dashboard setup with no record in the repo of what's configured — the tasks/design docs in this change substitute for that record instead, since Vercel's dashboard-driven config isn't naturally expressed as a repo file the way Terraform HCL is.

**Recommendation**: **Native Vercel git integration.** No Terraform provider for Vercel is introduced by this change.

### Decision 2: Drop `output: 'export'`; let Vercel build a normal Next.js SSR app

**Chosen approach**: Remove `output: 'export'` (and re-evaluate `images: { unoptimized: true }`, see below) from `frontend/next.config.js`. Vercel's build pipeline natively runs `next build` and deploys the result as a hybrid static/SSR/ISR app on its edge/serverless infrastructure — this is the default, zero-config path for any Next.js project on Vercel and unlocks image optimization, dynamic routes with server-side data fetching, and future ISR/streaming use if the app needs it, none of which `output: 'export'` permits.

**Alternatives considered**:
- *Keep `output: 'export'` and deploy the static `out/` dir to Vercel as a static site*: technically possible (Vercel can host static export output), but throws away the main technical benefit of moving to Vercel (native Next.js runtime features) and keeps the export-vs-Dockerfile inconsistency conceptually alive (still a static bundle, still no SSR). Rejected — if the goal were to just relocate a static site, Netlify/Cloudflare Pages/S3 would be equally valid and cheaper; Vercel's value proposition here specifically depends on not using static export.
- *Keep `standalone` output and self-host via the Dockerfile on Vercel*: not supported — Vercel does not run arbitrary Dockerfiles for standard projects; its build system expects a Next.js build it can adapt to its own serverless output format. Rejected as infeasible on Vercel.

**Follow-up on `images.unoptimized`**: currently `true` (required by static export, which disallows the default loader). Once `output: 'export'` is removed, Vercel's built-in Image Optimization API becomes available; this proposal does not mandate flipping `unoptimized` to `false` (that's an incremental follow-up affecting `next/image` usage sites, not a deployment-target requirement), but notes it as a natural next step now that the platform supports it. Tracked as a task for awareness, not a blocking requirement of this change.

### Decision 3: Remove `frontend/Dockerfile`; it has no remaining consumer

**Chosen approach**: Delete `frontend/Dockerfile`. It exists today to produce a `standalone` server image, but nothing in the current Render **static site** deploy path invokes it (Render's `render_static_site` resource builds via `build_command`/`publish_path`, not Docker), and Vercel's build pipeline never invokes a project's Dockerfile either. It has no current or future consumer once this change lands.

**Alternatives considered**:
- *Keep it for "local Docker run" convenience*: considered, since a standalone-server Docker image is a reasonable way to smoke-test an SSR build locally without `next dev`. Rejected as the default recommendation because keeping a Dockerfile whose `output: 'standalone'` mode assumption must now also be added to `next.config.js` (superseding the removed `output: 'export'`) creates a second thing to keep in sync with the Vercel build config over time, for a convenience that `vercel dev` / `next build && next start` already covers without a container. Noted in `tasks.md` as a decision the implementer can revisit if local Docker parity is valued enough to maintain it deliberately (in which case `next.config.js` would need `output: 'standalone'` re-added specifically for that local flow, decoupled from the Vercel build which doesn't need any explicit `output` value at all).

### Decision 4: Decommission `render_static_site.frontend` and scope Terraform/CI to backend-only concerns

**Chosen approach**: Remove the `render_static_site.frontend` resource block from `terraform/main.tf`, and remove the frontend-only variables (`frontend_plan`) and outputs (`frontend_service_name`, `frontend_service_url`, and the frontend fields inside `deployment_info`) from `terraform/variables.tf` / `terraform/outputs.tf`. In `.github/workflows/deploy.yml`, drop the frontend-specific `TF_VAR_project_name`/`TF_VAR_repo`/`TF_VAR_branch` usage if nothing else needs them, and remove the "Check Frontend" step from the `verify-deployment` job (Vercel's own deployment dashboard/build-status is the source of truth for frontend deploy success, not a GitHub Actions curl check). Since the backend Render service is unmanaged by Terraform already, this leaves `terraform/main.tf` provider-only (or the implementer may decide the `render` provider/Terraform setup is no longer needed at all if no other Render resource is ever added — this proposal does not mandate deleting the Terraform directory itself, only the frontend resource within it, since backend-Terraform-parity is out of scope per proposal.md).

**Alternatives considered**:
- *Leave the Terraform resource in place but stop applying it (mark unused)*: rejected — a `render_static_site` resource left in state but no longer the source of truth risks configuration drift (someone edits it thinking it's live) and Terraform would try to reconcile/recreate it on the next `apply` if the Render service is ever manually deleted.

### Decision 5: Environment variables move to Vercel Project Settings, scoped by environment

**Chosen approach**: Configure `NEXT_PUBLIC_API_URL` (and any other `NEXT_PUBLIC_*` frontend var currently sourced from `conf/.env`/Terraform, e.g. `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_BACKEND_NGROK_URL`, `NEXT_PUBLIC_FRONTEND_NGROK_URL`) directly in the Vercel dashboard under Project Settings → Environment Variables, using Vercel's built-in Production/Preview/Development scoping. This replaces both the Terraform `env_vars` block (removed per Decision 4) and the `ARG NEXT_PUBLIC_API_URL` Docker build arg (moot once the Dockerfile is removed per Decision 3). Since these are all `NEXT_PUBLIC_*` (build-time-inlined) variables, they must still be set correctly *before* each Vercel build — Vercel resolves this automatically per deployment environment, which is a strict improvement over the current single hardcoded Terraform value with no preview-specific override.

**Alternatives considered**:
- *Commit a `.env.production` / `.env.preview` file to the repo*: rejected — these are meant to point at live backend URLs and per-environment values; committing them either hardcodes production URLs into the repo (fine for `NEXT_PUBLIC_*` since they're not secret, but couples config changes to code commits/PRs unnecessarily) or risks accidental secret leakage if a non-public var is ever added later. Vercel's dashboard-based env var management avoids both issues and matches the "no NEXT_PUBLIC config file to keep in sync" simplification this migration is partly motivated by.

## Risks / Trade-offs

- **[Risk]** Vercel dashboard configuration (project settings, env vars) is not expressed as a file in this repo, so there's no git history / PR review trail for those changes, unlike the removed Terraform `env_vars`. → **Mitigation**: `tasks.md` records the exact env vars to configure as a one-time setup checklist; if stronger auditability is wanted later, revisit the community Terraform provider (Decision 1) as a follow-up, now with a clear cost/benefit baseline from this migration.
- **[Risk]** Removing `output: 'export'` and the Dockerfile changes the local dev/build story (e.g. any local scripts or docs assuming `npm run build` produces a static `out/` directory, or assuming `docker build -t mjai-frontend ./frontend` works, will break). → **Mitigation**: `tasks.md` includes updating references in `docs/deployment-plan.md` and confirming no other script depends on `out/` or the Dockerfile before removing them; `README.md` updates are flagged as an explicit follow-up task since this change's file-edit scope is limited to the OpenSpec artifacts themselves (implementation happens in the apply phase).
- **[Risk]** The current Render frontend URL (`https://mjai-app-frontend.onrender.com`, referenced in `.github/workflows/deploy.yml`'s notification text) will no longer resolve to a live deployment once decommissioned, and any hardcoded links to it (docs, bookmarks, backend CORS allow-list if it references the Render frontend URL) will break. → **Mitigation**: `tasks.md` includes a step to audit `backend/app/main.py`'s CORS allow-list / `FRONTEND_URL` env var and update it to the new Vercel production URL before or immediately after cutover, and to search the repo for the old Render frontend URL string.
- **[Trade-off]** Vercel's free/Hobby tier has usage limits (bandwidth, build minutes, serverless function invocations) different from Render's static site free tier; if traffic grows, a paid Vercel plan may become necessary. → Accepted as a reasonable trade-off given the DX and feature benefits (preview deploys, native SSR/image optimization); not a blocker for this migration, and cost is not a concern raised in scope for this change.

## Migration Plan

1. Create the Vercel project (dashboard import of the GitHub repo, or `vercel link`), set root directory to `frontend`, and let Vercel auto-detect the Next.js framework preset.
2. Configure Production and Preview environment variables in Vercel (`NEXT_PUBLIC_API_URL` → `https://mjai.onrender.com`, plus any other `NEXT_PUBLIC_*` vars in current use).
3. Remove `output: 'export'` from `frontend/next.config.js`; trigger a Vercel deployment (e.g. via a draft PR) and verify the preview deployment builds successfully and the app renders and calls the backend without CORS errors.
4. Once the Vercel preview is verified end-to-end, point DNS/production traffic at the Vercel production URL (or promote the Vercel deployment domain as the new canonical frontend URL) and update the backend's CORS allow-list / `FRONTEND_URL` env var accordingly.
5. Remove the `render_static_site.frontend` Terraform resource, related variables/outputs, `frontend/Dockerfile`, and the frontend steps in `.github/workflows/deploy.yml`, in a single follow-up PR once the Vercel deployment is confirmed stable — do not remove the Render static site until Vercel is verified live, to avoid a window with no working frontend deployment.
6. Update `docs/github-secrets.md` and `docs/deployment-plan.md` to remove/replace Render-frontend-specific content with Vercel setup notes.

**Rollback strategy**: Because the Render `render_static_site` resource and `frontend/Dockerfile` are only removed in step 5 *after* Vercel is verified (steps 1–4 are additive), rollback before step 5 is simply "don't cut over DNS/CORS to Vercel, keep using the existing Render frontend" — no destructive action needs to be undone. If an issue is discovered only after step 5, re-adding the `render_static_site` resource block (same shape as it exists today, restorable from git history) and re-running `terraform apply` restores the Render frontend, though `output: 'export'` would also need to be re-added to `next.config.js` for that path to build correctly again.

## Open Questions

- Final custom domain for the Vercel-hosted frontend (keep an `onrender.com`-style Vercel-provided domain, or configure a custom domain) — deferred to whoever performs the Vercel project setup; doesn't change the specs, approach, or task breakdown in this proposal.
- Whether to eventually flip `images.unoptimized` to `false` to use Vercel's Image Optimization API — deferred as a follow-up optimization, not required for deployment-target parity.
