## Migration Plan: Supabase → Render Database

### 1. Preparation Steps

1. **Backup Current Database**
   ```bash
   # From Supabase dashboard or using pg_dump
   pg_dump -h [YOUR-PROJECT-REF].supabase.co -U postgres -d postgres > mjai_backup.sql
   ```

2. **Update Environment Variables**
   - Rotate and remove existing Supabase secrets from `conf/.env`
   - Update backend environment with new Render DATABASE_URL

3. **Test Migration Locally**
   ```bash
   # Using existing migration script (adapted for Render)
   cd backend
   python db/migrate_to_supabase.py
   ```

### 2. Migration Process

1. **Infrastructure Setup**
   ```bash
   # Initialize Terraform
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

2. **Database Schema Migration**
   ```sql
   -- Run on Render Postgres DB
   -- Create tables
   CREATE TABLE IF NOT EXISTS sessions (
       id SERIAL PRIMARY KEY,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       metadata JSONB DEFAULT '{}'::jsonb
   );

   CREATE TABLE IF NOT EXISTS histories (
       id SERIAL PRIMARY KEY,
       session_id INTEGER REFERENCES sessions(id),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       role TEXT NOT NULL,
       content TEXT NOT NULL,
       metadata JSONB DEFAULT '{}'::jsonb
   );

   CREATE TABLE IF NOT EXISTS proposals (
       id SERIAL PRIMARY KEY,
       history_id INTEGER REFERENCES histories(id),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       content TEXT NOT NULL,
       metadata JSONB DEFAULT '{}'::jsonb
   );
   ```

3. **Data Migration**
   ```bash
   # Option A: Using pg_restore (if using pg_dump backup)
   pg_restore -h [RENDER-DB-HOST] -U [RENDER-DB-USER] -d [RENDER-DB-NAME] mjai_backup.sql

   # Option B: Using Python migration script
   cd backend
   DATABASE_URL=postgres://[RENDER-DB-CONNECTION-STRING] python db/migrate_to_supabase.py
   ```

### 3. Verification Steps

1. **Database Validation**
   ```sql
   -- Run on Render Postgres
   SELECT COUNT(*) FROM sessions;
   SELECT COUNT(*) FROM histories;
   SELECT COUNT(*) FROM proposals;
   ```

2. **Application Tests**
   ```bash
   # Backend API tests
   cd backend
   pytest

   # Frontend integration
   cd frontend
   npm test
   ```

3. **Staging Deployment**
   - Deploy to a staging environment on Render
   - Verify all API endpoints
   - Check frontend functionality

### 4. Production Cutover

1. **Database Switch**
   - Update production DATABASE_URL to point to Render
   - Verify backend connects successfully

2. **Frontend Update**
   - Deploy frontend with Render backend URL
   - Monitor error rates and API responses

3. **Cleanup**
   - Remove Supabase configuration
   - Archive old secrets
   - Update documentation

### 5. Rollback Plan

1. **Database Rollback**
   ```bash
   # If needed, restore from backup
   pg_restore -h [SUPABASE-HOST] -U postgres -d postgres mjai_backup.sql
   ```

2. **Configuration Rollback**
   - Revert DATABASE_URL to Supabase
   - Revert frontend API endpoints
   - Re-enable Supabase client if needed

### 6. Monitoring & Verification

1. **Health Checks**
   - Monitor backend /health endpoint
   - Watch application logs
   - Check error rates

2. **Performance Metrics**
   - Compare query latencies
   - Monitor connection pool usage
   - Check API response times

### Success Criteria

- ✓ All tables and data migrated successfully
- ✓ Application tests passing
- ✓ Frontend able to perform all operations
- ✓ No data loss or corruption
- ✓ Performance metrics within acceptable range
- ✓ Zero downtime during cutover (or minimal planned downtime)