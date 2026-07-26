from typing import Optional

from sqlalchemy.orm import Session
from app.models.client import Client

def create_client(db: Session, name: str, phone: str, email: Optional[str] = None):
    client = Client(name=name, phone=phone, email=email)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

def get_clients(db: Session):
    return db.query(Client).all()
