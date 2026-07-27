# Diseño: Sincronización CRM → MOYZA App

**Fecha:** 2026-07-26
**Estado:** Propuesta de diseño — pendiente de aprobación
**Autor:** Diseño técnico previo a implementación

---

## 1. Contexto

Existe un ETL externo que descarga información de propiedades desde un CRM y la deja
en una base de datos Postgres **distinta** a la de esta aplicación, pero en el **mismo
motor y misma red**.

- **Frecuencia del ETL:** 1 o 2 veces cada 3 horas.
- **Datos que trae:** referencia de propiedad (`ref`), atributos de la propiedad,
  **propietario** y **captador**.
- **Objetivo:** que las tablas de la app (`properties`, `clients`, `agents`) reflejen
  la información del CRM sin perder la información propia de la app.

### 1.1 El problema real

Al revisar el modelo actual se identificaron dos hechos que condicionan toda la solución:

**a) No existe ninguna llave externa hacia el CRM.**

Ni `properties`, ni `clients`, ni `agents` tienen `ref`, `crm_id` o `external_id`.
Sin una llave estable no hay forma de decidir si una propiedad que llega del CRM
ya existe en la app. Cualquier sync sin esto **duplica registros en cada corrida**.

Además, las llaves naturales disponibles no son confiables:

| Tabla | Situación actual | Problema |
|---|---|---|
| `clients` | `email` nullable, `phone` NOT NULL pero **no unique** | No hay identificador único usable |
| `agents` | `email` NOT NULL + unique | Sirve, **si** el CRM trae el email del captador |
| `properties` | solo `id` autoincremental | Sin llave natural |

**b) Las tablas de la app son el ancla de FKs de todo el producto.**

`properties.id` es referenciado por:

- `property_visits`
- `property_alerts`
- `property_interactions`
- `property_price_history`
- `property_status_history`
- `report_job_logs`
- `reports`

Y `properties` contiene campos que **el CRM no conoce ni conocerá**:
`fair_price`, `auto_send_report`, `report_frequency`, `report_day`, `report_hour`.
Igual `agents` con los campos de firma digital.

**Consecuencia:** las tablas de la app **no pueden ser reemplazadas** por las del CRM,
y el sync **nunca puede borrar filas** — rompería visitas y alertas históricas.
Esto descarta de entrada cualquier enfoque de "apuntar la app a la BD del CRM".

---

## 2. Decisiones tomadas

| # | Decisión | Valor acordado |
|---|---|---|
| D1 | Dueño de `properties.status` | **CRM solo puede cerrar.** Ver §5.2 |
| D2 | Acceso a la BD del CRM | Usuario **read-only**, misma red → segundo engine SQLAlchemy |
| D3 | Datos existentes en la app | Son de prueba → **no hay backfill**, se limpia y se popula desde cero |
| D4 | Alcance de este documento | Diseño primero, implementación después |

---

## 3. Alternativas evaluadas

### 3.1 `postgres_fdw` — leer el CRM en vivo como tablas foráneas — ❌ Descartado

Montar las tablas del CRM dentro de la BD de la app y consultarlas sin copiar.

- ✅ Cero duplicación, cero desfase, cero cron.
- ❌ **No se puede declarar una FK desde `property_visits` hacia una tabla foránea.**
  Esto por sí solo rompe el modelo.
- ❌ No se indexa; los JOIN con tablas locales traen la tabla remota completa a memoria.
- ❌ Si el CRM se cae, la app se cae.
- ❌ Alembic y los modelos SQLAlchemy no lo manejan.

**Veredicto:** inviable como modelo principal. Descartado también como transporte,
porque D2 (usuario read-only) hace innecesario crear extensiones en el CRM.

### 3.2 Replicación lógica Postgres → tabla espejo — ❌ Descartado

- ✅ Espejo casi en tiempo real, sin cron.
- ❌ Requiere `wal_level=logical` y privilegios de superusuario **en el CRM**.
  D2 lo descarta: solo hay acceso read-only.
