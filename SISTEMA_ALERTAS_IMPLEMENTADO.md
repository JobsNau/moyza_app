# Sistema de Alertas de Propiedades - Implementación Completa

## 📋 Descripción General

Sistema completo de notificaciones/alertas para gestionar interesados en propiedades inmobiliarias. Permite al admin crear alertas manualmente cuando llegan leads por email/portales, asignarlas automáticamente al agente responsable, y hacer seguimiento completo del desempeño.

---

## ✅ Componentes Implementados

### 1. **Modelos de Base de Datos**

#### `PropertyAlert` (`app/models/property_alert.py`)
- Almacena información de cada alerta/lead
- Campos principales:
  - `property_id`: Propiedad asociada
  - `agent_id`: Agente responsable (asignado automáticamente)
  - `lead_name`, `lead_phone`, `lead_email`: Datos del interesado
  - `source`: Origen (Idealista, Fotocasa, etc.)
  - `alert_type`: LEAD_INTERES, CAMBIO_PRECIO, VISITA_SOLICITADA, OTRO
  - `priority`: ALTA, NORMAL, BAJA
  - `status`: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
  - `created_at`, `read_at`, `completed_at`: Timestamps para métricas

#### `AlertFollowUp` (`app/models/alert_follow_up.py`)
- Registro de cada acción de seguimiento
- Campos principales:
  - `alert_id`: Alerta asociada
  - `action_type`: LLAMADA, VISITA_PROGRAMADA, EMAIL_ENVIADO, OFERTA_RECIBIDA, etc.
  - `notes`: Descripción de la acción
  - `next_action_date`: Fecha de próximo seguimiento (opcional)
  - `created_by`: Usuario que registró el seguimiento

### 2. **Constantes** (`app/core/constants.py`)

- **AlertType**: Tipos de alertas
- **AlertPriority**: Prioridades (Alta, Normal, Baja)
- **AlertStatus**: Estados del ciclo de vida
- **FollowUpActionType**: Tipos de acciones de seguimiento

### 3. **Migración de Base de Datos**

Archivo: `alembic/versions/a1b2c3d4e5f6_add_property_alerts_and_follow_ups.py`

**Para aplicar la migración:**
```bash
cd backend
alembic upgrade head
```

### 4. **Rutas API** (`app/web/routes/alerts.py`)

#### Rutas Principales:

1. **`GET /alerts`** - Lista de alertas
   - Admin: ve todas las alertas
   - Agente: solo ve sus alertas
   - Incluye filtros por estado y prioridad

2. **`GET /alerts/{alert_id}`** - Detalle de alerta
   - Muestra información completa del lead y propiedad
   - Historial de seguimientos
   - Acciones disponibles

3. **`POST /alerts/create`** - Crear nueva alerta (solo admin)
   - Asigna automáticamente al agente de la propiedad
   - Valida que la propiedad tenga agente asignado

4. **`POST /alerts/{alert_id}/mark-read`** - Marcar como leída
   - Registra timestamp de lectura
   - Cambia estado de PENDING a IN_PROGRESS

5. **`POST /alerts/{alert_id}/follow-up`** - Agregar seguimiento
   - Registra acción del agente
   - Permite programar próxima acción

6. **`POST /alerts/{alert_id}/complete`** - Completar alerta
   - Cambia estado a COMPLETED
   - Registra timestamp de finalización

7. **`GET /api/alerts/unread-count`** - Contador de alertas no leídas
   - Usado para el badge en el sidebar
   - Filtra por rol (admin/agente)

8. **`GET /alerts-dashboard`** - Dashboard de métricas (solo admin)
   - Métricas generales del sistema
   - Desempeño por agente
   - Alertas abandonadas

### 5. **Templates**

#### `alerts/list.html`
- Vista principal de alertas
- Cards con métricas (Pendientes, En Proceso, Completadas)
- Tabla con todas las alertas
- Modal para crear nueva alerta (solo admin)
- Badges de prioridad y estado

#### `alerts/detail.html`
- Información completa del interesado
- Datos de la propiedad
- Timeline de seguimientos
- Sidebar con acciones rápidas:
  - Marcar como leída
  - Agregar seguimiento
  - Completar alerta
- Modal para agregar seguimiento

#### `alerts/dashboard.html` (solo admin)
- 4 cards con métricas principales:
  - Total de alertas
  - Alertas pendientes
  - Alertas completadas
  - Tiempo promedio de respuesta
- Alerta visual de alertas abandonadas (>7 días)
- Tabla de desempeño por agente:
  - Total alertas
  - Pendientes
  - Completadas
  - Tiempo respuesta promedio
  - Última actividad
  - Tasa de conversión

### 6. **Sidebar con Badge**

Modificado: `components/sidebar.html`

- Nuevo enlace "Alertas" con icono de campana
- Badge rojo que muestra contador de alertas no leídas
- Actualización automática cada 2 minutos vía AJAX
- Enlace "Dashboard Alertas" (solo visible para admin)

---

## 🔄 Flujo de Uso

### Flujo Completo (Ejemplo Real):

1. **10:00 AM** - Admin recibe email de Idealista: "Juan Pérez interesado en Piso Centro"
   
2. **10:05 AM** - Admin accede a `/alerts` → Click "Nueva Alerta"
   - Selecciona: Piso Centro
   - Nombre: Juan Pérez
   - Teléfono: 666555444
   - Email: juan@example.com
   - Origen: Idealista
   - Tipo: Lead Interesado
   - Prioridad: ALTA
   - Sistema asigna automáticamente al agente Carlos

