import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends
from fastapi import Form

from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.core.constants import AlertType, PropertyStatus
from app.core.constants import AlertPriority
from app.core.constants import AlertStatus
from app.core.constants import FollowUpActionType
from app.db.deps import get_db

from app.models.property_alert import PropertyAlert
from app.models.alert_follow_up import AlertFollowUp
from app.models.property import Property
from app.models.agent import Agent
from app.models.user import User

from app.web.utils.flash import set_flash
from app.web.dependencies.auth import is_admin, get_agent_from_user, require_admin_role


router = APIRouter()
logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory="app/web/templates"
)

# Estados que se consideran "abiertos" para la cola secuencial del agente
OPEN_ALERT_STATUSES = [AlertStatus.PENDING, AlertStatus.IN_PROGRESS]


def get_active_alert_id(agent_id: int, db: Session):
    """Devuelve el id de la alerta 'activa' del agente (cola FIFO).

    La activa es la alerta abierta más antigua (por fecha de creación, y en
    empate por id). El agente solo puede trabajar/cerrar esta; el resto quedan
    bloqueadas hasta que la cierre. Retorna None si no tiene alertas abiertas.
    """
    active = (
        db.query(PropertyAlert)
        .filter(
            PropertyAlert.agent_id == agent_id,
            PropertyAlert.status.in_(OPEN_ALERT_STATUSES),
        )
        .order_by(PropertyAlert.created_at.asc(), PropertyAlert.id.asc())
        .first()
    )
    return active.id if active else None


def is_alert_locked_for_user(alert: PropertyAlert, current_user, db: Session) -> bool:
    """True si la cola secuencial impide al usuario actuar sobre esta alerta.

    El admin nunca está bloqueado. Un agente está bloqueado si la alerta no es
    su alerta activa (la más antigua abierta).
    """
    if is_admin(current_user):
        return False

    agent = get_agent_from_user(current_user, db)
    if not agent:
        return False

    active_id = get_active_alert_id(agent.id, db)
    return active_id is not None and alert.id != active_id


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lista de alertas - Admin ve todas, agentes solo las suyas"""

    current_user = request.state.user

    # Base query
    base_query = db.query(PropertyAlert).join(Property).join(Agent)

    # Si es agente, filtrar solo sus alertas
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if agent:
            base_query = base_query.filter(PropertyAlert.agent_id == agent.id)
        else:
            # Si no es admin y no tiene agente asociado, no mostrar nada
            base_query = base_query.filter(PropertyAlert.id == -1)

    # Ordenar por prioridad y fecha
    alerts = base_query.order_by(
        case(
            (PropertyAlert.priority == AlertPriority.ALTA, 1),
            (PropertyAlert.priority == AlertPriority.NORMAL, 2),
            (PropertyAlert.priority == AlertPriority.BAJA, 3),
            else_=4
        ),
        PropertyAlert.created_at.desc()
    ).all()

    # Contar alertas por estado
    pending_count = base_query.filter(PropertyAlert.status == AlertStatus.PENDING).count()
    in_progress_count = base_query.filter(PropertyAlert.status == AlertStatus.IN_PROGRESS).count()
    completed_count = base_query.filter(PropertyAlert.status == AlertStatus.COMPLETED).count()

    # Obtener propiedades y agentes para el formulario de creación (solo admin)
    properties = []
    agents = []
    if is_admin(current_user):
        properties = db.query(Property).filter(Property.status != PropertyStatus.ARCHIVED)
        agents = db.query(Agent).all()

    # Cola secuencial: para un agente, solo la alerta activa (más antigua abierta)
    # es accionable; el resto se muestran bloqueadas. El admin no tiene cola.
    active_alert_id = None
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if agent:
            active_alert_id = get_active_alert_id(agent.id, db)

    return templates.TemplateResponse(
        request=request,
        name="alerts/list.html",
        context={
            "request": request,
            "alerts": alerts,
            "current_user": current_user,
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "completed_count": completed_count,
            "properties": properties,
            "agents": agents,
            "active_alert_id": active_alert_id,
            "is_admin": is_admin(current_user),
            "AlertType": AlertType,
            "AlertPriority": AlertPriority,
            "AlertStatus": AlertStatus
        }
    )


@router.get("/alerts/{alert_id}", response_class=HTMLResponse)
async def alert_detail(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Detalle de una alerta con historial de seguimientos"""

    current_user = request.state.user

    alert = db.query(PropertyAlert).filter(PropertyAlert.id == alert_id).first()

    if not alert:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Alerta no encontrada")
        return response

    # Verificar permisos: admin puede ver todo, agente solo sus alertas
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if not agent or alert.agent_id != agent.id:
            response = RedirectResponse(url="/alerts", status_code=302)
            set_flash(response, "error", "No tienes permisos para ver esta alerta")
            return response

    # Obtener seguimientos ordenados por fecha
    follow_ups = db.query(AlertFollowUp).filter(
        AlertFollowUp.alert_id == alert_id
    ).order_by(AlertFollowUp.created_at.desc()).all()

    # Cola secuencial: si esta no es la alerta activa del agente, se bloquean
    # las acciones (marcar leída, seguimiento, completar).
    alert_locked = is_alert_locked_for_user(alert, current_user, db)

    return templates.TemplateResponse(
        request=request,
        name="alerts/detail.html",
        context={
            "request": request,
            "alert": alert,
            "follow_ups": follow_ups,
            "current_user": current_user,
            "alert_locked": alert_locked,
            "FollowUpActionType": FollowUpActionType,
            "AlertStatus": AlertStatus
        }
    )


