from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User, Role, Privilege, Employee as EmployeeModel, Organisation
from app.schemas import UserResponse, RoleResponse, PrivilegeResponse, UserRoleUpdate, OrganisationCreate, OrganisationResponse, Employee, ResearchCreate, ResearchUpdate, Research, ResearchListResponse
from app.services.role_service import RoleService
# Removed cache services - using database indexes instead
from app.crud import OrganisationCRUD, ResearchCRUD
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])

def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)

@router.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all users (Admin only) - Optimized with eager loading and database indexes"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_users")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Get total count efficiently
    total_count = db.query(User).count()
    
    # Single query with eager loading to avoid N+1 problem
    from sqlalchemy.orm import joinedload
    
    users = db.query(User)\
        .options(joinedload(User.privileges))\
        .order_by(User.created_at.desc())\
        .offset(skip).limit(limit).all()
    
    # Build response efficiently
    user_responses = []
    for user in users:
        # Get user-specific privileges (already loaded via eager loading)
        user_privileges = {priv.name for priv in user.privileges}
        
        user_responses.append(UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            privileges=list(user_privileges),
            is_active=user.is_active,
            age=user.age,
            country=user.country,
            state=user.state,
            city=user.city,
            pincode=user.pincode,
            created_at=user.created_at
        ))
    
    # Return pagination metadata
    result = {
        "users": user_responses,
        "pagination": {
            "total": total_count,
            "page": (skip // limit) + 1,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
    }
    
    return result

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
    """Get all roles (Admin only) - Optimized with eager loading"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_roles")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # OPTIMIZED: Single query with eager loading to avoid N+1 problem
    from sqlalchemy.orm import joinedload
    
    roles = db.query(Role)\
        .options(joinedload(Role.privileges))\
        .filter(Role.is_active == True).all()
    
    # Build response efficiently - privileges are already loaded
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

@router.get("/test-analytics")
async def get_test_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get test analytics (Admin only) - NEON DB OPTIMIZED with aggressive caching"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_all_assessments")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Using database indexes for performance instead of caching
    
    try:
        from app.models import ClinicalAssessment, Employee as EmployeeModel
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # OPTIMIZATION 1: Use simple, fast queries instead of complex CTEs
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Fast individual queries (much faster than complex CTEs for small datasets)
        total_tests = db.query(ClinicalAssessment).count()
        
        recent_tests = db.query(ClinicalAssessment).filter(
            ClinicalAssessment.created_at >= thirty_days_ago
        ).count()
        
        employee_tests = db.query(ClinicalAssessment).join(
            EmployeeModel, ClinicalAssessment.user_id == EmployeeModel.user_id
        ).count()
        
        # Get tests by type
        tests_by_type = db.query(
            ClinicalAssessment.assessment_type,
            func.count(ClinicalAssessment.id).label('count')
        ).group_by(ClinicalAssessment.assessment_type).all()
        
        # Get tests by organization
        tests_by_org = db.query(
            EmployeeModel.org_id,
            func.count(ClinicalAssessment.id).label('count')
        ).join(ClinicalAssessment, EmployeeModel.user_id == ClinicalAssessment.user_id).group_by(EmployeeModel.org_id).all()
        
        # Get tests by severity
        tests_by_severity = db.query(
            ClinicalAssessment.severity_level,
            func.count(ClinicalAssessment.id).label('count')
        ).filter(ClinicalAssessment.severity_level.isnot(None)).group_by(ClinicalAssessment.severity_level).all()
        
        result = {
            "total_tests": total_tests,
            "employee_tests": employee_tests,
            "recent_tests": recent_tests,
            "tests_by_type": [{"type": t[0], "count": t[1]} for t in tests_by_type],
            "tests_by_organization": [{"org_id": t[0], "count": t[1]} for t in tests_by_org],
            "tests_by_severity": [{"severity": t[0], "count": t[1]} for t in tests_by_severity]
        }
        
        # Result returned directly - no caching needed
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch test analytics: {str(e)}")

@router.get("/organisations")
async def get_all_organisations(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all organisations (Admin only) - NEON DB OPTIMIZED with aggressive caching"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_organisations")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Using database indexes for performance instead of caching
    
    # OPTIMIZATION 1: Use efficient query without count for better performance
    organisations = db.query(Organisation)\
        .order_by(Organisation.created_at.desc())\
        .offset(skip).limit(limit).all()
    
    # OPTIMIZATION 2: Estimate total count based on current page (faster than full count)
    estimated_total = len(organisations) + skip if len(organisations) == limit else len(organisations) + skip
    
    # OPTIMIZATION 3: Convert to response format efficiently
    from app.schemas import OrganisationResponse
    organisation_responses = [OrganisationResponse(
        id=org.id,
        org_id=org.org_id,
        org_name=org.org_name,
        hr_email=org.hr_email,
        created_at=org.created_at,
        updated_at=org.updated_at
    ) for org in organisations]
    
    # OPTIMIZATION 4: Return pagination metadata with estimated total
    result = {
        "organisations": organisation_responses,
        "pagination": {
            "total": estimated_total,
            "page": (skip // limit) + 1,
            "limit": limit,
            "total_pages": (estimated_total + limit - 1) // limit if estimated_total > 0 else 1
        }
    }
    
    # Result returned directly - no caching needed
    
    return result

# Removed cache-related endpoints - using database indexes instead

@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get admin statistics (Admin only)"""
    # Check if user has admin privileges
    has_privilege = await role_service.user_has_privilege(current_user.id, "view_analytics")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    try:
        # Import models for counting
        from app.models import User, Employee, Organisation
        
        # Count records in each table
        total_users = db.query(User).count()
        total_employees = db.query(Employee).count()
        total_organizations = db.query(Organisation).count()
        
        return {
            "totalUsers": total_users,
            "totalEmployees": total_employees,
            "totalOrganizations": total_organizations
        }
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error fetching admin stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/weekly-users")
async def get_weekly_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get monthly user registration statistics (Admin only)"""
    # Check if user has admin privileges
    has_privilege = await role_service.user_has_privilege(current_user.id, "view_analytics")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    try:
        # Import models and functions for date handling
        from app.models import User
        from sqlalchemy import func, text
        from datetime import datetime, timedelta
        
        # Get the last 12 months of data
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        
        # Query to get monthly user registration data
        # Using PostgreSQL's DATE_TRUNC function to group by month
        query = text("""
            SELECT 
                DATE_TRUNC('month', created_at) as month_start,
                COUNT(*) as new_users
            FROM users 
            WHERE created_at >= :start_date
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY DATE_TRUNC('month', created_at)
        """)
        
        result = db.execute(query, {"start_date": twelve_months_ago}).fetchall()
        
        # Format the data according to the required structure
        weekly_data = []
        month_number = 1
        
        for row in result:
            weekly_data.append({
                "week": f"Week {month_number}",
                "newUsers": row.new_users
            })
            month_number += 1
        
        # If no data found, return empty array
        if not weekly_data:
            weekly_data = []
        
        return {
            "weeklyData": weekly_data
        }
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error fetching weekly user stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/search")
async def search_users(
    email: str = None,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Search users by email (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_users")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    query = db.query(User)
    
    if email:
        # Use case-insensitive search with proper indexing
        query = query.filter(User.email.ilike(f"%{email.lower()}%"))
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
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

@router.get("/employees")
async def get_all_employees(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all employees (Admin only) - NEON DB OPTIMIZED with aggressive caching"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_employees")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Using database indexes for performance instead of caching
    
    # OPTIMIZATION 1: Use efficient query without count for better performance
    from sqlalchemy.orm import joinedload
    
    employees = db.query(EmployeeModel)\
        .options(
            # Eager load user data
            joinedload(EmployeeModel.user)
        )\
        .order_by(EmployeeModel.created_at.desc())\
        .offset(skip).limit(limit).all()
    
    # OPTIMIZATION 2: Estimate total count based on current page (faster than full count)
    estimated_total = len(employees) + skip if len(employees) == limit else len(employees) + skip
    
    # OPTIMIZATION 3: Return pagination metadata with estimated total
    result = {
        "employees": employees,
        "pagination": {
            "total": estimated_total,
            "page": (skip // limit) + 1,
            "limit": limit,
            "total_pages": (estimated_total + limit - 1) // limit if estimated_total > 0 else 1
        }
    }
    
    # Result returned directly - no caching needed
    
    return result

@router.get("/employees/search")
async def search_employees(
    employee_code: str = None,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Search employees by employee code (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_employees")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    query = db.query(EmployeeModel)
    
    if employee_code:
        # Use case-insensitive search with proper indexing
        query = query.filter(EmployeeModel.employee_code.ilike(f"%{employee_code.upper()}%"))
    
    employees = query.order_by(EmployeeModel.created_at.desc()).offset(skip).limit(limit).all()
    return employees

@router.get("/organisations/search")
async def search_organisations(
    org_id: str = None,
    hr_email: str = None,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Search organisations by org ID or HR email (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_organisations")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    query = db.query(Organisation)
    
    if org_id:
        # Use case-insensitive search with proper indexing
        query = query.filter(Organisation.org_id.ilike(f"%{org_id.upper()}%"))
    
    if hr_email:
        # Use case-insensitive search with proper indexing
        query = query.filter(Organisation.hr_email.ilike(f"%{hr_email.lower()}%"))
    
    organisations = query.order_by(Organisation.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to response format
    from app.schemas import OrganisationResponse
    return [OrganisationResponse(
        id=org.id,
        org_id=org.org_id,
        org_name=org.org_name,
        hr_email=org.hr_email,
        created_at=org.created_at,
        updated_at=org.updated_at
    ) for org in organisations]

# Research Management Endpoints
@router.post("/researches", response_model=Research)
async def create_research(
    research_data: ResearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Create a new research entry (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_researches")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    try:
        # Create research entry with pre-uploaded thumbnail URL
        research = ResearchCRUD.create_research(
            db=db,
            title=research_data.title,
            description=research_data.description,
            thumbnail_url=research_data.thumbnail_url,
            source_url=research_data.source_url
        )
        
        return research
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create research: {str(e)}")

@router.post("/researches/upload")
async def upload_research_thumbnail(
    thumbnail_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """Upload research thumbnail to S3 (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_researches")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    try:
        # Upload thumbnail to S3
        from app.services.s3_service import s3_service
        thumbnail_url = await s3_service.upload_research_thumbnail(thumbnail_file)
        
        return {"thumbnail_url": thumbnail_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload thumbnail: {str(e)}")

@router.get("/researches", response_model=ResearchListResponse)
async def get_researches(
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all researches with pagination (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "read_researches")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    skip = (page - 1) * per_page
    researches = ResearchCRUD.get_researches(db, skip=skip, limit=per_page, active_only=True)
    total = ResearchCRUD.get_researches_count(db, active_only=True)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return ResearchListResponse(
        researches=researches,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.put("/researches/{research_id}", response_model=Research)
async def update_research(
    research_id: int,
    research_data: ResearchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Update a research entry (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_researches")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Get existing research
    research = ResearchCRUD.get_research_by_id(db, research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    
    # Update research
    update_data = research_data.dict(exclude_unset=True)
    updated_research = ResearchCRUD.update_research(db, research_id, **update_data)
    
    return updated_research

@router.delete("/researches/{research_id}")
async def delete_research(
    research_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """Delete a research entry (Admin only)"""
    has_privilege = await role_service.user_has_privilege(current_user.id, "manage_researches")
    if not has_privilege:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    # Get existing research
    research = ResearchCRUD.get_research_by_id(db, research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    
    # Delete research (soft delete)
    success = ResearchCRUD.delete_research(db, research_id)
    
    if success:
        # Also delete the thumbnail from S3
        try:
            from app.services.s3_service import s3_service
            await s3_service.delete_research_thumbnail(research.thumbnail_url)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to delete thumbnail from S3: {e}")
        
        return {"message": "Research deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete research")