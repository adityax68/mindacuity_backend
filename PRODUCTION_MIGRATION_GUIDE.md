# Production Database Migration Guide

## 🎯 Migrating Password Reset Feature to Production

This guide covers how to safely apply the password reset migration (`abdaa4f06ec2`) to your production database.

---

## ⚠️ Pre-Migration Checklist

**Before running ANY migration in production:**

- [ ] **Backup your database** (critical!)
- [ ] **Test in staging environment** first
- [ ] **Schedule maintenance window** (if possible)
- [ ] **Notify users** of potential downtime
- [ ] **Have rollback plan ready**
- [ ] **Verify current migration version**
- [ ] **Review migration SQL**

---

## 📋 Step-by-Step Process

### Step 1: Backup Production Database

**PostgreSQL backup:**

```bash
# Create a backup with timestamp
pg_dump -h your-prod-host \
        -U your-db-user \
        -d your-db-name \
        -F c \
        -b \
        -v \
        -f "health_app_backup_$(date +%Y%m%d_%H%M%S).backup"

# Or using connection string
pg_dump $DATABASE_URL -F c -f "health_app_backup_$(date +%Y%m%d_%H%M%S).backup"
```

**Verify backup:**
```bash
# Check backup file exists and has size > 0
ls -lh health_app_backup_*.backup
```

**Store backup securely:**
```bash
# Upload to S3 or secure storage
aws s3 cp health_app_backup_*.backup s3://your-backup-bucket/
```

---

### Step 2: Check Current Migration Version

**Connect to production and check:**

```bash
# SSH into your production server
ssh your-production-server

# Activate virtual environment
cd /path/to/health_app/backend
source venv/bin/activate

# Check current migration version
alembic current

# Expected output: 3dc44802e7fe (head) - add_email_verification_fields
```

**Or using SQL directly:**

```sql
-- Connect to your production database
SELECT version_num FROM alembic_version;

-- Should show: 3dc44802e7fe
```

---

### Step 3: Review the Migration

**Check what the migration will do:**

```bash
# Show the SQL that will be executed (dry run)
alembic upgrade abdaa4f06ec2 --sql

# This shows:
# - ADD COLUMN password_reset_token
# - ADD COLUMN password_reset_expires_at
# - ADD COLUMN password_reset_attempts
# - ADD COLUMN last_reset_attempt
# - CREATE INDEX ix_users_password_reset_token
```

**The migration is SAFE because:**
- ✅ All columns are nullable (no data issues)
- ✅ Default value for attempts is 0
- ✅ Only adds columns (no data modification)
- ✅ No existing data is affected
- ✅ Non-blocking operation

---

### Step 4: Test in Staging First

**If you have a staging environment:**

```bash
# On staging server
cd /path/to/health_app/backend
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify columns were added
psql $DATABASE_URL -c "\d+ users"

# Test the endpoints
curl -X POST https://staging.yourdomain.com/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

### Step 5: Run Migration in Production

**Method 1: Using Alembic (Recommended)**

```bash
# SSH into production server
ssh your-production-server

# Navigate to backend directory
cd /path/to/health_app/backend

# Activate virtual environment
source venv/bin/activate

# IMPORTANT: Set production DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Run the migration
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade 3dc44802e7fe -> abdaa4f06ec2, add_password_reset_fields
```

**Method 2: Manual SQL (If Alembic not available)**

```sql
-- Connect to production database
psql $DATABASE_URL

-- Start transaction
BEGIN;

-- Add columns
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR;
ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN password_reset_attempts INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN last_reset_attempt TIMESTAMP WITH TIME ZONE;

-- Create index
CREATE INDEX ix_users_password_reset_token ON users(password_reset_token);

-- Update alembic version
UPDATE alembic_version SET version_num = 'abdaa4f06ec2';

-- Verify changes
\d+ users

-- If everything looks good, commit
COMMIT;

-- If something is wrong, rollback
-- ROLLBACK;
```

---

### Step 6: Verify Migration Success

**Check migration status:**

```bash
alembic current
# Should show: abdaa4f06ec2 (head) - add_password_reset_fields
```

**Verify database schema:**

```bash
# Check columns were added
psql $DATABASE_URL -c "\d+ users" | grep password_reset
```

Expected output:
```
password_reset_token         | character varying |           |          |
password_reset_expires_at    | timestamp with time zone |           |          |
password_reset_attempts      | integer           |           | not null | 0
last_reset_attempt           | timestamp with time zone |           |          |
```

**Check index:**
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' AND indexname LIKE '%password_reset%';
```

---

### Step 7: Deploy Updated Code

**After migration succeeds, deploy new backend code:**

```bash
# Pull latest code
git pull origin main

# Install any new dependencies (if any)
pip install -r requirements.txt

# Restart backend service
# For systemd:
sudo systemctl restart health_app

# For PM2:
pm2 restart health_app

# For Docker:
docker-compose restart backend

# For manual uvicorn:
pkill -f uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

---

### Step 8: Test the Feature

**Test forgot-password endpoint:**

```bash
curl -X POST https://yourdomain.com/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "your-test-email@example.com"}'

# Expected response:
# {
#   "success": true,
#   "message": "If an account with that email exists, a password reset link has been sent."
# }
```

**Check email was sent:**
- Verify email arrives in inbox
- Click reset link
- Verify token works

**Test reset-password endpoint:**

```bash
curl -X POST https://yourdomain.com/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "token-from-email",
    "new_password": "newTestPassword123"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Password has been reset successfully..."
# }
```

---

## 🔄 Rollback Plan

**If something goes wrong, here's how to rollback:**

### Option 1: Restore from Backup

```bash
# Stop the application first
sudo systemctl stop health_app

# Restore database from backup
pg_restore -h your-prod-host \
           -U your-db-user \
           -d your-db-name \
           -c \
           -v \
           health_app_backup_TIMESTAMP.backup

# Restart application
sudo systemctl start health_app
```

### Option 2: Rollback Migration

```bash
# Downgrade to previous version
alembic downgrade 3dc44802e7fe

# This will:
# - Drop the index
# - Remove the 4 password reset columns
```

**Rollback SQL (manual):**

```sql
BEGIN;

-- Drop index
DROP INDEX IF EXISTS ix_users_password_reset_token;

-- Remove columns
ALTER TABLE users DROP COLUMN IF EXISTS last_reset_attempt;
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_attempts;
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_expires_at;
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_token;

-- Update alembic version
UPDATE alembic_version SET version_num = '3dc44802e7fe';

COMMIT;
```

---

## 🎯 Different Deployment Scenarios

### Scenario 1: Heroku

```bash
# Push code with migration
git push heroku main

# Run migration
heroku run alembic upgrade head -a your-app-name

# Or using Heroku Postgres directly
heroku pg:psql -a your-app-name
# Then run SQL manually

# Restart dynos
heroku restart -a your-app-name
```

### Scenario 2: AWS RDS + EC2

```bash
# SSH into EC2 instance
ssh ec2-user@your-instance

# Set DATABASE_URL to point to RDS
export DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/dbname"

# Run migration
cd /app/backend
source venv/bin/activate
alembic upgrade head

# Restart application
sudo systemctl restart health_app
```

### Scenario 3: Docker/Kubernetes

```bash
# Build new image with updated code
docker build -t health-app-backend:latest .

# Push to registry
docker push your-registry/health-app-backend:latest

# Run migration in a one-off container
docker run --rm \
  -e DATABASE_URL=$DATABASE_URL \
  your-registry/health-app-backend:latest \
  alembic upgrade head

# Update deployment (K8s)
kubectl rollout restart deployment health-app-backend

# Or Docker Compose
docker-compose up -d --no-deps backend
```

### Scenario 4: Managed Services (Railway, Render, Fly.io)

```bash
# Most managed services run migrations automatically
# But you can also run manually:

