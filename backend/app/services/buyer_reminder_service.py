"""
Servicio de recordatorio de compradores sin gestión.

Identifica compradores cuya última gestión (follow-up o creación de alerta)
supera el umbral de horas configurado, y envía un email de recordatorio al
agente responsable con el listado de compradores pendientes.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.alert_follow_up import AlertFollowUp
from app.models.alert_reminder_log import AlertReminderLog
from app.models.property_alert import PropertyAlert
from app.services.gmail_service import GmailService

logger = logging.getLogger(__name__)

# Cambiar a ["PENDING"] para notificar solo alertas nuevas sin abrir.
# Dejar ["PENDING", "IN_PROGRESS"] para notificar cualquier alerta activa.
REMINDER_STATUSES = ["PENDING"]


def _last_action_subquery(db: Session):
    """Subconsulta: fecha del último follow-up por alerta."""
    return (
        db.query(
            AlertFollowUp.alert_id,
            func.max(AlertFollowUp.created_at).label("last_followup_at"),
        )
        .group_by(AlertFollowUp.alert_id)
        .subquery()
    )


def get_pending_buyers_by_agent(db: Session, hours_threshold: int) -> dict[int, list[dict]]:
    """
    Devuelve un dict {agent_id: [lista de compradores pendientes]}.
    Un comprador aparece si tiene al menos una alerta activa cuya
    última gestión supera `hours_threshold` horas.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours_threshold)

    last_followup = _last_action_subquery(db)

    alerts = (
        db.query(PropertyAlert)
        .outerjoin(last_followup, last_followup.c.alert_id == PropertyAlert.id)
        .filter(PropertyAlert.status.in_(REMINDER_STATUSES))
        .filter(
            func.coalesce(last_followup.c.last_followup_at, PropertyAlert.created_at)
            < cutoff
        )
        .all()
    )

    result: dict[int, list[dict]] = {}

    for alert in alerts:
        last_action = (
            max(
                (fu.created_at for fu in alert.follow_ups),
                default=alert.created_at,
            )
        )
        entry = {
            "alert_id": alert.id,
            "buyer_name": alert.lead_name,
            "buyer_phone": alert.lead_phone or "—",
            "alert_status": alert.status,
            "last_action_at": last_action,
            "hours_elapsed": int((datetime.utcnow() - last_action).total_seconds() // 3600),
        }

        agent_id = alert.agent_id
        result.setdefault(agent_id, []).append(entry)

    return result


def _build_email_body(agent_name: str, buyers: list[dict], hours_threshold: int) -> str:
    rows = ""
    for b in sorted(buyers, key=lambda x: x["last_action_at"]):
        rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{b['buyer_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{b['buyer_phone']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{b['alert_status']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#c0392b;font-weight:bold;">
                {b['hours_elapsed']} horas
            </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:680px;margin:auto;">
      <h2 style="color:#0E567B;">Recordatorio: compradores sin gestión</h2>
      <p>Hola <strong>{agent_name}</strong>,</p>
      <p>Los siguientes compradores llevan más de <strong>{hours_threshold} horas</strong>
         sin recibir gestión:</p>
      <table style="width:100%;border-collapse:collapse;margin-top:16px;">
        <thead>
          <tr style="background:#0E567B;color:#fff;">
            <th style="padding:10px 12px;text-align:left;">Comprador</th>
            <th style="padding:10px 12px;text-align:left;">Teléfono</th>
            <th style="padding:10px 12px;text-align:left;">Estado</th>
            <th style="padding:10px 12px;text-align:left;">Sin gestión</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;font-size:13px;color:#888;">
        Este es un recordatorio automático del sistema Moyza.
      </p>
    </body></html>
    """


def run_buyer_reminders(
    db: Session,
    gmail_service: GmailService,
    hours_threshold: int,
    sender_name: Optional[str] = "Sistema Moyza",
):
    """
    Punto de entrada principal llamado desde el scheduler.
    Consulta compradores pendientes y envía un email por agente.
    """
    logger.info(
        f"Iniciando recordatorio de compradores (umbral: {hours_threshold}h, "
        f"estados: {REMINDER_STATUSES})"
    )

    pending_by_agent = get_pending_buyers_by_agent(db, hours_threshold)

    if not pending_by_agent:
        logger.info("No hay compradores pendientes de atención. No se envían recordatorios.")
        return

    agents = (
        db.query(Agent)
        .filter(Agent.id.in_(pending_by_agent.keys()))
        .all()
    )
    agents_by_id = {a.id: a for a in agents}

    sent, skipped = 0, 0
    executed_at = datetime.utcnow()

    for agent_id, buyers in pending_by_agent.items():
        agent = agents_by_id.get(agent_id)
        if not agent:
            logger.warning(f"Agente {agent_id} no encontrado, omitiendo.")
            db.add(AlertReminderLog(
                executed_at=executed_at,
                agent_id=None,
                agent_name=f"[Desconocido id={agent_id}]",
                agent_email="",
                buyers_count=len(buyers),
                status="SKIPPED",
                skip_reason="agente_no_encontrado",
            ))
            skipped += 1
            continue

        if not agent.email:
            logger.warning(
                f"Agente {agent.name} (id={agent_id}) no tiene email configurado, omitiendo."
            )
            db.add(AlertReminderLog(
                executed_at=executed_at,
                agent_id=agent.id,
                agent_name=agent.name,
                agent_email="",
                buyers_count=len(buyers),
                status="SKIPPED",
                skip_reason="sin_email",
            ))
            skipped += 1
            continue

        subject = f"[Moyza] {len(buyers)} comprador(es) pendiente(s) de atención"
        body = _build_email_body(agent.name, buyers, hours_threshold)

        success = gmail_service.send_email(agent.email, subject, body)

        db.add(AlertReminderLog(
            executed_at=executed_at,
            agent_id=agent.id,
            agent_name=agent.name,
            agent_email=agent.email,
            buyers_count=len(buyers),
            status="SENT" if success else "ERROR",
            error_message=None if success else "Fallo al enviar via Gmail API",
        ))

        if success:
            sent += 1
        else:
            skipped += 1

    db.commit()
    logger.info(
        f"Recordatorios completados: {sent} enviados, {skipped} omitidos."
    )
