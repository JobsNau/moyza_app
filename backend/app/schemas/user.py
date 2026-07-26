import re

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.role import RoleResponse


# Permite dígitos, espacios y los separadores habituales: +34 600 123 456, (01) 555-1234
PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]{6,20}$")


class UserCreate(BaseModel):

    email: EmailStr

    full_name: str

    password: str

    role_id: int

    phone: Optional[str] = None

    company: Optional[str] = None

    @field_validator("phone", "company")
    @classmethod
    def empty_to_none(cls, value: Optional[str]) -> Optional[str]:
        """Un input HTML vacío llega como cadena vacía: se normaliza a None."""

        if value is None:
            return None

        return value.strip() or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:

        if value is None:
            return None

        if not PHONE_PATTERN.match(value):
            raise ValueError(
                "Teléfono no válido: usa solo números, espacios y los signos + ( ) - ."
            )

        return value


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