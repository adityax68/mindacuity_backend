from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Role, Privilege, user_privileges, role_privileges
from typing import List, Set
from fastapi import HTTPException

class RoleService:
    def __init__(self, db: AsyncSession):
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
        ]
        
        # Create privileges if they don't exist
        for priv_data in default_privileges:
            result = await self.db.execute(select(Privilege).where(Privilege.name == priv_data["name"]))
            existing_priv = result.scalar_one_or_none()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                self.db.add(privilege)
        
        await self.db.commit()
        
        # Create default roles
        result = await self.db.execute(select(Role).where(Role.name == "user"))
        user_role = result.scalar_one_or_none()
        if not user_role:
            user_role = Role(name="user", description="Regular user with basic access")
            self.db.add(user_role)
        
        result = await self.db.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator with full access")
            self.db.add(admin_role)
        
        await self.db.commit()
        
        # Assign privileges to roles
        await self.assign_privileges_to_role("user", [
            "take_assessment", "read_own_assessments"
        ])
        
        # Admin gets all privileges
        result = await self.db.execute(select(Privilege).where(Privilege.is_active == True))
        all_privileges = result.scalars().all()
        await self.assign_privileges_to_role("admin", [priv.name for priv in all_privileges])
    
    async def assign_privileges_to_role(self, role_name: str, privilege_names: List[str]):
        """Assign privileges to a role"""
        result = await self.db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            raise ValueError(f"Role {role_name} not found")
        
        # Clear existing privileges
        role.privileges.clear()
        
        # Add new privileges
        for priv_name in privilege_names:
            result = await self.db.execute(select(Privilege).where(Privilege.name == priv_name))
            privilege = result.scalar_one_or_none()
            if privilege:
                role.privileges.append(privilege)
        
        await self.db.commit()
    
    async def get_user_privileges(self, user_id: int) -> Set[str]:
        """Get all privileges for a user"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return set()
        
        # Get role-based privileges
        role_privileges = set()
        if user.role:
            result = await self.db.execute(select(Role).where(Role.name == user.role))
            role = result.scalar_one_or_none()
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