# Railway
railway run alembic upgrade head

# Render
# Add to render.yaml:
# - name: migrate
#   command: alembic upgrade head

# Fly.io
fly ssh console
cd /app/backend
alembic upgrade head
```

---

## 🔧 Environment Variables

**Make sure these are set in production:**

```bash
# Required for password reset
FRONTEND_URL=https://yourdomain.com

# Email service (already configured)
SES_FROM_EMAIL=noreply@yourdomain.com
SES_FROM_NAME=Your App Name
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

---

## 📊 Monitoring After Migration

**Monitor these for 24 hours after migration:**

1. **Database Performance**
   ```sql
   -- Check query performance
   SELECT * FROM pg_stat_user_tables WHERE relname = 'users';
   
   -- Check index usage
   SELECT * FROM pg_stat_user_indexes WHERE indexrelname LIKE '%password_reset%';
   ```

2. **Application Logs**
   ```bash
   # Check for errors
   tail -f /var/log/health_app/app.log | grep -i error
   
   # Check password reset attempts
   tail -f /var/log/health_app/app.log | grep -i "password reset"
   ```

3. **Email Delivery**
   - Monitor SES dashboard for bounces
   - Check email delivery rates
   - Verify no spam complaints

4. **API Response Times**
   - Monitor `/forgot-password` endpoint latency
   - Monitor `/reset-password` endpoint latency

---

## ✅ Post-Migration Checklist

After successful migration:

- [ ] Verify migration version: `alembic current`
- [ ] Check database schema: columns and index exist
- [ ] Test forgot-password endpoint
- [ ] Test reset-password endpoint  
- [ ] Verify emails are being sent
- [ ] Test complete user flow (email to password reset)
- [ ] Monitor error logs for 24 hours
- [ ] Update team documentation
- [ ] Archive database backup securely
- [ ] Celebrate! 🎉

---

## 🚨 Troubleshooting

### Issue: Migration fails with "column already exists"

**Cause:** Migration was partially applied

**Solution:**
```sql
-- Check which columns exist
\d+ users

-- If some columns exist, you can:
-- Option 1: Drop them and re-run migration
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_token;
-- etc...

-- Option 2: Skip adding existing columns in migration
-- Modify migration to check IF NOT EXISTS
```

### Issue: "Can't locate revision"

**Cause:** Alembic version table out of sync

**Solution:**
```bash
# Check current version in database
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version"

# Stamp to correct version
alembic stamp 3dc44802e7fe

# Then upgrade
alembic upgrade head
```

### Issue: Downtime during migration

**Cause:** Large table with locks

**Solution:**
```sql
-- These migrations are non-blocking, but if concerned:
-- 1. Add columns with CONCURRENTLY (PostgreSQL)
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR;
-- (Should be instant since adding nullable columns)

-- 2. Create index concurrently
CREATE INDEX CONCURRENTLY ix_users_password_reset_token 
ON users(password_reset_token);
```

---

## 📚 Additional Resources

- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **PostgreSQL ALTER TABLE:** https://www.postgresql.org/docs/current/sql-altertable.html
- **Database Backup Best Practices:** https://www.postgresql.org/docs/current/backup.html

---

## 🎓 Best Practices Summary

1. ✅ **Always backup first** - No exceptions!
2. ✅ **Test in staging** - Catch issues before prod
3. ✅ **Review migration SQL** - Know what will happen
4. ✅ **Have rollback plan** - Be prepared
5. ✅ **Monitor after deployment** - Watch for issues
6. ✅ **Run migrations during low traffic** - If possible
7. ✅ **Keep backups for 30 days** - Safety net
8. ✅ **Document everything** - Future you will thank you

---

## 🎉 That's It!

Follow these steps and your production migration will be smooth and safe!

**Questions?** Review this guide or check the main implementation docs.

**Need help?** Most issues are solved by:
1. Checking alembic version
2. Reviewing migration logs
3. Verifying environment variables
4. Restoring from backup if needed

Good luck! 🚀





