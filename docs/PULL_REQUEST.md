# Draft PR: Render Migration Implementation

## Changes

1. Infrastructure:
   - Added Terraform configuration for Render deployment
   - Created database migration tools and verification SQL
   - Updated deployment documentation

2. Frontend:
   - Removed Supabase client dependency
   - Simplified API configuration
   - Updated Dockerfile and environment handling

3. Backend:
   - Added database migration script
   - Added migration verification tools
   - Updated Dockerfile for Render compatibility

## Added Files
- `backend/db/migrate_to_render.py`: Data migration script
- `backend/db/verify_migration.sql`: Schema/data verification
- `backend/.github/workflows/migrate-database.yml`: Migration workflow

## Modified Files
- `terraform/main.tf`: Updated Render provider and resources
- `terraform/variables.tf`: Added new variables
- `terraform/outputs.tf`: Enhanced outputs
- `frontend/Dockerfile`: Removed Supabase args
- `frontend/src/app/api.ts`: Removed Supabase client
- `frontend/next.config.js`: Simplified config
- `conf/compose.render.yml`: Production compose
- `conf/.env.example`: Updated for Render
- `DEPLOY.md`: New Render deployment docs

## How to Test

1. Infrastructure:
   ```bash
   cd terraform
   terraform init
   terraform plan
   ```

2. Frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   npm start
   ```

3. Backend:
   ```bash
   cd backend
   python -m pytest
   ```

4. Migration (staging):
   ```bash
   # Set env vars
   export SOURCE_DATABASE_URL="..."
   export TARGET_DATABASE_URL="..."
   
   # Run migration
   cd backend
   python db/migrate_to_render.py
   
   # Verify
   psql $TARGET_DATABASE_URL < db/verify_migration.sql
   ```

## Deployment Plan

1. Infrastructure Setup:
   - Create Render account if needed
   - Generate Render API key
   - Add GitHub secrets

2. Database Migration:
   - Run migration in staging first
   - Verify data integrity
   - Schedule production migration

3. Application Deployment:
   - Deploy backend first
   - Verify health checks
   - Deploy frontend
   - Verify end-to-end

4. Monitoring:
   - Watch error rates
   - Monitor database metrics
   - Check API response times

## Rollback Plan

1. If migration fails:
   - Revert to Supabase connection
   - Restore from backup if needed

2. If deployment fails:
   - Roll back to previous version
   - Switch DATABASE_URL back

## Security Notes

- Remove old Supabase credentials after migration
- Rotate database passwords
- Use Render secrets for sensitive data

## Next Steps

- [ ] Review and approve PR
- [ ] Schedule staging deployment
- [ ] Prepare production migration plan
- [ ] Update monitoring configuration