- ❌ Aunque se pudiera, el espejo llega con el esquema del CRM → **seguiría siendo
  necesaria toda la lógica de mapeo**. Solo cambia el transporte, no el trabajo.

### 3.3 Segundo engine + UPSERT directo — ⚠️ Viable, más simple

Leer el CRM con un segundo engine y hacer UPSERT directo sobre `properties`.

- ✅ Menos piezas.
- ❌ No se puede reprocesar sin volver a leer el CRM → depurar es doloroso.
- ❌ Sin rastro de qué vio exactamente el sync en cada corrida.

### 3.4 Segundo engine + tabla staging + sync interno — ✅ **ELEGIDO**

```
┌─────────────┐
│   CRM DB    │  (Postgres, read-only, misma red)
└──────┬──────┘
       │  engine secundario SQLAlchemy (read-only)
       │  SELECT con watermark
       ▼
┌──────────────────────────────────────────────────┐
│  BD de la APP                                    │
│                                                  │
│  ┌────────────────────┐                          │
│  │ crm_properties_raw │  espejo crudo + hash     │
│  └─────────┬──────────┘                          │
│            │  CrmSyncService (todo en SQL local) │
│            ▼                                     │
│  ┌───────────────────────────────────────┐       │
│  │ clients → agents → properties         │       │
│  │  + property_price_history             │       │
│  │  + property_status_history            │       │
│  └───────────────────────────────────────┘       │
│                                                  │
│  ┌──────────────────┐                            │
│  │  crm_sync_logs   │  auditoría por corrida     │
│  └──────────────────┘                            │
└──────────────────────────────────────────────────┘
```

**Por qué esta:**

- **Separa transporte de lógica de negocio.** Si mañana cambia el acceso al CRM
  (FDW, replicación, API), solo cambia la etapa de ingesta. El sync no se toca.
- **Reprocesable.** Se puede re-ejecutar el sync sobre el staging sin tocar el CRM.
  Esto es la diferencia entre depurar en minutos y depurar en horas.
- **Auditable.** Queda el payload y el hash de cada corrida.
- **Diff en SQL local**, no en Python fila por fila.
- **La app es inmune a caídas del CRM.** Si el CRM no responde, el sync falla y se
  registra; la app sigue operando con los últimos datos buenos.

**Costo aceptado:** una tabla y una etapa más; datos con hasta ~3h de desfase
(irrelevante dado que el propio ETL corre cada 3h — el sync nunca puede ser más
fresco que su fuente).

---

## 4. Propiedad del dato

Regla central. Si esto no queda fijado, el sync pisa cambios hechos a mano cada 3 horas
y nadie entiende por qué.

| Campo | Dueño | Comportamiento en cada sync |
|---|---|---|
| `properties.title` | CRM | Sobrescribe |
| `properties.address` | CRM | Sobrescribe |
| `properties.city` | CRM | Sobrescribe |
| `properties.property_type` | CRM | Sobrescribe |
| `properties.business_type` | CRM | Sobrescribe |
| `properties.price` | CRM | Sobrescribe **+ registra en `property_price_history`** |
| `properties.description` | CRM | Sobrescribe |
| `properties.client_id` | CRM | Re-vincula si cambió el propietario |
| `properties.agent_id` | CRM | Re-vincula si cambió el captador |
| `properties.status` | **Mixto** | Ver §5.2 — CRM solo cierra |
| `properties.market_entry_date` | CRM | Solo en creación (INSERT) |
| `properties.fair_price` | **App** | Nunca se toca |
| `properties.auto_send_report` | **App** | Nunca se toca |
| `properties.report_frequency` / `report_day` / `report_hour` | **App** | Nunca se toca |
| `agents.signature_*` | **App** | Nunca se toca |
| `clients.status` | **App** | Nunca se toca |
| visitas, alertas, interacciones, informes, historiales | **App** | El sync solo inserta en los historiales |

---

## 5. Esquema propuesto

### 5.1 Llaves externas y trazabilidad

Todos los campos nuevos son `nullable=True` para que los registros creados a mano
desde la app sigan siendo válidos y no entren en conflicto con el sync.

```python
# properties
crm_ref       = Column(String, unique=True, index=True, nullable=True)
source        = Column(String, nullable=False, default="MANUAL")   # MANUAL | CRM
crm_synced_at = Column(DateTime, nullable=True)
crm_hash      = Column(String, nullable=True)
is_archived   = Column(Boolean, nullable=False, default=False)

# clients
crm_ref       = Column(String, unique=True, index=True, nullable=True)
source        = Column(String, nullable=False, default="MANUAL")
crm_synced_at = Column(DateTime, nullable=True)

# agents
crm_ref       = Column(String, unique=True, index=True, nullable=True)
source        = Column(String, nullable=False, default="MANUAL")
crm_synced_at = Column(DateTime, nullable=True)
```

Notas de diseño:

- **`crm_ref` unique** es la garantía estructural contra duplicados. Es la pieza
  más importante de todo el diseño: sin ella nada funciona.
- **`crm_hash`** guarda el hash de los campos que el CRM controla. Si el hash no cambió,
  el sync no escribe nada. Convierte una corrida sin cambios en un no-op, y evita
  ensuciar `updated_at` e historiales.
- **`is_archived`** en lugar de borrar. Si una `ref` desaparece del CRM, se marca
  archivada; las visitas y alertas históricas siguen intactas. **El sync nunca hace DELETE.**
- **`source`** distingue lo creado a mano de lo importado, para que la UI pueda
  bloquear la edición de campos que el CRM va a sobrescribir en 3 horas.

### 5.2 Mapeo de estados — regla "el CRM solo cierra" (D1)

Estados de la app (`PropertyStatus` en `app/core/constants.py`):
`Activa`, `Reservada`, `Pausada`, `Vendida`, `Retirada`, `Archivada`.

Regla acordada:

> El CRM **solo puede mover una propiedad hacia un estado terminal** (`Vendida`,
> `Retirada`). Cualquier otra transición la controla exclusivamente la app.

Tabla de decisión:

| Estado en app | Estado que llega del CRM | Acción |
|---|---|---|
| cualquiera (no terminal) | terminal (`Vendida` / `Retirada`) | ✅ **Aplica** + registra en `property_status_history` |
| `Activa` | `Reservada` / `Pausada` | ❌ Ignora — la app manda |
| `Vendida` / `Retirada` / `Archivada` | cualquier no terminal | ❌ Ignora — **no se reabre desde el CRM** |
| — (INSERT nuevo) | cualquiera | ✅ Aplica el estado mapeado del CRM |

Racional: proteger `auto_send_report` y los flujos de visitas/alertas de cambios
inesperados cada 3 horas, sin dejar que la app anuncie como activa una propiedad
que el CRM ya cerró.

⚠️ **Bloqueante:** el mapeo `valor_del_CRM → PropertyStatus` requiere conocer los
valores reales que emite el CRM. Ver §10.

### 5.3 Tabla staging

```python
class CrmPropertyRaw(Base):
    __tablename__ = "crm_properties_raw"

    id             = Column(Integer, primary_key=True)
    crm_ref        = Column(String, unique=True, index=True, nullable=False)
    payload        = Column(JSONB, nullable=False)     # fila del CRM tal cual llegó
    payload_hash   = Column(String, nullable=False)
    crm_updated_at = Column(DateTime, nullable=True)   # si el CRM lo expone
    fetched_at     = Column(DateTime, nullable=False, default=utcnow)
    processed_at   = Column(DateTime, nullable=True)   # NULL = pendiente de sync
    process_error  = Column(Text, nullable=True)
```

`JSONB` permite absorber cambios de esquema del CRM sin migración, y consultar
campos sueltos con SQL cuando haga falta depurar.

### 5.4 Auditoría

`crm_sync_logs`, calcado del estilo de `ReportJobLog` para que encaje con las vistas
de logs que ya existen en la app (`/report_logs`, `/ai_logs`):

```python
class CrmSyncLog(Base):
    __tablename__ = "crm_sync_logs"

    id               = Column(Integer, primary_key=True, index=True)
    run_at           = Column(DateTime, nullable=False, default=utcnow, index=True)
    trigger          = Column(String, nullable=False)   # ETL_HOOK | SCHEDULER | MANUAL
    status           = Column(String, nullable=False, default="running")
                       # running | success | partial | failed | skipped_locked
    stage            = Column(String, nullable=True)    # fetch | clients | agents | properties

    rows_fetched     = Column(Integer, default=0)
    clients_created  = Column(Integer, default=0)
    clients_updated  = Column(Integer, default=0)
    agents_created   = Column(Integer, default=0)
    agents_updated   = Column(Integer, default=0)
    props_created    = Column(Integer, default=0)
    props_updated    = Column(Integer, default=0)
    props_unchanged  = Column(Integer, default=0)
    props_archived   = Column(Integer, default=0)
    rows_failed      = Column(Integer, default=0)

    watermark_from   = Column(DateTime, nullable=True)
    watermark_to     = Column(DateTime, nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)
    error_message    = Column(Text, nullable=True)
```

Sin esto el sync es una caja negra que corre 8 veces al día.

---

## 6. Algoritmo del sync

### 6.1 Etapa 1 — Ingesta (CRM → staging)

1. Tomar `pg_advisory_lock` (§7.3). Si está ocupado → `skipped_locked`, salir.
2. Leer watermark: `MAX(crm_updated_at)` de la corrida anterior exitosa.
3. Consultar el CRM con el engine secundario:
   - Si el CRM expone `updated_at` → `WHERE updated_at > :watermark` (incremental).
   - Si no → leer todo; el `payload_hash` filtra lo que no cambió.
4. UPSERT en `crm_properties_raw` por `crm_ref`. Si el hash coincide con el ya
   almacenado, no marcar como pendiente.
5. Cerrar la conexión al CRM. **A partir de aquí todo es local.**

### 6.2 Etapa 2 — Sync (staging → tablas de la app)

Orden obligatorio por las FKs: **`clients` → `agents` → `properties`**.

**Clientes (propietario):**
1. Buscar por `crm_ref`.
2. Si no existe → INSERT con `source="CRM"`.
3. Si existe → UPDATE de campos propiedad del CRM. No tocar `status`.

**Agentes (captador):**
1. Buscar por `crm_ref`; si no hay, fallback por `email` (es unique) y adoptar
   el registro asignándole el `crm_ref`.
2. INSERT o UPDATE según corresponda. **Nunca tocar los campos `signature_*`.**

**Propiedades:**
1. Buscar por `crm_ref`.
2. **No existe** → INSERT con `source="CRM"`, estado mapeado del CRM,
   `market_entry_date` del CRM.
3. **Existe y `crm_hash` no cambió** → no-op, contar en `props_unchanged`.
4. **Existe y cambió:**
   - Si cambia `price` → **INSERT en `property_price_history`** con
     `old_price`, `new_price`, `reason="CRM_SYNC"`, `created_by=NULL`.
   - Si cambia `status` y la transición está permitida (§5.2) → aplicar
     e **INSERT en `property_status_history`** con `changed_by=NULL`.
   - Actualizar el resto de campos del CRM.
   - Nunca tocar `fair_price`, `auto_send_report`, `report_*`.
   - Actualizar `crm_hash` y `crm_synced_at`.
5. **Archivado:** las propiedades con `source="CRM"` cuya `crm_ref` ya no aparece
   en el CRM se marcan `is_archived=True`. **Solo en corridas de sync completo**,
   nunca en una incremental por watermark (en una incremental la ausencia no
   significa borrado, solo significa "sin cambios").

> **Los dos pasos que se olvidan siempre** son los historiales de precio y estado.
> Sin ellos, `property_metrics` y los informes generados muestran un hueco: el precio
> cambió y no hay registro de por qué. Van dentro de la misma transacción que el UPDATE.

### 6.3 Transaccionalidad

Una transacción **por propiedad**, no una global. Una fila corrupta del CRM no debe
tumbar las otras 500: se registra en `process_error`, se cuenta en `rows_failed`,
y la corrida termina como `partial`.

---

## 7. Orquestación

