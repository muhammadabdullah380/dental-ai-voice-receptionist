from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    detail: str
    project_type: str
    year: str


class ExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: str
    role: str
    company: str
    detail: str


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    message: str = Field(min_length=10, max_length=5000)


class ContactResponse(BaseModel):
    id: int
    message: str
    created_at: datetime
