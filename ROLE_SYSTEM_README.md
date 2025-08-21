# Role-Based Access Control (RBAC) System

This document explains how to use the new role-based access control system implemented in your Mind Acuity backend.

## Overview

The system now supports two roles:
- **User**: Regular users with basic assessment privileges
- **Admin**: Administrators with full system access

## Database Changes

The following new tables have been added:
- `roles`: Defines available roles
- `privileges`: Defines system permissions
- `role_privileges`: Links roles to privileges
- `user_privileges`: Links users to specific privileges (for future use)

## Setup Instructions

### 1. Run Database Migration

```bash
cd backend
python scripts/migrate_to_roles.py
```

This will:
- Create new tables
- Initialize default roles and privileges
- Update existing users to have 'user' role

### 2. Make a User an Admin

```bash
cd backend
python scripts/make_admin.py <email>
```

Example:
```bash
python scripts/make_admin.py admin@example.com
```

### 3. Initialize Roles (Optional)

If you need to reinitialize roles and privileges:

```bash
# Make a POST request to /api/v1/admin/initialize-roles
# Requires admin privileges
```

## API Endpoints

### Admin Endpoints

All admin endpoints require authentication and admin privileges:

- `GET /api/v1/admin/users` - List all users
- `PUT /api/v1/admin/users/{user_id}/role` - Update user role
- `GET /api/v1/admin/roles` - List all roles
- `GET /api/v1/admin/privileges` - List all privileges
- `POST /api/v1/admin/initialize-roles` - Initialize roles and privileges
- `GET /api/v1/admin/analytics` - Get system analytics

### Updated Auth Endpoints

- `POST /api/v1/auth/login` - Now returns user with role and privileges
- `GET /api/v1/auth/me` - Now returns user with role and privileges

## Privileges

### Assessment Privileges
- `take_assessment` - Take mental health assessments
- `read_own_assessments` - Read own assessment results
- `create_assessment` - Create new assessments
- `read_all_assessments` - Read all user assessments
- `delete_assessment` - Delete assessments

### User Management Privileges
- `read_users` - Read user information
- `create_users` - Create new users
- `update_users` - Update user information
- `delete_users` - Delete users

### System Privileges
- `system_config` - Configure system settings
- `view_analytics` - View system analytics
- `manage_roles` - Manage user roles and privileges

## Role Privilege Mapping

### User Role
- `take_assessment`
- `read_own_assessments`

### Admin Role
- All privileges automatically assigned

## Frontend Integration

The frontend now includes:
- Role-based navigation (Admin Panel button for admins)
- Admin Dashboard component
- Updated AuthContext with privilege checking

## Adding New Roles

To add new roles in the future:

1. Add the role to the database:
```python
new_role = Role(name="therapist", description="Mental health therapist")
db.add(new_role)
```

2. Assign privileges:
```python
await role_service.assign_privileges_to_role("therapist", [
    "read_patient_assessments",
    "create_treatment_plans"
])
```

3. Update the frontend to handle the new role

## Security Notes

- All admin endpoints require authentication
- Privilege checks are performed at the API level
- Role information is included in JWT tokens
- Frontend shows/hides features based on user privileges

## Troubleshooting

### Common Issues

1. **Migration fails**: Ensure database is accessible and user has proper permissions
2. **Admin access denied**: Check if user has admin role and proper privileges
3. **Privileges not showing**: Run the initialize-roles endpoint or check database

### Debug Commands

```bash
# Check user roles in database
psql -d your_database -c "SELECT email, role FROM users;"

# Check role privileges
psql -d your_database -c "SELECT r.name, p.name FROM roles r JOIN role_privileges rp ON r.id = rp.role_id JOIN privileges p ON rp.privilege_id = p.id;"
```

## Future Enhancements

- Custom privilege assignments per user
- Role hierarchy system
- Audit logging for privilege changes
- Dynamic privilege loading
- Role-based UI components 