from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.agent import Agent
from app.models.role import Role
from app.schemas.user import UserCreate
from app.core.password import hash_password


def create_user(db: Session, user: UserCreate):

    existing_user = (
    db.query(User)
    .filter(User.email == user.email)
    .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Verificar si el rol existe
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Rol no válido"
        )

    # Crear usuario
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password),
        role_id=user.role_id,
        phone=user.phone,
        company=user.company
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Si el rol es "agente", crear automáticamente el registro en agents
    if role.name.lower() in ['agente', 'agent']:

        # Verificar si ya existe un agente con este email
        existing_agent = db.query(Agent).filter(Agent.email == user.email).first()

        if not existing_agent:
            db_agent = Agent(
                name=user.full_name,
                email=user.email,
                phone=user.phone,
                company=user.company
                # dni y zone son opcionales: se completan después
            )
            db.add(db_agent)
            db.commit()

    return db_user


def get_users(db: Session):

    return db.query(User).all()


def delete_user(db: Session, user_id: int):
    """Eliminar un usuario por ID"""

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    # Si el usuario tiene rol de agente, también eliminar el agente
    if user.role and user.role.name.lower() in ['agente', 'agent']:
        agent = db.query(Agent).filter(Agent.email == user.email).first()
        if agent:
            db.delete(agent)

    db.delete(user)
    db.commit()

    return {"message": "Usuario eliminado correctamente"}