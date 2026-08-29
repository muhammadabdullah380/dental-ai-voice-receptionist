import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())