### 7.1 Disparo principal — encadenado al ETL

Es el mecanismo correcto: se ejecuta exactamente cuando hay datos nuevos, sin adivinar.

```bash
# crontab del ETL
python /ruta/etl.py && python -m app.jobs.crm_sync --trigger=ETL_HOOK
```

El `&&` importa: si el ETL falla, el sync no corre sobre datos a medias.

### 7.2 Red de seguridad — APScheduler existente

En `app/jobs/scheduler.py` ya existe el patrón de "solo worker maestro"
(`WORKER_ID == "0"`), así que un job nuevo encaja sin cambios estructurales:

```python
scheduler.add_job(
    check_crm_sync_watermark,
    "cron", hour="*", minute=35,
    id="check_crm_sync_watermark",
    replace_existing=True,
)
```

Corre el sync **solo si** la última corrida exitosa tiene más de N horas
(sugerido: 4h, algo más que el ciclo del ETL). Cubre el caso de que el cron del ETL
falle silenciosamente.

### 7.3 Lock

Ambas vías pueden coincidir. Un lock a nivel de Postgres lo resuelve sin archivos
ni estado compartido:

```sql
SELECT pg_try_advisory_lock(:crm_sync_lock_id);
```

Si no se obtiene → registrar `skipped_locked` y salir sin error. Es la opción correcta
frente a un lockfile porque el lock muere con la conexión: un proceso que se cae no
deja el sync bloqueado para siempre.

### 7.4 Configuración

```python
# app/core/config.py
CRM_DB_HOST / CRM_DB_PORT / CRM_DB_USER / CRM_DB_PASSWORD / CRM_DB_NAME
CRM_SYNC_ENABLED: bool = False          # apagado por defecto
CRM_SYNC_MAX_AGE_HOURS: int = 4         # umbral de la red de seguridad
CRM_SYNC_DRY_RUN: bool = False

@property
def CRM_DATABASE_URL(self): ...
```

Engine secundario en `app/db/crm_session.py`, separado del principal, con
`pool_pre_ping=True` y `isolation_level="AUTOCOMMIT"` en modo lectura.
`CRM_SYNC_ENABLED=False` por defecto permite desplegar el código sin activar el sync.

---

## 8. Casos borde

| Caso | Tratamiento |
|---|---|
| Propiedad desaparece del CRM | `is_archived=True`. **Nunca DELETE** (rompería FKs de visitas/alertas) |
| Propiedad reaparece | `is_archived=False`, se reactiva el mismo `id` → conserva su historial |
| Cambia el propietario | Re-vincular `client_id`. El `Client` anterior se conserva |
| Cambia el captador | Re-vincular `agent_id`. Las visitas ya firmadas conservan su agente original |
| Captador sin email en el CRM | ⚠️ `agents.email` es **NOT NULL + unique** → bloqueante. Ver §10 |
| Propietario sin teléfono | ⚠️ `clients.phone` es **NOT NULL** → bloqueante. Ver §10 |
| Precio a `NULL` en el CRM | Ignorar el cambio y registrar warning. No borrar un precio existente |
| Propiedad creada a mano que luego aparece en el CRM | D3 dice que no aplica hoy. A futuro: vista de reconciliación manual |
| Dos `ref` distintas, misma propiedad física | El CRM es la autoridad: quedan como dos registros |
| ETL corre 2 veces en la ventana | Idempotente por `crm_ref` + `payload_hash` |

---

## 9. Plan de implementación por fases

Cada fase es desplegable y verificable de forma independiente.

**Fase 0 — Descubrimiento del esquema del CRM** *(bloqueante, ver §10)*
- Documentar tablas, columnas y tipos reales del CRM.
- Confirmar si existe `updated_at` (define incremental vs full).
- Recoger el catálogo de valores de estado del CRM.

**Fase 1 — Llaves y esquema**
- Migración Alembic: `crm_ref`, `source`, `crm_synced_at`, `crm_hash`, `is_archived`.
- Modelos `CrmPropertyRaw` y `CrmSyncLog` + registro en `app/db/base.py`.
- Limpieza de los datos de prueba (D3).
- *Sin esta fase nada más funciona, y no compromete el resto del diseño.*

