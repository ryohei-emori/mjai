## 1. Vercel Entrypoint Setup

- [x] 1.1 Create `api/` directory at repo root
- [x] 1.2 Create `api/index.py` that imports and re-exports `app` from `backend.app.main`
- [x] 1.3 Create/symlink `requirements.txt` at repo root pointing to `backend/requirements.txt`

## 2. Vercel Configuration

- [x] 2.1 Create `vercel.json` at repo root with function config and rewrites
- [x] 2.2 Add `.python-version` file at repo root to pin Python version (3.12)

## 3. Backend Code Updates

- [x] 3.1 Update `backend/app/main.py` CORS allow-list: add Vercel origins, remove Render origins
- [x] 3.2 Add `FRONTEND_URL` env var support to CORS configuration if not already present

## 4. Frontend Configuration

- [x] 4.1 Update `conf/.env.example` with new `NEXT_PUBLIC_API_URL` pattern for Vercel (relative path for monorepo)

## 5. Documentation Updates

- [x] 5.1 Update `AGENTS.md`: change backend deployment from Render to Vercel; update env var table; update CI/CD section
- [x] 5.2 Update `docs/DESIGN.md`: update architecture diagram and component descriptions for Vercel backend
- [x] 5.3 ~~Update `docs/github-secrets.md`~~ (SKIPPED: file deleted; content merged into AGENTS.md)

## 6. Manual Vercel Dashboard Setup (Owner tasks)

- [ ] 6.1 Import repo to Vercel or reconfigure existing project for monorepo (root dir: `.`, framework: Next.js, build command: `cd frontend && npm install && npm run build`, output dir: `frontend/.next`)
- [ ] 6.2 Configure Production environment variables in Vercel: `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOWED_USER_EMAIL`, `FRONTEND_URL`, `ENVIRONMENT=production`
- [ ] 6.3 Configure Preview environment variables if different from Production
- [ ] 6.4 Update `NEXT_PUBLIC_API_URL` in Vercel to empty or `/api` for same-origin monorepo

## 7. Verification

- [ ] 7.1 Deploy preview (create PR) and verify `/api/health` returns 200
- [ ] 7.2 Test API calls from frontend preview (create session, fetch sessions)
- [ ] 7.3 Merge to main and verify production deployment
- [ ] 7.4 Verify frontend can authenticate and call all API endpoints

## 8. Render Retirement (Manual - Owner)

- [ ] 8.1 Confirm Vercel deployment is stable (at least 24h with no issues)
- [ ] 8.2 Suspend Render Web Service `mjai` (srv-d2f031buibrs738hhe40) from Render dashboard
- [ ] 8.3 After confirming no regressions, delete Render Web Service from Render dashboard
