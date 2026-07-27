"""Lectura de los campos de la tabla externa en los formularios de propiedades.

Los campos replicados de la tabla externa son muchos y todos opcionales, así que
en lugar de declararlos uno a uno en la firma de cada ruta se leen aquí desde el
formulario y se convierten al tipo que espera el modelo.
"""

from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation


# Campos de texto libre. El valor es la etiqueta que se muestra en los errores.
TEXT_FIELDS = {
    "referencia": "Referencia",
    "codigo": "Código",
    "ref_catastral": "Referencia catastral",
    "property_type": "Tipo de inmueble",
    "business_type": "Operación",
    "estado_inmueble": "Estado del inmueble",
    "situacion": "Situación",
    "pais": "País",
    "zona": "Zona",
    "planta": "Planta",
    "llaves": "Llaves",
    "mandato_acuerdo": "Mandato / Acuerdo",
}

# Campos de texto con longitud fija en la base de datos
LIMITED_TEXT_FIELDS = {
    "cod_postal": ("Código postal", 5),
    "moneda": ("Moneda", 3),
}

DECIMAL_FIELDS = {
    "m2_utiles": "M2 útiles",
    "m2_construidos": "M2 construidos",
}

# Contadores almacenados como SMALLINT
COUNT_FIELDS = {
    "num_dormitorios": "Dormitorios",
    "num_banos_aseos": "Baños y aseos",
    "num_salones": "Salones",
    "num_terrazas": "Terrazas",
    "num_armarios": "Armarios",
    "num_garaje_aparcam": "Garaje / Aparcamiento",
    "num_ascensores": "Ascensores",
    "num_despachos": "Despachos",
    "num_locales": "Locales",
}

DATE_FIELDS = {
    "fecha_alta": "Fecha de alta",
}

# Límite superior de un SMALLINT en PostgreSQL
COUNT_MAX = 32767

# Campos que nunca deben quedar vacíos porque las vistas los muestran
# siempre. Si el formulario no trae valor se aplica el del modelo.
FIELD_DEFAULTS = {
    "property_type": "Casa",
    "business_type": "Venta",
    "moneda": "EUR",
}

# Campos que se guardan siempre en mayúsculas
UPPERCASE_FIELDS = ("moneda",)


def field_names():
    """Nombres de todos los campos que gestiona este módulo."""

    return (
        tuple(TEXT_FIELDS)
        + tuple(LIMITED_TEXT_FIELDS)
        + tuple(DECIMAL_FIELDS)
        + tuple(COUNT_FIELDS)
        + tuple(DATE_FIELDS)
    )


def _clean(form, name):
    """Devuelve el valor del formulario sin espacios, o None si viene vacío."""

    value = form.get(name)

    if value is None:
        return None

    value = str(value).strip()

    return value or None


def extract_fields(form):
    """Convierte los campos del formulario a los tipos del modelo.

    Devuelve una tupla (valores, errores). Los campos ausentes o vacíos se
    devuelven como None para poder limpiarlos desde el formulario.
    """

    values = {}
    errors = []

    for name in TEXT_FIELDS:
        values[name] = _clean(form, name)

    for name, (label, max_length) in LIMITED_TEXT_FIELDS.items():
        value = _clean(form, name)

        if value is not None and len(value) > max_length:
            errors.append(f"{label} no puede tener más de {max_length} caracteres")
            continue

        values[name] = value

    for name in UPPERCASE_FIELDS:
        if values.get(name) is not None:
            values[name] = values[name].upper()

    for name, default in FIELD_DEFAULTS.items():
        if values.get(name) is None:
            values[name] = default

    for name, label in DECIMAL_FIELDS.items():
        value = _clean(form, name)

        if value is None:
            values[name] = None
            continue

        try:
            number = Decimal(value.replace(",", "."))
        except (InvalidOperation, ValueError):
            errors.append(f"{label} debe ser un número")
            continue

        if number < 0:
            errors.append(f"{label} no puede ser negativo")
            continue

        values[name] = number

    for name, label in COUNT_FIELDS.items():
        value = _clean(form, name)

        if value is None:
            values[name] = None
            continue

        try:
            number = int(value)
        except ValueError:
            errors.append(f"{label} debe ser un número entero")
            continue

        if number < 0 or number > COUNT_MAX:
            errors.append(f"{label} debe estar entre 0 y {COUNT_MAX}")
            continue

        values[name] = number

    for name, label in DATE_FIELDS.items():
        value = _clean(form, name)

        if value is None:
            values[name] = None
            continue

        try:
            values[name] = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"{label} debe tener el formato AAAA-MM-DD")

    return values, errors
