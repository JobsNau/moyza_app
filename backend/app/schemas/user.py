from typing import Optional

from pydantic import BaseModel, EmailStr

from app.schemas.role import RoleResponse


class UserCreate(BaseModel):

    email: EmailStr

    full_name: str

    password: str

    role_id: int

    phone: Optional[str] = None

    company: Optional[str] = None


class UserResponse(BaseModel):

    id: int

    email: EmailStr

    full_name: str

    is_active: bool

    role_id: int

    phone: Optional[str] = None

    company: Optional[str] = None

    class Config:
        from_attributes = True