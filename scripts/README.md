# 🛠️ Scripts Directory - Health App

This directory contains utility scripts for managing your Health App database and privilege system.

## 📋 Available Scripts

### **🔧 Migration Scripts**

#### **`run_migrations.py`** - Advanced Migration Runner
- **Purpose**: Run database migrations with tracking and safety checks
- **Usage**: `python scripts/run_migrations.py [options]`
- **Features**: 
  - Migration tracking with database table
  - File hash verification for integrity
  - Idempotent execution (safe to run multiple times)
  - Error handling with rollback
  - Dry run mode for testing
  - Force mode for error recovery
  - Status checking with detailed reports

#### **`migrate.py`** - Simple Migration Manager
- **Purpose**: Easy-to-use commands for common migration tasks
- **Usage**: `python scripts/migrate.py [command]`
- **Commands**:
  - `run` - Run all pending migrations
  - `status` - Show migration status
  - `dry-run` - Show what would be done
  - `force` - Run migrations (continue on error)
  - `reset` - Reset database (DANGEROUS!)
  - `seed` - Reset and seed database

### **🔐 Privilege Management Scripts**

#### **`initialize_aws_privileges.py`** - Complete Privilege Setup
- **Purpose**: Initialize complete privilege system for AWS migration
- **Usage**: `python scripts/initialize_aws_privileges.py`
- **Features**:
  - Creates all roles and privileges
  - Assigns privileges to roles
  - Updates existing users
  - Verifies setup

#### **`aws_migration_setup.py`** - AWS Migration Setup
- **Purpose**: Complete AWS migration setup with privilege system
- **Usage**: `python scripts/aws_migration_setup.py`
- **Features**:
  - Checks database connection
  - Creates all tables
  - Migrates existing data
  - Initializes privilege system

#### **`add_new_privilege.py`** - Add New Privilege
- **Purpose**: Add a new privilege to the system
- **Usage**: `python scripts/add_new_privilege.py --name "privilege_name" --description "Description" --category "category"`
- **Features**:
  - Creates new privilege
  - Assigns to admin role by default
  - Validates input

#### **`assign_privilege_to_role.py`** - Assign Privilege to Role
- **Purpose**: Assign a privilege to a specific role
- **Usage**: `python scripts/assign_privilege_to_role.py --privilege "privilege_name" --role "role_name"`
- **Features**:
  - Assigns privilege to role
  - Validates role and privilege exist
  - Prevents duplicate assignments

#### **`update_user_role.py`** - Update User Role
- **Purpose**: Change a user's role
- **Usage**: `python scripts/update_user_role.py --email "user@example.com" --role "admin"`
- **Features**:
  - Updates user role
  - Validates role exists
  - Shows user information

#### **`make_admin.py`** - Make User Admin
- **Purpose**: Make an existing user an admin
- **Usage**: `python scripts/make_admin.py <email>`
- **Features**:
  - Simple user-to-admin conversion
  - Finds user by email
  - Updates role to admin

### **💾 Backup & Restore Scripts**

#### **`backup_privileges.py`** - Backup Privilege System
- **Purpose**: Create a backup of the entire privilege system
- **Usage**: `python scripts/backup_privileges.py [--output backup_file.json]`
- **Features**:
  - Exports all privileges, roles, and relationships
  - Creates JSON backup file
  - Includes metadata and timestamps

#### **`restore_privileges.py`** - Restore from Backup
- **Purpose**: Restore privilege system from backup
- **Usage**: `python scripts/restore_privileges.py --backup_file backup_file.json`
- **Features**:
  - Restores from JSON backup
  - Clears existing data
  - Recreates all relationships

## 🚀 Quick Start Guide

### **For New Setup:**
```bash
# 1. Initialize complete system
python scripts/aws_migration_setup.py

# 2. Check status
python scripts/migrate.py status

# 3. Make user admin
python scripts/make_admin.py user@example.com
```

### **For Adding New Privileges:**
```bash
# 1. Add new privilege
python scripts/add_new_privilege.py --name "manage_reports" --description "Manage system reports" --category "system"

# 2. Assign to role
python scripts/assign_privilege_to_role.py --privilege "manage_reports" --role "hr"

# 3. Check status
python scripts/migrate.py status
```

### **For Database Migrations:**
```bash
# 1. Run migrations
python scripts/migrate.py run

# 2. Check status
python scripts/migrate.py status

# 3. Dry run (see what would happen)
python scripts/migrate.py dry-run
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
| **Migration** | `run_migrations.py`, `migrate.py` | Database migrations |
| **Setup** | `aws_migration_setup.py`, `initialize_aws_privileges.py` | Initial setup |
| **Privileges** | `add_new_privilege.py`, `assign_privilege_to_role.py` | Privilege management |
| **Users** | `make_admin.py`, `update_user_role.py` | User management |
| **Backup** | `backup_privileges.py`, `restore_privileges.py` | Backup/restore |

## 🎯 Best Practices

### **1. Always Backup Before Major Changes**
```bash
python scripts/backup_privileges.py
```

### **2. Test on Development First**
```bash
# Test migration
python scripts/migrate.py dry-run

# Test privilege changes
python scripts/add_new_privilege.py --name "test_priv" --description "Test" --category "test"
```

### **3. Use Status Commands**
```bash
# Check migration status
python scripts/migrate.py status

# Check privilege system
python scripts/check_privileges.py
```

### **4. Document Changes**
- Keep track of what privileges you add
- Document any custom role assignments
- Update team when making changes

## 🆘 Troubleshooting

### **Migration Issues:**
```bash
# Check what's wrong
python scripts/migrate.py status

# Force run (continue on error)
python scripts/migrate.py force

# Reset if needed (DANGEROUS!)
python scripts/migrate.py reset
```

### **Privilege Issues:**
```bash
# Check current state
python scripts/check_privileges.py

# Restore from backup
python scripts/restore_privileges.py --backup_file backup.json
```

## 🎉 Summary

Your scripts directory now contains **10 essential scripts** for:
- ✅ **Database migrations** with safety and tracking
- ✅ **Privilege management** with full CRUD operations
- ✅ **User management** with role updates
- ✅ **Backup and restore** capabilities
- ✅ **AWS migration** support

All scripts are **production-ready** and **team-friendly**! 🚀
