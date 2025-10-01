# AWS Migration - Privilege System Setup Guide

This guide explains how to migrate your privilege system from Neon to AWS and manage privileges in production.

## 🚀 Migration Process

### Step 1: Database Migration

1. **Export data from Neon** (if needed):
```bash
# Export users and existing data
pg_dump "your_neon_connection_string" --data-only --table=users > users_data.sql
```

2. **Set up AWS RDS PostgreSQL**:
   - Create RDS PostgreSQL instance
   - Configure security groups
   - Update your `DATABASE_URL` in environment variables

3. **Run the migration script**:
```bash
cd backend
python scripts/aws_migration_setup.py
```

### Step 2: Initialize Privilege System

Run the complete privilege initialization:
```bash
python scripts/initialize_aws_privileges.py
```

## 📋 Complete Privilege System

### Current Privileges by Category

#### Assessment Privileges
- `take_assessment` - Take mental health assessments
- `read_own_assessments` - Read own assessment results
- `create_assessment` - Create new assessments
- `read_all_assessments` - Read all user assessments
- `delete_assessment` - Delete assessments

#### User Management Privileges
- `read_users` - Read user information
- `create_users` - Create new users
- `update_users` - Update user information
- `delete_users` - Delete users

#### System Privileges
- `system_config` - Configure system settings
- `view_analytics` - View system analytics
- `manage_roles` - Manage user roles and privileges
- `admin_access` - Access to admin panel

#### Organisation Management Privileges
- `manage_organisations` - Create, update, and delete organisations
- `read_organisations` - View organisation details and lists

#### HR Management Privileges
- `manage_complaints` - Create, read, update, and resolve complaints
- `manage_employees` - Create, read, update, and manage employee records
- `view_employee_data` - View employee assessments, complaints, and personal data

#### Research Management Privileges
- `read_researches` - Read research articles
- `manage_researches` - Manage research articles (create, update, delete)

### Role Privilege Mapping

#### User Role
- `take_assessment`
- `read_own_assessments`

#### Employee Role
- `take_assessment`
- `read_own_assessments`

#### Counsellor Role
- `take_assessment`
- `read_own_assessments`
- `read_all_assessments`
- `view_analytics`

#### HR Role
- `take_assessment`
- `read_own_assessments`
- `read_all_assessments`
- `read_users`
- `view_analytics`
- `manage_complaints`
- `manage_employees`
- `view_employee_data`
- `create_users`
- `update_users`

#### Admin Role
- **ALL privileges** (automatically assigned)

## 🔧 Adding New Privileges in Production

### Process for Adding New Privileges

1. **Create the privilege**:
```bash
python scripts/add_new_privilege.py --name "new_privilege" --description "Description" --category "category_name"
```

2. **Assign to roles**:
```bash
python scripts/assign_privilege_to_role.py --privilege "new_privilege" --role "admin"
```

3. **Verify assignment**:
```bash
python scripts/check_privileges.py
```

### Manual Process

1. **Add privilege to database**:
```sql
INSERT INTO privileges (name, description, category, is_active, created_at) 
VALUES ('new_privilege', 'Description', 'category', true, NOW());
```

2. **Assign to admin role** (admin gets all privileges automatically):
```sql
INSERT INTO role_privileges (role_id, privilege_id)
SELECT r.id, p.id 
FROM roles r, privileges p 
WHERE r.name = 'admin' AND p.name = 'new_privilege';
```

3. **Assign to specific roles**:
```sql
INSERT INTO role_privileges (role_id, privilege_id)
SELECT r.id, p.id 
FROM roles r, privileges p 
WHERE r.name = 'role_name' AND p.name = 'new_privilege';
```

## 🛠️ Management Scripts

### Available Scripts

1. **`initialize_aws_privileges.py`** - Complete privilege system setup
2. **`add_new_privilege.py`** - Add single privilege
3. **`assign_privilege_to_role.py`** - Assign privilege to role
4. **`check_privileges.py`** - Verify current privilege status
5. **`update_user_role.py`** - Change user's role
6. **`backup_privileges.py`** - Backup privilege system

### Usage Examples

```bash
# Initialize complete system
python scripts/initialize_aws_privileges.py

# Add new privilege
python scripts/add_new_privilege.py --name "manage_reports" --description "Manage system reports" --category "system"

# Assign privilege to role
python scripts/assign_privilege_to_role.py --privilege "manage_reports" --role "hr"

# Check current status
python scripts/check_privileges.py

# Update user role
python scripts/update_user_role.py --email "user@example.com" --role "admin"
```

## 🔍 Verification Commands

### Check Database Status
```sql
-- Check all privileges
SELECT name, description, category FROM privileges WHERE is_active = true ORDER BY category, name;

-- Check role assignments
SELECT r.name as role_name, p.name as privilege_name, p.category
FROM roles r
JOIN role_privileges rp ON r.id = rp.role_id
JOIN privileges p ON rp.privilege_id = p.id
ORDER BY r.name, p.category, p.name;

-- Check user roles
SELECT email, role, is_active FROM users ORDER BY role, email;
```

### API Verification
```bash
# Check admin privileges
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/admin/privileges

# Check user info
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/auth/me
```

## 🚨 Important Notes

1. **Admin Role**: Always gets ALL privileges automatically
2. **User Role**: Gets only basic assessment privileges
3. **New Privileges**: Must be manually assigned to non-admin roles
4. **Backup**: Always backup before making privilege changes
5. **Testing**: Test privilege changes in staging environment first

## 🔄 Rollback Process

If something goes wrong:

1. **Restore from backup**:
```bash
python scripts/restore_privileges.py --backup_file "backup_2024_01_01.json"
```

2. **Reinitialize system**:
```bash
python scripts/initialize_aws_privileges.py --force
```

3. **Manual fix**:
```sql
-- Remove problematic privilege
DELETE FROM role_privileges WHERE privilege_id = (SELECT id FROM privileges WHERE name = 'problematic_privilege');
DELETE FROM privileges WHERE name = 'problematic_privilege';
```

## 📞 Support

If you encounter issues:
1. Check the logs in `backend/logs/`
2. Run `python scripts/check_privileges.py` for diagnostics
3. Verify database connectivity
4. Check environment variables
