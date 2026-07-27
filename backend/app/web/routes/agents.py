import os
import base64
import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends
from fastapi import Form
from fastapi import File
from fastapi import UploadFile

from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.db.deps import get_db

from app.models.agent import Agent
from app.models.property import Property

from app.web.dependencies.auth import is_admin, get_agent_from_user


router = APIRouter()
logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory="app/web/templates"
)


def _clean(value):
    """Normaliza un campo opcional de formulario: '' o espacios -> None."""
    if value is None:
        return None

    value = value.strip()

    return value or None


@router.get("/agents", response_class=HTMLResponse)
async def agents_page(
    request: Request,
    db: Session = Depends(get_db)
):
    error = request.query_params.get("error")

    current_user = request.state.user

    # Si es admin, mostrar todos los agentes
    # Si es agente, mostrar solo su propio perfil
    if is_admin(current_user):
        agents = db.query(Agent).all()
    else:
        agent = get_agent_from_user(current_user, db)
        agents = [agent] if agent else []

    return templates.TemplateResponse(
        request=request,
        name="agents/home.html",
        context={
            "request": request,
            "agents": agents,
            "current_user": current_user,
            "error": error
        }
    )


@router.post("/agents/create")
async def create_agent(
        request: Request,
        name: str = Form(None),
        email: str = Form(None),
        dni: str = Form(None),
        phone: str = Form(None),
        zone: str = Form(None),
        company: str = Form(None),
        db: Session = Depends(get_db)
    ):

    # Solo el nombre es obligatorio; el resto es opcional.
    # Se normaliza aquí para no depender de la validación de FastAPI, que
    # devolvería un 422 sin plantilla (la página "se caía").
    name = (name or "").strip()
    email = _clean(email)

    if not name:
        return RedirectResponse(
            url="/agents?error=missing_fields",
            status_code=302
        )

    # El correo solo debe ser único cuando se indica
    if email:

        existing_agent = db.query(Agent).filter(
            Agent.email == email
        ).first()

        if existing_agent:
            return RedirectResponse(
                url="/agents?error=email_exists",
                status_code=302
            )

    try:
        agent = Agent(
            name=name,
            email=email,
            dni=_clean(dni),
            phone=_clean(phone),
            zone=_clean(zone),
            company=_clean(company)
        )

        db.add(agent)

        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Error creando agente: email=%s", email)
        return RedirectResponse(
            url="/agents?error=save_failed",
            status_code=302
        )

    return RedirectResponse(
        url="/agents",
        status_code=302
    )


@router.post("/agents/update")
async def update_agent(
    request: Request,
    agent_id: str = Form(None),
    name: str = Form(None),
    email: str = Form(None),
    dni: str = Form(None),
    phone: str = Form(None),
    zone: str = Form(None),
    company: str = Form(None),
    db: Session = Depends(get_db)
):

    try:
        agent_id = int(agent_id)
    except (TypeError, ValueError):
        return RedirectResponse(
            url="/agents?error=missing_fields",
            status_code=302
        )

    name = (name or "").strip()
    email = _clean(email)

    if not name:
        return RedirectResponse(
            url="/agents?error=missing_fields",
            status_code=302
        )

    agent = db.query(Agent).filter(
        Agent.id == agent_id
    ).first()

    if not agent:
        return RedirectResponse(
            url="/agents?error=agent_not_found",
            status_code=302
        )

    # El correo debe seguir siendo único entre agentes, cuando se indica
    if email:

        email_owner = db.query(Agent).filter(
            Agent.email == email,
            Agent.id != agent_id
        ).first()

        if email_owner:
            return RedirectResponse(
                url="/agents?error=email_exists",
                status_code=302
            )

    try:
        agent.name = name
        agent.email = email
        agent.dni = _clean(dni)
        agent.phone = _clean(phone)
        agent.zone = _clean(zone)
        agent.company = _clean(company)

        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Error actualizando agente: agent_id=%s", agent_id)
        return RedirectResponse(
            url="/agents?error=save_failed",
            status_code=302
        )

    return RedirectResponse(
        url="/agents",
        status_code=302
    )


@router.post("/agents/delete/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):

    properties = db.query(Property).filter(
        Property.agent_id == agent_id
    ).count()

    if properties > 0:
        return RedirectResponse(
            url="/agents?error=in_use",
            status_code=302
        )

    agent = db.query(Agent).filter(
        Agent.id == agent_id
    ).first()

    if agent:

        db.delete(agent)

        db.commit()

    return RedirectResponse(
        url="/agents",
        status_code=302
    )


@router.post("/agents/{agent_id}/upload-signature")
async def upload_agent_signature(
    agent_id: int,
    signature_data: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para subir la firma del agente.
    signature_data viene como base64 string desde el canvas del frontend
    """
    agent = db.query(Agent).filter(
        Agent.id == agent_id
    ).first()

    if not agent:
        return RedirectResponse(
            url="/agents?error=agent_not_found",
            status_code=302
        )

    # Crear directorio de firmas si no existe
    signatures_dir = "storage/signatures/agents"
    os.makedirs(signatures_dir, exist_ok=True)

    # Decodificar base64
    if signature_data.startswith("data:image/png;base64,"):
        signature_data = signature_data.replace("data:image/png;base64,", "")

    signature_bytes = base64.b64decode(signature_data)

    # Generar nombre de archivo único
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"agent_{agent_id}_{timestamp}.png"
    filepath = os.path.join(signatures_dir, filename)

    # Guardar archivo
    with open(filepath, "wb") as f:
        f.write(signature_bytes)

    # Actualizar agente
    agent.signature_filename = filename
    agent.signature_filepath = filepath
    agent.signature_uploaded_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(
        url="/agents",
        status_code=302
    )