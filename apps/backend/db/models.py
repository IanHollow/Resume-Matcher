from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, UniqueConstraint
from sqlalchemy.types import JSON
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ResumeDoc(Base):
    __tablename__ = "resumedoc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hash = Column(String(64), nullable=False)
    model_hash = Column(String(64), nullable=False)
    filename = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    upload_dt = Column(DateTime(timezone=True), server_default=sa.func.now())
    parsed_json = Column(JSON, nullable=True)
    vector = Column(LargeBinary, nullable=True)

    __table_args__ = (
        UniqueConstraint("hash", "model_hash", name="uq_resume_hash_model"),
    )