**Fase 2 — Conexión e ingesta**
- `CRM_*` en config, `app/db/crm_session.py`.
- Etapa de ingesta CRM → `crm_properties_raw`.
- Comando `python -m app.jobs.crm_sync --fetch-only` para validar la lectura aislada.

**Fase 3 — Sync**
- `CrmSyncService` con el mapeo de campos, la regla de estados de §5.2 y los
  historiales de precio/estado.
- Modo `--dry-run` que reporta qué haría sin escribir. **Primera ejecución siempre así.**

**Fase 4 — Orquestación**
- Job en APScheduler + entrypoint CLI para el cron del ETL.
- `pg_advisory_lock`.

**Fase 5 — Observabilidad y UI**
- Vista `/crm_sync_logs` siguiendo el patrón de `/report_logs`.
- Badge "sincronizado desde CRM" y bloqueo de edición de campos gobernados por
  el CRM cuando `source="CRM"`.

**Fase 6 — Pruebas**
- Idempotencia: correr el sync dos veces → la segunda es todo `unchanged`.
- Cada rama de la tabla de estados de §5.2.
- Que `fair_price` y `auto_send_report` sobreviven a un sync.
- Que archivar no rompe una propiedad con visitas y alertas.

---

## 10. Puntos abiertos — bloquean la Fase 1

Información del CRM que hace falta antes de escribir código:

1. **Esquema real del CRM.** Nombre de las tablas y el listado de columnas con tipos.
   `\d nombre_tabla` en psql es suficiente.
2. **¿Existe `updated_at` (o equivalente) en la tabla de propiedades?**
   Con él el sync es incremental; sin él hay que leer todo y depender del hash.
3. **Catálogo de valores de estado del CRM.**
   `SELECT DISTINCT estado FROM <tabla>;` — necesario para el mapeo de §5.2.
4. **¿El CRM trae email del captador?**
   `agents.email` es NOT NULL + unique. Si no viene, hay que decidir entre
   generar un placeholder o relajar la restricción con una migración.
5. **¿El CRM trae teléfono del propietario?**
   `clients.phone` es NOT NULL. Mismo problema.
6. **¿Cómo viene identificado el propietario/captador?** ¿Con su propio `ref`,
   o solo como texto plano? Si es texto plano, no hay llave estable para
   `clients.crm_ref` / `agents.crm_ref` y el matcheo se vuelve heurístico.
7. **¿Una propiedad puede tener más de un captador?** El modelo actual asume
   `agent_id` único.

---

## 11. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El sync pisa cambios hechos a mano | Alto | Tabla de propiedad del dato (§4) + UI que bloquea campos del CRM |
| El CRM cambia su esquema sin aviso | Medio | `payload` en JSONB absorbe el cambio; el mapeo falla ruidoso, no en silencio |
| Duplicados por `crm_ref` ausente | **Crítico** | Constraint `unique` a nivel de BD, no validación en Python |
| Corridas solapadas | Medio | `pg_advisory_lock` |
| Sync falla en silencio durante días | Medio | `crm_sync_logs` + red de seguridad por watermark (§7.2) |
| Historiales de precio con huecos | Medio | Escritura de historial dentro de la misma transacción del UPDATE |
| Un `DELETE` accidental rompe FKs | Alto | `is_archived`; el servicio no implementa ninguna ruta de borrado |

---

## 12. Resumen

- **Arquitectura:** segundo engine read-only → tabla staging en la BD de la app →
  sync interno hacia `clients`/`agents`/`properties`.
- **Las tablas de la app siguen siendo canónicas.** El CRM alimenta campos, no reemplaza tablas.
- **`crm_ref` unique es la pieza indispensable.** Todo lo demás depende de ella.
- **El sync nunca borra.** Archiva.
- **`status`:** el CRM solo puede cerrar; la app controla el resto.
- **Disparo:** encadenado al cron del ETL, con red de seguridad horaria por watermark.
- **Siguiente paso:** responder §10 para desbloquear la Fase 1.
