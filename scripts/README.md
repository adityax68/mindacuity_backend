# 🛠️ Scripts Directory - Health App (CLEAN VERSION)

This directory contains **clean, unified utility scripts** for managing your Health App database and privilege system.

## 📋 Available Scripts

### **🔧 Migration Management (Alembic)**

#### **`manage_alembic.py`** - Alembic Migration Manager
- **Purpose**: Clean interface to Alembic (industry standard migration system)
- **Usage**: `python scripts/manage_alembic.py [command]`
- **Commands**:
  - `status` - Show migration status
  - `upgrade` - Apply all pending migrations
  - `downgrade [revision]` - Downgrade to specific revision
  - `history` - Show migration history
  - `current` - Show current revision
  - `create "message"` - Create new migration
  - `reset` - Reset database (DANGEROUS!)

#### **Direct Alembic Commands**
- **Purpose**: Use Alembic directly for advanced operations
- **Usage**: `alembic [command]`
- **Examples**:
  - `alembic upgrade head` - Apply all migrations
  - `alembic revision --autogenerate -m "Add new table"` - Create migration
  - `alembic current` - Show current revision
  - `alembic history` - Show migration history

### **🔐 Privilege Management**

#### **`manage_privileges.py`** - Unified Privilege System
- **Purpose**: Complete privilege management in one script
- **Usage**: `python scripts/manage_privileges.py [command]`
- **Commands**:
  - `init` - Initialize privilege system
  - `add --name "priv_name" --description "Description" --category "category"` - Add new privilege
  - `assign --privilege "priv_name" --role "role_name"` - Assign privilege to role
  - `list` - List all privileges
  - `status` - Show system status
  - `backup [--output file]` - Backup privilege system
  - `restore --backup file` - Restore from backup

### **👥 User Management**

#### **`manage_users.py`** - Unified User System
- **Purpose**: Complete user management in one script
- **Usage**: `python scripts/manage_users.py [command]`
- **Commands**:
  - `make-admin <email>` - Make user admin
  - `update-role --email <email> --role <role>` - Update user role
  - `list` - List all users
  - `info <email>` - Show user information

#### **`make_admin.py`** - Quick Admin Creation
- **Purpose**: Simple user-to-admin conversion (kept for convenience)
- **Usage**: `python scripts/make_admin.py <email>`

### **🌱 Seed System**

#### **`seed_system.py`** - Unified Seed System
- **Purpose**: Handle all database seeding operations
- **Usage**: `python scripts/seed_system.py [command]`
- **Commands**:
  - `test-definitions` - Seed test definitions (PHQ-9, GAD-7, PSS-10)
  - `test-user` - Create a test user
  - `all` - Seed everything

### **💾 Backup & Restore**

#### **`backup_privileges.py`** - Backup Privilege System
- **Purpose**: Create a backup of the entire privilege system
- **Usage**: `python scripts/backup_privileges.py [--output backup_file.json]`

#### **`restore_privileges.py`** - Restore from Backup
- **Purpose**: Restore privilege system from backup
- **Usage**: `python scripts/restore_privileges.py --backup_file backup_file.json`

## 🚀 Quick Start Guide

### **For New Setup:**
```bash
# 1. Initialize privilege system
python scripts/manage_privileges.py init

# 2. Seed test definitions
python scripts/seed_system.py test-definitions

# 3. Create test user
python scripts/seed_system.py test-user

# 4. Make user admin
python scripts/manage_users.py make-admin test@example.com

# 5. Check status
python scripts/manage_privileges.py status
```

### **For Adding New Privileges:**
```bash
# 1. Add new privilege
python scripts/manage_privileges.py add --name "manage_reports" --description "Manage system reports" --category "system"

# 2. Assign to role
python scripts/manage_privileges.py assign --privilege "manage_reports" --role "hr"

# 3. Check status
python scripts/manage_privileges.py status
```

