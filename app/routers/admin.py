from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User, Role, Privilege
from app.schemas import UserResponse, RoleResponse, PrivilegeResponse, UserRoleUpdate, OrganisationCreate, OrganisationResponse
from app.services.role_service import RoleService
from app.crud import OrganisationCRUD
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])

def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all users (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_users")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    # Get privileges for each user
    user_responses = []
    for user in users:
        privileges = await role_service.get_user_privileges(user.id)
        user_responses.append(UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            privileges=list(privileges),
            is_active=user.is_active,
            created_at=user.created_at
        ))
    
    return user_responses

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Update user role (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "update_users")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    valid_roles = ["user", "admin"]
    if role_update.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    user.role = role_update.role
    db.commit()
    
    return {"message": f"User role updated to {role_update.role}"}

@router.get("/roles", response_model=List[RoleResponse])
async def get_all_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all roles (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_roles")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    roles = db.query(Role).filter(Role.is_active == True).all()
    
    role_responses = []
    for role in roles:
        privileges = [priv.name for priv in role.privileges]
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            privileges=privileges
        ))
    
    return role_responses

@router.get("/privileges", response_model=List[PrivilegeResponse])
async def get_all_privileges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all privileges (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_roles")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
    return privileges

@router.post("/initialize-roles")
async def initialize_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Initialize default roles and privileges (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_roles")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    try:
        await role_service.initialize_default_roles_and_privileges()
        return {"message": "Roles and privileges initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize roles: {str(e)}")

@router.get("/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get system analytics (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "view_analytics")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Get basic analytics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "user_distribution": {
            "user": db.query(User).filter(User.role == "user").count(),
            "admin": admin_users
        }
    }

@router.post("/organisations", response_model=OrganisationResponse)
async def create_organisation(
    organisation: OrganisationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Create a new organisation (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_organisations")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Check if organisation with same email already exists
    existing_org = OrganisationCRUD.get_organisation_by_email(db, organisation.hr_email)
    if existing_org:
        raise HTTPException(status_code=400, detail="Organisation with this HR email already exists")
    
    try:
        # Create organisation
        new_organisation = OrganisationCRUD.create_organisation(
            db=db,
            org_name=organisation.org_name,
            hr_email=organisation.hr_email
        )
        
        return new_organisation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create organisation: {str(e)}")

@router.get("/organisations", response_model=List[OrganisationResponse])
async def get_all_organisations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all organisations (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_organisations")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    organisations = OrganisationCRUD.get_all_organisations(db, skip=skip, limit=limit)
    return organisations