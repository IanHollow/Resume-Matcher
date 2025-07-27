import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db_session
from db import ResumeDoc
from app.schemas.pydantic.resume_doc import ResumeDocModel, ResumeDocUpdate

resume_doc_router = APIRouter()
logger = logging.getLogger(__name__)

@resume_doc_router.get("", response_model=List[ResumeDocModel], summary="List uploaded resumes")
async def list_resumes(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(ResumeDoc))
    docs = result.scalars().all()
    return [ResumeDocModel.model_validate(doc) for doc in docs]

@resume_doc_router.get("/{doc_id}", response_model=ResumeDocModel, summary="Get resume info")
async def get_resume_doc(doc_id: int, db: AsyncSession = Depends(get_db_session)):
    doc = await db.get(ResumeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return ResumeDocModel.model_validate(doc)

@resume_doc_router.patch("/{doc_id}", response_model=ResumeDocModel, summary="Update resume info")
async def update_resume_doc(doc_id: int, payload: ResumeDocUpdate, db: AsyncSession = Depends(get_db_session)):
    doc = await db.get(ResumeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    doc.display_name = payload.display_name
    await db.commit()
    await db.refresh(doc)
    return ResumeDocModel.model_validate(doc)

@resume_doc_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete resume")
async def delete_resume_doc(doc_id: int, db: AsyncSession = Depends(get_db_session)):
    doc = await db.get(ResumeDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    await db.delete(doc)
    await db.commit()
    return None