@router.post("/alerts/create")
async def create_alert(
    request: Request,
    property_id: int = Form(...),
    lead_name: str = Form(...),
    lead_phone: str = Form(None),
    lead_email: str = Form(None),
    source: str = Form(None),
    alert_type: str = Form(AlertType.LEAD_INTERES),
    message: str = Form(None),
    priority: str = Form(AlertPriority.NORMAL),
    db: Session = Depends(get_db)
):
    """Crear nueva alerta (solo admin)"""

    current_user = request.state.user

    if not is_admin(current_user):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Solo administradores pueden crear alertas")
        return response

    # Obtener la propiedad y su agente
    property_item = db.query(Property).filter(Property.id == property_id).first()

    if not property_item:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Propiedad no encontrada")
        return response

    if not property_item.agent_id:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "La propiedad no tiene agente asignado")
        return response

    try:
        alert = PropertyAlert(
            property_id=property_id,
            agent_id=property_item.agent_id,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_email=lead_email,
            source=source,
            alert_type=alert_type,
            message=message,
            priority=priority,
            status=AlertStatus.PENDING,
            created_by=current_user.id
        )

        db.add(alert)
        db.commit()

        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "success", f"Alerta creada para {lead_name}")
        return response

    except Exception:
        db.rollback()
        logger.exception("Error creando alerta: property_id=%s", property_id)
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Ocurrió un error al crear la alerta")
        return response


