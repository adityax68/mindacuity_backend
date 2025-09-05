from sqlalchemy.orm import Session
from app.models import User, Role, Privilege, user_privileges, role_privileges
from typing import List, Set
from fastapi import HTTPException

class RoleService:
    def __init__(self, db: Session):
        self.db = db
    
    async def initialize_default_roles_and_privileges(self):
        """Initialize default roles and privileges"""
        
        # Create default privileges
        default_privileges = [
            # Assessment privileges
            {"name": "take_assessment", "description": "Take mental health assessments", "category": "assessment"},
            {"name": "read_own_assessments", "description": "Read own assessment results", "category": "assessment"},
            {"name": "create_assessment", "description": "Create new assessments", "category": "assessment"},
            {"name": "read_all_assessments", "description": "Read all user assessments", "category": "assessment"},
            {"name": "delete_assessment", "description": "Delete assessments", "category": "assessment"},
            
            # User management privileges
            {"name": "read_users", "description": "Read user information", "category": "user_management"},
            {"name": "create_users", "description": "Create new users", "category": "user_management"},
            {"name": "update_users", "description": "Update user information", "category": "user_management"},
            {"name": "delete_users", "description": "Delete users", "category": "user_management"},
            
            # System privileges
            {"name": "system_config", "description": "Configure system settings", "category": "system"},
            {"name": "view_analytics", "description": "View system analytics", "category": "system"},
            {"name": "manage_roles", "description": "Manage user roles and privileges", "category": "system"},
            
            # Organisation management privileges
            {"name": "manage_organisations", "description": "Create, update, and delete organisations", "category": "organisation_management"},
            {"name": "read_organisations", "description": "View organisation details and lists", "category": "organisation_management"},
        ]
        
        # Create privileges if they don't exist
        for priv_data in default_privileges:
            existing_priv = self.db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                self.db.add(privilege)
        
        self.db.commit()
        
        # Create default roles
        user_role = self.db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(name="user", description="Regular user with basic access")
            self.db.add(user_role)
        
        admin_role = self.db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator with full access")
            self.db.add(admin_role)
        
        hr_role = self.db.query(Role).filter(Role.name == "hr").first()
        if not hr_role:
            hr_role = Role(name="hr", description="HR personnel with employee management access")
            self.db.add(hr_role)
        
        employee_role = self.db.query(Role).filter(Role.name == "employee").first()
        if not employee_role:
            employee_role = Role(name="employee", description="Employee with basic assessment access")
            self.db.add(employee_role)
        
        counsellor_role = self.db.query(Role).filter(Role.name == "counsellor").first()
        if not counsellor_role:
            counsellor_role = Role(name="counsellor", description="Counsellor with assessment and support access")
            self.db.add(counsellor_role)
        
        self.db.commit()
        
        # Assign privileges to roles
        await self.assign_privileges_to_role("user", [
            "take_assessment", "read_own_assessments"
        ])
        
        await self.assign_privileges_to_role("employee", [
            "take_assessment", "read_own_assessments"
        ])
        
        await self.assign_privileges_to_role("hr", [
            "take_assessment", "read_own_assessments", "read_all_assessments", "read_users", "view_analytics"
        ])
        
        await self.assign_privileges_to_role("counsellor", [
            "take_assessment", "read_own_assessments", "read_all_assessments", "view_analytics"
        ])
        
        # Admin gets all privileges
        all_privileges = self.db.query(Privilege).filter(Privilege.is_active == True).all()
        await self.assign_privileges_to_role("admin", [priv.name for priv in all_privileges])
    
    async def assign_privileges_to_role(self, role_name: str, privilege_names: List[str]):
        """Assign privileges to a role"""
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role {role_name} not found")
        
        # Clear existing privileges
        role.privileges.clear()
        
        # Add new privileges
        for priv_name in privilege_names:
            privilege = self.db.query(Privilege).filter(Privilege.name == priv_name).first()
            if privilege:
                role.privileges.append(privilege)
        
        self.db.commit()
    
    async def get_user_privileges(self, user_id: int) -> Set[str]:
        """Get all privileges for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return set()
        
        # Get role-based privileges
        role_privileges = set()
        if user.role:
            role = self.db.query(Role).filter(Role.name == user.role).first()
            if role:
                role_privileges = {priv.name for priv in role.privileges}
        
        # Get user-specific privileges (for future custom assignments)
        user_privileges = {priv.name for priv in user.privileges}
        
        # Combine both
        all_privileges = role_privileges.union(user_privileges)
        return all_privileges
    
    async def user_has_privilege(self, user_id: int, privilege_name: str) -> bool:
        """Check if user has specific privilege"""
        user_privileges = await self.get_user_privileges(user_id)
        return privilege_name in user_privileges
    
    async def require_privilege(self, privilege_name: str):
        """Decorator to require specific privilege"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Get current user from kwargs
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                has_privilege = await self.user_has_privilege(current_user.id, privilege_name)
                if not has_privilege:
                    raise HTTPException(status_code=403, detail=f"Privilege required: {privilege_name}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator 