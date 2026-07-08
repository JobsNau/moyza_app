class PropertyStatus:
    ACTIVE = "Activa"
    RESERVED = "Reservada"
    PAUSED = "Pausada"
    SOLD = "Vendida"
    WITHDRAWN = "Retirada"
    ARCHIVED = "Archivada"

    @classmethod
    def values(cls):
        return {
            cls.ACTIVE,
            cls.RESERVED,
            cls.PAUSED,
            cls.SOLD,
            cls.WITHDRAWN,
            cls.ARCHIVED,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


class PropertyInteractionType:
    INQUIRY = "CONSULTA"
    VISIT = "VISITA"
    INTERESTED = "INTERESADO"
    OFFER = "OFERTA"

    @classmethod
    def values(cls):
        return {
            cls.INQUIRY,
            cls.VISIT,
            cls.INTERESTED,
            cls.OFFER,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


class ReportType:
    AUTOMATIC = "AUTOMATICO"
    GENERAL = "GENERAL"
    FOLLOW_UP = "SEGUIMIENTO"
    VALUATION = "VALORACION"

    @classmethod
    def upload_values(cls):
        return {
            cls.GENERAL,
            cls.FOLLOW_UP,
            cls.VALUATION,
        }

    @classmethod
    def values(cls):
        return cls.upload_values() | {cls.AUTOMATIC}

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()

    @classmethod
    def is_valid_upload(cls, value: str) -> bool:
        return value in cls.upload_values()


class AlertType:
    LEAD_INTERES = "LEAD_INTERES"
    CAMBIO_PRECIO = "CAMBIO_PRECIO"
    VISITA_SOLICITADA = "VISITA_SOLICITADA"
    OTRO = "OTRO"

    @classmethod
    def values(cls):
        return {
            cls.LEAD_INTERES,
            cls.CAMBIO_PRECIO,
            cls.VISITA_SOLICITADA,
            cls.OTRO,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


class AlertPriority:
    ALTA = "ALTA"
    NORMAL = "NORMAL"
    BAJA = "BAJA"

    @classmethod
    def values(cls):
        return {
            cls.ALTA,
            cls.NORMAL,
            cls.BAJA,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


class AlertStatus:
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def values(cls):
        return {
            cls.PENDING,
            cls.IN_PROGRESS,
            cls.COMPLETED,
            cls.CANCELLED,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()


class FollowUpActionType:
    LLAMADA = "LLAMADA"
    VISITA_PROGRAMADA = "VISITA_PROGRAMADA"
    EMAIL_ENVIADO = "EMAIL_ENVIADO"
    OFERTA_RECIBIDA = "OFERTA_RECIBIDA"
    CAMBIO_PRECIO = "CAMBIO_PRECIO"
    SIN_INTERES = "SIN_INTERES"
    NEGOCIACION = "NEGOCIACION"
    OTRO = "OTRO"

    @classmethod
    def values(cls):
        return {
            cls.LLAMADA,
            cls.VISITA_PROGRAMADA,
            cls.EMAIL_ENVIADO,
            cls.OFERTA_RECIBIDA,
            cls.CAMBIO_PRECIO,
            cls.SIN_INTERES,
            cls.NEGOCIACION,
            cls.OTRO,
        }

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()