@router.post("/alerts/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Marcar alerta como leída"""

    current_user = request.state.user

    alert = db.query(PropertyAlert).filter(PropertyAlert.id == alert_id).first()

    if not alert:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Alerta no encontrada")
        return response

    # Verificar permisos
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if not agent or alert.agent_id != agent.id:
            response = RedirectResponse(url="/alerts", status_code=302)
            set_flash(response, "error", "No tienes permisos para esta alerta")
            return response

    # Cola secuencial: solo se puede trabajar la alerta activa
    if is_alert_locked_for_user(alert, current_user, db):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Debes completar tu alerta activa antes de atender esta")
        return response

    try:
        if not alert.read_at:
            alert.read_at = datetime.utcnow()

        if alert.status == AlertStatus.PENDING:
            alert.status = AlertStatus.IN_PROGRESS

        db.commit()

        response = RedirectResponse(url=f"/alerts/{alert_id}", status_code=302)
        set_flash(response, "success", "Alerta marcada como leída")
        return response

    except Exception:
        db.rollback()
        logger.exception("Error marcando alerta como leída: alert_id=%s", alert_id)
        response = RedirectResponse(url=f"/alerts/{alert_id}", status_code=302)
        set_flash(response, "error", "Ocurrió un error")
        return response


@router.post("/alerts/{alert_id}/follow-up")
async def add_follow_up(
    alert_id: int,
    request: Request,
    action_type: str = Form(...),
    notes: str = Form(None),
    next_action_date: str = Form(None),
    db: Session = Depends(get_db)
):
    """Agregar seguimiento a una alerta"""

    current_user = request.state.user

    alert = db.query(PropertyAlert).filter(PropertyAlert.id == alert_id).first()

    if not alert:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Alerta no encontrada")
        return response

    # Verificar permisos
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if not agent or alert.agent_id != agent.id:
            response = RedirectResponse(url="/alerts", status_code=302)
            set_flash(response, "error", "No tienes permisos para esta alerta")
            return response

    # Cola secuencial: solo se puede trabajar la alerta activa
    if is_alert_locked_for_user(alert, current_user, db):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Debes completar tu alerta activa antes de atender esta")
        return response

    try:
        # Parsear fecha si existe
        next_action_date_parsed = None
        if next_action_date:
            try:
                next_action_date_parsed = datetime.fromisoformat(next_action_date)
            except ValueError:
                pass

        follow_up = AlertFollowUp(
            alert_id=alert_id,
            action_type=action_type,
            notes=notes,
            next_action_date=next_action_date_parsed,
            created_by=current_user.id
        )

        db.add(follow_up)

        # Actualizar estado de alerta
        if alert.status == AlertStatus.PENDING:
            alert.status = AlertStatus.IN_PROGRESS

        db.commit()

        response = RedirectResponse(url=f"/alerts/{alert_id}", status_code=302)
        set_flash(response, "success", "Seguimiento agregado correctamente")
        return response

    except Exception:
        db.rollback()
        logger.exception("Error agregando seguimiento: alert_id=%s", alert_id)
        response = RedirectResponse(url=f"/alerts/{alert_id}", status_code=302)
        set_flash(response, "error", "Ocurrió un error al agregar el seguimiento")
        return response


@router.post("/alerts/{alert_id}/complete")
async def complete_alert(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Completar/cerrar una alerta"""

    current_user = request.state.user

    alert = db.query(PropertyAlert).filter(PropertyAlert.id == alert_id).first()

    if not alert:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Alerta no encontrada")
        return response

    # Verificar permisos
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if not agent or alert.agent_id != agent.id:
            response = RedirectResponse(url="/alerts", status_code=302)
            set_flash(response, "error", "No tienes permisos para esta alerta")
            return response

    # Cola secuencial: solo se puede completar la alerta activa
    if is_alert_locked_for_user(alert, current_user, db):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Debes completar tu alerta activa antes de atender esta")
        return response

    try:
        alert.status = AlertStatus.COMPLETED
        alert.completed_at = datetime.utcnow()

        db.commit()

        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "success", "Alerta completada correctamente")
        return response

    except Exception:
        db.rollback()
        logger.exception("Error completando alerta: alert_id=%s", alert_id)
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Ocurrió un error al completar la alerta")
        return response


@router.get("/api/alerts/unread-count")
async def get_unread_count(
    request: Request,
    db: Session = Depends(get_db)
):
    """API endpoint para obtener contador de alertas no leídas (para badge)"""

    # Obtener usuario desde el token (las rutas API no pasan por AuthMiddleware)
    from app.core.security import decode_token

    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(content={"unread_count": 0})

    payload = decode_token(token)
    if not payload:
        return JSONResponse(content={"unread_count": 0})

    email = payload.get("sub")
    if not email:
        return JSONResponse(content={"unread_count": 0})

    current_user = db.query(User).filter(User.email == email).first()
    if not current_user:
        return JSONResponse(content={"unread_count": 0})

    base_query = db.query(PropertyAlert).filter(
        PropertyAlert.read_at.is_(None),
        PropertyAlert.status.in_([AlertStatus.PENDING, AlertStatus.IN_PROGRESS])
    )

    # Si es agente, filtrar solo sus alertas
    if not is_admin(current_user):
        agent = get_agent_from_user(current_user, db)
        if agent:
            base_query = base_query.filter(PropertyAlert.agent_id == agent.id)
        else:
            return JSONResponse(content={"unread_count": 0})

    unread_count = base_query.count()

    return JSONResponse(content={"unread_count": unread_count})


@router.post("/alerts/{alert_id}/delete")
async def delete_alert(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Eliminar una alerta (solo admin)"""

    current_user = request.state.user

    if not is_admin(current_user):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Solo administradores pueden eliminar alertas")
        return response

    alert = db.query(PropertyAlert).filter(PropertyAlert.id == alert_id).first()

    if not alert:
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Alerta no encontrada")
        return response

    try:
        # Los seguimientos se eliminan automáticamente por cascade
        db.delete(alert)
        db.commit()

        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "success", f"Alerta de {alert.lead_name} eliminada correctamente")
        return response

    except Exception:
        db.rollback()
        logger.exception("Error eliminando alerta: alert_id=%s", alert_id)
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Ocurrió un error al eliminar la alerta")
        return response


@router.get("/alerts-dashboard", response_class=HTMLResponse)
async def alerts_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Dashboard de métricas de alertas (solo admin)"""

    current_user = request.state.user

    if not is_admin(current_user):
        response = RedirectResponse(url="/alerts", status_code=302)
        set_flash(response, "error", "Solo administradores pueden acceder al dashboard")
        return response

    # Obtener todas las alertas
    all_alerts = db.query(PropertyAlert).all()

    # Métricas generales
    total_alerts = len(all_alerts)
    pending_alerts = sum(1 for a in all_alerts if a.status == AlertStatus.PENDING)
    in_progress_alerts = sum(1 for a in all_alerts if a.status == AlertStatus.IN_PROGRESS)
    completed_alerts = sum(1 for a in all_alerts if a.status == AlertStatus.COMPLETED)

    # Alertas sin atender por más de 7 días
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    abandoned_alerts = [
        a for a in all_alerts
        if a.status == AlertStatus.PENDING and a.created_at < seven_days_ago
    ]

    # Tiempo promedio de respuesta (tiempo entre creación y primera lectura)
    response_times = []
    for alert in all_alerts:
        if alert.read_at and alert.created_at:
            delta = alert.read_at - alert.created_at
            response_times.append(delta.total_seconds() / 3600)  # en horas

    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    # Métricas por agente
    agents_data = []
    agents = db.query(Agent).all()

    for agent in agents:
        agent_alerts = [a for a in all_alerts if a.agent_id == agent.id]

        if not agent_alerts:
            continue

        agent_pending = sum(1 for a in agent_alerts if a.status == AlertStatus.PENDING)
        agent_completed = sum(1 for a in agent_alerts if a.status == AlertStatus.COMPLETED)

        # Tiempo promedio de respuesta del agente
        agent_response_times = []
        for alert in agent_alerts:
            if alert.read_at and alert.created_at:
                delta = alert.read_at - alert.created_at
                agent_response_times.append(delta.total_seconds() / 3600)

        agent_avg_response = sum(agent_response_times) / len(agent_response_times) if agent_response_times else 0

        # Última actividad
        last_activity = None
        if agent_alerts:
            latest_alert = max(agent_alerts, key=lambda a: a.created_at if a.created_at else datetime.min)
            last_activity = latest_alert.created_at

        agents_data.append({
            "agent": agent,
            "total_alerts": len(agent_alerts),
            "pending": agent_pending,
            "completed": agent_completed,
            "avg_response_time": round(agent_avg_response, 1),
            "last_activity": last_activity
        })

    # Ordenar por alertas pendientes (mayor primero)
    agents_data.sort(key=lambda x: x["pending"], reverse=True)

    return templates.TemplateResponse(
        request=request,
        name="alerts/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "total_alerts": total_alerts,
            "pending_alerts": pending_alerts,
            "in_progress_alerts": in_progress_alerts,
            "completed_alerts": completed_alerts,
            "abandoned_alerts": abandoned_alerts,
            "avg_response_time": round(avg_response_time, 1),
            "agents_data": agents_data,
            "AlertStatus": AlertStatus
        }
    )
