"""
Servicio de auditoría para los envíos por WhatsApp de la ficha de visita.

Registra cada intento (éxito, error u omitido) para poder ver en
/report-logs quién recibió la ficha, cuándo y qué falló si algo falló.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.visit_whatsapp_log import VisitWhatsappLog


logger = logging.getLogger(__name__)


def log_whatsapp_attempt(
    db: Session,
    visit_id: int,
    recipient_type: str,
    status: str,
    trigger: str,
    property_id: Optional[int] = None,
    recipient_name: Optional[str] = None,
    recipient_phone: Optional[str] = None,
    error_message: Optional[str] = None,
    file_url: Optional[str] = None,
    duration_ms: Optional[int] = None,
    triggered_by: Optional[int] = None
) -> Optional[VisitWhatsappLog]:
    """
    Crea un registro de auditoría para un intento de envío de la ficha de visita.

    Args:
        db: Sesión de base de datos.
        visit_id: ID de la visita.
        recipient_type: 'comprador' o 'agente'.
        status: 'SENT', 'ERROR' o 'SKIPPED'.
        trigger: 'finalize' (automático al firmar) o 'manual_resend' (botón Enviar).
        property_id: ID de la propiedad asociada a la visita.
        recipient_name: Nombre del destinatario (para mostrar en el log).
        recipient_phone: Teléfono al que se intentó enviar.
        error_message: Mensaje de error si status='ERROR'.
        file_url: URL pública del PDF usada en el intento.
        duration_ms: Duración de la llamada a la API de WhatsApp, en milisegundos.
        triggered_by: ID del usuario que disparó el envío (None si fue automático).
    """
    try:
        log_entry = VisitWhatsappLog(
            visit_id=visit_id,
            property_id=property_id,
            recipient_type=recipient_type,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            status=status,
            error_message=error_message,
            trigger=trigger,
            file_url=file_url,
            duration_ms=duration_ms,
            triggered_by=triggered_by
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        logger.info(
            "Visit WhatsApp log: visit_id=%s recipient=%s status=%s trigger=%s",
            visit_id, recipient_type, status, trigger
        )

        return log_entry
    except Exception:
        db.rollback()
        logger.exception(
            "No se pudo registrar el log de envío WhatsApp de visita: visit_id=%s recipient=%s",
            visit_id, recipient_type
        )
        return None
