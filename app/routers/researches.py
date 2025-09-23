from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import ResearchCRUD
from app.schemas import Research, ResearchListResponse
from typing import List

router = APIRouter(prefix="/researches", tags=["researches"])

@router.get("/", response_model=ResearchListResponse)
async def get_researches(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get all active researches with pagination (Public endpoint)"""
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

@router.get("/{research_id}", response_model=Research)
async def get_research(
    research_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific research by ID (Public endpoint)"""
    research = ResearchCRUD.get_research_by_id(db, research_id)
    if not research or not research.is_active:
        raise HTTPException(status_code=404, detail="Research not found")
    
    return research
