from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.agent import Agent
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate
from app.core.password import hash_password
from app.services.user_email_service import send_welcome_email


def create_user(
    db: Session,
    user: UserCreate,
    background_tasks: Optional[BackgroundTasks] = None
):

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

    # Correo de bienvenida con las credenciales. user.password es el texto plano
    # recibido del cliente, disponible solo en este punto (nunca se persiste así).
    # send_welcome_email captura sus propios errores: no interrumpe la creación.
    if background_tasks is not None:
        background_tasks.add_task(
            send_welcome_email,
            email=db_user.email,
            full_name=db_user.full_name,
            password=user.password,
            role_name=role.name,
        )
    else:
        send_welcome_email(
            email=db_user.email,
            full_name=db_user.full_name,
            password=user.password,
            role_name=role.name,
        )

    return db_user


def update_user(db: Session, user_id: int, data: UserUpdate):
    """Actualiza nombre, teléfono, empresa y rol de un usuario.

    El email no es editable, así que la ficha de Agent (vinculada por email)
    nunca queda huérfana: solo se sincronizan sus datos de contacto.
    """

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    role = db.query(Role).filter(Role.id == data.role_id).first()

    if not role:
        raise HTTPException(
            status_code=400,
            detail="Rol no válido"
        )

    user.full_name = data.full_name
    user.role_id = data.role_id
    user.phone = data.phone
    user.company = data.company

    agent = db.query(Agent).filter(Agent.email == user.email).first()

    if role.name.lower() in ['agente', 'agent']:

        if agent:
            # Mantener sincronizados los datos de contacto de la ficha
            agent.name = data.full_name
            agent.phone = data.phone
            agent.company = data.company
        else:
            # El usuario pasa a ser agente: crear la ficha que faltaba
            db.add(Agent(
                name=data.full_name,
                email=user.email,
                phone=data.phone,
                company=data.company
            ))

    db.commit()
    db.refresh(user)

    return user


def change_user_password(db: Session, user_id: int, new_password: str):
    """Establece una nueva contraseña. Pensado para uso administrativo:
    no exige la contraseña actual."""

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    user.hashed_password = hash_password(new_password)

    db.commit()
    db.refresh(user)

    return user


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