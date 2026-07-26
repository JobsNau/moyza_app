from typing import Optional

from pydantic import BaseModel, EmailStr

class ClientCreate(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None

class ClientResponse(ClientCreate):
    id: int

    class Config:
        from_attributes = True