3. **11:30 AM** - Agente Carlos se loguea
   - Ve badge "1" en "Alertas" del sidebar
   - Accede a `/alerts` → Ve la alerta sin leer (fila con fondo azul)
   - Click "Ver Detalle" → `/alerts/123`

4. **11:35 AM** - Carlos marca como leída (automático al abrir)
   - Estado cambia de PENDING → IN_PROGRESS
   - Llama a Juan Pérez
   - Click "Agregar Seguimiento":
     - Tipo: LLAMADA
     - Notas: "Interesado, quiere visita jueves 16:00"
     - Próxima acción: 2026-07-10 16:00

5. **Jueves 16:00** - Después de la visita
   - Carlos agrega nuevo seguimiento:
     - Tipo: VISITA_PROGRAMADA
     - Notas: "Visita realizada, muy interesado, consulta con banco"
     - Próxima acción: 2026-07-12 10:00

6. **Viernes 11:00** - Juan hace oferta
   - Carlos agrega seguimiento:
     - Tipo: OFERTA_RECIBIDA
     - Notas: "Oferta formal 190k (precio pedido 200k)"
   - Click "Completar Alerta"
   - Estado → COMPLETED

7. **Fin de mes** - Admin revisa dashboard `/alerts-dashboard`
   - Ve que Carlos:
     - Atendió 15 alertas
     - Tiempo promedio respuesta: 2.3 horas
     - Tasa conversión: 33% (5 de 15 completadas)

---

## 📊 Métricas y Reportes

### Métricas Automáticas Calculadas:

1. **Tiempo de Respuesta**: Diferencia entre `created_at` y `read_at`
2. **Tasa de Conversión**: `alertas_completadas / total_alertas * 100`
3. **Alertas Abandonadas**: Alertas con status PENDING y más de 7 días sin leer
4. **Actividad por Agente**: Última fecha de creación de alerta para cada agente

---

## 🎨 Características UX

### Indicadores Visuales:

1. **Badges de Estado**:
   - Pendiente: amarillo
   - En Proceso: azul
   - Completada: verde

2. **Badges de Prioridad**:
   - Alta: rojo
   - Normal: azul
   - Baja: gris

3. **Alertas No Leídas**: Fila con fondo azul claro en la lista

4. **Contador en Sidebar**: Badge rojo con número de alertas no leídas

5. **Alertas Abandonadas**: Box rojo destacado en dashboard

### Responsive Design:

- Todas las vistas adaptadas a móvil/tablet/desktop
- Tabla con scroll horizontal en pantallas pequeñas
- Cards apiladas verticalmente en móvil

---

## 🔐 Permisos y Seguridad

### Control de Acceso:

1. **Admin**:
   - Crear alertas
   - Ver todas las alertas
   - Acceder al dashboard de métricas
   - Ver alertas de todos los agentes

2. **Agente**:
   - Ver solo sus alertas (filtradas por `agent_id`)
   - Marcar como leídas
   - Agregar seguimientos
   - Completar alertas

### Validaciones:

- Verificación de propiedad tiene agente asignado antes de crear alerta
- Verificación de permisos en cada endpoint
- Filtrado automático por rol en queries

---

## 🚀 Próximos Pasos (Opcionales/Futuro)

1. **Notificaciones Push**:
   - Enviar email al agente cuando se crea alerta de prioridad ALTA
   - Notificaciones browser (Web Push API)

2. **Integración con Portales**:
   - Webhooks de Idealista/Fotocasa para crear alertas automáticamente
   - Parser de emails para extracción automática de datos

3. **Recordatorios Automáticos**:
   - Enviar recordatorio si alerta tiene `next_action_date` próxima
   - Notificar alertas pendientes > 3 días sin seguimiento

4. **Exportación de Reportes**:
   - Dashboard exportable a PDF
   - CSV con listado de alertas

5. **Estadísticas Avanzadas**:
   - Gráficos de evolución temporal
   - Comparativa mensual de desempeño
   - Alertas por origen/portal

---

## 📝 Notas Técnicas

### Dependencias Necesarias:

Ya incluidas en el proyecto:
- FastAPI
- SQLAlchemy
- Jinja2
- PostgreSQL

### Variables de Entorno:

No requiere configuración adicional, usa la conexión de BD existente.

### Testing:

Para probar el sistema:
1. Aplicar migración: `alembic upgrade head`
2. Iniciar servidor: `uvicorn app.main:app --reload`
3. Loguearse como admin
4. Crear una alerta de prueba desde `/alerts`
5. Loguearse como agente y verificar visibilidad

---

## 🐛 Troubleshooting

### Si las alertas no aparecen:

1. Verificar que la propiedad tiene `agent_id` asignado
2. Verificar que el usuario agente tiene email que coincide con tabla `agents`
3. Revisar logs del servidor para errores SQL

### Si el badge no se actualiza:

1. Verificar consola del navegador para errores JS
2. Confirmar que endpoint `/api/alerts/unread-count` responde correctamente
3. Verificar que el usuario tiene sesión activa

---

## ✅ Checklist de Implementación

- [x] Modelos de BD creados
- [x] Migración generada
- [x] Constantes definidas
- [x] Rutas API implementadas
- [x] Templates creados
- [x] Sidebar actualizado con badge
- [x] Dashboard de métricas
- [x] Permisos configurados
- [x] Documentación completa

---

## 📞 Soporte

Para dudas o ajustes adicionales, revisar:
- Modelos: `backend/app/models/property_alert.py` y `alert_follow_up.py`
- Rutas: `backend/app/web/routes/alerts.py`
- Templates: `backend/app/web/templates/alerts/`
- Constantes: `backend/app/core/constants.py`
