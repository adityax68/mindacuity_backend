# 🗄️ Database Migration Guide

This guide explains how to use the migration system in your Health App.

## 🚀 Quick Start

### **Run All Migrations**
```bash
python scripts/migrate.py run
```

### **Check Migration Status**
```bash
python scripts/migrate.py status
```

### **Dry Run (See What Would Happen)**
```bash
python scripts/migrate.py dry-run
```

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `migrate run` | Run all pending migrations |
| `migrate status` | Show migration status |
| `migrate dry-run` | Show what would be done without making changes |
| `migrate force` | Run migrations (continue on error) |
| `migrate reset` | Reset database (DANGEROUS!) |
| `migrate seed` | Reset and seed database |

## 🔄 Migration Workflow

### **1. Development**
```bash
# Check current status
python scripts/migrate.py status

# Run pending migrations
python scripts/migrate.py run

# Verify everything works
python app/main.py
```

### **2. Team Collaboration**
```bash
# Pull latest code
git pull origin main

# Run any new migrations
python scripts/migrate.py run

# Check status
python scripts/migrate.py status
```

### **3. Production Deployment**
```bash
# Backup database first!
pg_dump mydb > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
python scripts/migrate.py run

# Verify application
python app/main.py
```

## 📁 Migration Files

All migration files are stored in `migrations/` directory:

| File | Purpose |
|------|---------|
| `create_test_schema.sql` | Create test assessment tables |
| `seed_test_data.sql` | Add PHQ-9, GAD-7, PSS-10 data |
| `add_performance_indexes.sql` | Add 22+ performance indexes |
| `add_chat_attachments.sql` | Add file attachment support |
| `add_complaint_org_fields.sql` | Add organization fields |
| `add_refresh_tokens.sql` | Add JWT refresh token support |
| `add_user_profile_fields.sql` | Add user profile fields |
| `create_session_based_chat.sql` | Add chat system |
| `fix_conversation_usage_foreign_key.sql` | Fix foreign key constraint |
| `add_search_indexes.sql` | Add search optimization |
| `add_test_performance_indexes.sql` | Add test-specific indexes |

## 🛡️ Safety Features

### **1. Migration Tracking**
- Tracks which migrations have been applied
- Prevents duplicate execution
- Records file hashes for integrity checking

### **2. Idempotent Migrations**
- All migrations use `IF NOT EXISTS`
- Safe to run multiple times
- Won't break if already applied

### **3. Error Handling**
- Stops on first error (unless using `--force`)
- Detailed error messages
- Rollback on failure

## 🔧 Advanced Usage

### **Force Mode (Continue on Error)**
```bash
python scripts/migrate.py force
```

### **Dry Run (See What Would Happen)**
```bash
python scripts/migrate.py dry-run
```

### **Check Status**
```bash
python scripts/migrate.py status
```

### **Reset Database (Development Only)**
```bash
python scripts/migrate.py reset
```

### **Reset and Seed Database**
```bash
python scripts/migrate.py seed
```

## 🚨 Important Notes

### **1. Always Backup Before Production**
```bash
pg_dump mydb > backup_$(date +%Y%m%d_%H%M%S).sql
```

### **2. Test Migrations on Staging First**
- Never run untested migrations on production
- Use staging environment that mirrors production

### **3. Migration Order Matters**
- Migrations are run in alphabetical order
- Use numbered prefixes if order is critical
- Example: `001_create_users.sql`, `002_add_indexes.sql`

### **4. Team Collaboration**
- Always pull latest code before running migrations
- Don't skip migrations
- Communicate about database changes

## 🔍 Troubleshooting

### **Migration Fails**
```bash
# Check what went wrong
python scripts/migrate.py status

# Check database logs
tail -f /var/log/postgresql/postgresql.log

# Fix the issue and retry
python scripts/migrate.py run
```

### **Migration Already Applied**
```bash
# This is normal - migrations are idempotent
# The system will skip already-applied migrations
```

### **Database Connection Issues**
```bash
# Check your DATABASE_URL in .env file
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

## 📊 Migration Status Example

```
📊 Migration Status
==============================
📁 Total migration files: 11
✅ Applied migrations: 8
⏳ Pending migrations: 3

📋 Migration Details:
  ✅ Applied - create_test_schema (2024-01-15 10:30:00)
  ✅ Applied - seed_test_data (2024-01-15 10:30:05)
  ✅ Applied - add_performance_indexes (2024-01-15 10:30:10)
  ⏳ Pending - add_chat_attachments
  ⏳ Pending - add_complaint_org_fields
  ⏳ Pending - add_refresh_tokens
```

## 🎯 Best Practices

### **1. Naming Conventions**
- Use descriptive names: `add_user_email_field.sql`
- Use prefixes for order: `001_`, `002_`, etc.
- Use underscores: `add_user_profile_fields.sql`

### **2. Migration Content**
- Always use `IF NOT EXISTS` for tables
- Always use `IF NOT EXISTS` for indexes
- Always use `IF NOT EXISTS` for columns
- Test migrations on development first

### **3. Team Workflow**
- Create migration files
- Test locally
- Commit to version control
- Team members pull and run migrations
- Deploy to production

## 🆘 Emergency Procedures

### **Rollback Migration**
```bash
# 1. Restore from backup
psql mydb < backup_20240115_103000.sql

# 2. Check status
python scripts/migrate.py status

# 3. Run migrations up to desired point
python scripts/migrate.py run
```

### **Fix Corrupted Migration State**
```bash
# 1. Check migration history
psql mydb -c "SELECT * FROM migration_history ORDER BY applied_at;"

# 2. Remove problematic migration record
psql mydb -c "DELETE FROM migration_history WHERE migration_name = 'problematic_migration';"

# 3. Re-run migrations
python scripts/migrate.py run
```

## 🎉 Summary

Your migration system provides:
- ✅ **Safe execution** with tracking
- ✅ **Idempotent migrations** (safe to run multiple times)
- ✅ **Team collaboration** support
- ✅ **Production deployment** safety
- ✅ **Easy management** with simple commands

Use `python scripts/migrate.py run` to keep your database up to date! 🚀