### **For Database Migrations:**
```bash
# 1. Check status
python scripts/manage_alembic.py status

# 2. Apply migrations
python scripts/manage_alembic.py upgrade

# 3. Create new migration
python scripts/manage_alembic.py create "Add new feature"

# 4. Show history
python scripts/manage_alembic.py history
```

## 🛡️ Safety Features

### **Migration Safety:**
- ✅ **Idempotent migrations** - Safe to run multiple times
- ✅ **Migration tracking** - Prevents duplicate execution
- ✅ **Error handling** - Stops on first error
- ✅ **Rollback capability** - Can restore from backup

### **Privilege Safety:**
- ✅ **Validation** - Checks if roles/privileges exist
- ✅ **Backup system** - Can restore from backup
- ✅ **Verification** - Shows what was changed

## 📊 Script Categories

| Category | Scripts | Purpose |
|----------|---------|---------|
| **Migration** | `manage_alembic.py` | Alembic database migrations |
| **Privileges** | `manage_privileges.py` | Complete privilege management |
| **Users** | `manage_users.py`, `make_admin.py` | User management |
| **Seeding** | `seed_system.py` | Database seeding |
| **Backup** | `backup_privileges.py`, `restore_privileges.py` | Backup/restore |

## 🎯 Best Practices

### **1. Always Backup Before Major Changes**
```bash
python scripts/manage_privileges.py backup
```

### **2. Test on Development First**
```bash
# Test migration
python scripts/manage_migrations.py dry-run

# Test privilege changes
python scripts/manage_privileges.py add --name "test_priv" --description "Test" --category "test"
```

### **3. Use Status Commands**
```bash
# Check migration status
python scripts/manage_migrations.py status

# Check privilege system
python scripts/manage_privileges.py status
```

### **4. Document Changes**
- Keep track of what privileges you add
- Document any custom role assignments
- Update team when making changes

## 🆘 Troubleshooting

### **Migration Issues:**
```bash
# Check what's wrong
python scripts/manage_alembic.py status

# Show migration history
python scripts/manage_alembic.py history

# Downgrade if needed
python scripts/manage_alembic.py downgrade -1
```

### **Privilege Issues:**
```bash
# Check current state
python scripts/manage_privileges.py status

# Restore from backup
python scripts/manage_privileges.py restore --backup backup.json
```

## 🎉 Summary

Your scripts directory now contains **7 essential scripts** for:
- ✅ **Alembic database migrations** (industry standard)
- ✅ **Privilege management** with full CRUD operations
- ✅ **User management** with role updates
- ✅ **Database seeding** with test data
- ✅ **Backup and restore** capabilities

All scripts are **production-ready**, **team-friendly**, and **unified**! 🚀

## 🔄 What Changed

### **Removed (Redundant):**
- ❌ `aws_migration_setup.py` - AWS-specific, no longer needed
- ❌ `initialize_aws_privileges.py` - AWS-specific, no longer needed
- ❌ `add_new_privilege.py` - Merged into `manage_privileges.py`
- ❌ `assign_privilege_to_role.py` - Merged into `manage_privileges.py`
- ❌ `update_user_role.py` - Merged into `manage_users.py`
- ❌ `seed_test_definitions.py` - Merged into `seed_system.py`
- ❌ `run_migrations.py` - Replaced with Alembic
- ❌ `migrate.py` - Replaced with Alembic
- ❌ `migrations/` folder - Replaced with Alembic
- ❌ `reset_db.py` - Replaced with Alembic

### **Added (Unified):**
- ✅ `manage_privileges.py` - Complete privilege management
- ✅ `manage_users.py` - Complete user management
- ✅ `seed_system.py` - Complete seeding system
- ✅ `manage_alembic.py` - Alembic migration interface
- ✅ `alembic/` directory - Standard Alembic migrations
- ✅ `alembic.ini` - Alembic configuration

### **Kept (Essential):**
- ✅ `make_admin.py` - Quick admin creation
- ✅ `backup_privileges.py` - Backup system
- ✅ `restore_privileges.py` - Restore system