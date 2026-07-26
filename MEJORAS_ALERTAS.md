# Mejoras Sistema de Alertas

## ✅ Implementadas (2026-07-07)

### 1. **Eliminar Alertas (Solo Admin)**

#### Backend:
- **Ruta**: `POST /alerts/{alert_id}/delete`
- **Permisos**: Solo administradores
- **Comportamiento**: 
  - Elimina la alerta y todos sus seguimientos (cascade)
  - Mensaje de confirmación antes de eliminar
  - Flash message de éxito/error

#### Frontend:
- **Botón en Lista**: Aparece en la columna de acciones (solo para admin)
- **Botón en Detalle**: En el sidebar de acciones (solo para admin)
- **Confirmación**: Diálogo JavaScript para prevenir eliminación accidental

**Código agregado:**
- [app/web/routes/alerts.py:260-290](backend/app/web/routes/alerts.py) - Endpoint delete
- [app/web/templates/alerts/list.html](backend/app/web/templates/alerts/list.html) - Botón en lista
- [app/web/templates/alerts/detail.html](backend/app/web/templates/alerts/detail.html) - Botón en detalle

---

### 2. **Asignación Automática por Propiedad → Agente**

#### Flujo Completo:

**Paso 1: Creación de Alerta (Admin)**
```python
# 1. Admin selecciona PROPIEDAD en el formulario
# 2. Sistema obtiene automáticamente el agent_id de esa propiedad
property_item = db.query(Property).filter(Property.id == property_id).first()

# 3. Asigna la alerta al agente de la propiedad
alert = PropertyAlert(
    property_id=property_id,
    agent_id=property_item.agent_id,  # <-- Asignación automática
    lead_name=lead_name,
    # ...
)
```

**Paso 2: Login del Agente**
```python
# 1. Usuario agente se loguea con su email (ej: carlos@inmobiliaria.com)
# 2. Sistema busca Agent con ese email
agent = db.query(Agent).filter(Agent.email == user.email).first()

# 3. Filtra alertas solo de ese agente
if not is_admin(current_user):
    base_query = base_query.filter(PropertyAlert.agent_id == agent.id)
```

**Paso 3: Visualización**
- Agente Carlos solo ve alertas donde `PropertyAlert.agent_id == carlos.id`
- Badge en sidebar muestra solo alertas no leídas del agente
- Al abrir detalle, puede agregar seguimientos

---

## 🔗 Relación de Datos

```
User (email: carlos@inmobiliaria.com)
  ↓ (vinculado por email)
Agent (id: 5, email: carlos@inmobiliaria.com)
  ↓ (asignado a)
Property (id: 123, agent_id: 5, title: "Piso Centro")
  ↓ (genera)
PropertyAlert (id: 456, property_id: 123, agent_id: 5, lead_name: "Juan Pérez")
```

**Cuando Juan Pérez se interesa en "Piso Centro":**
1. Admin crea alerta seleccionando "Piso Centro" (property_id: 123)
2. Sistema detecta que "Piso Centro" tiene agent_id: 5 (Carlos)
3. Alerta se asigna automáticamente a Carlos
4. Carlos se loguea → Ve la alerta → Badge muestra "1"
5. Carlos abre alerta → Marca como leída → Agrega seguimiento

---

## 🎯 Validaciones Implementadas

### Al Crear Alerta:
```python
# 1. Verifica que la propiedad existe
if not property_item:
    return error("Propiedad no encontrada")

# 2. Verifica que la propiedad tiene agente asignado
if not property_item.agent_id:
    return error("La propiedad no tiene agente asignado")

# 3. Crea alerta con agent_id automático
alert.agent_id = property_item.agent_id
```

### Al Ver Alertas (Agente):
```python
# 1. Obtiene Agent vinculado al email del usuario
agent = get_agent_from_user(current_user, db)

# 2. Si no tiene Agent asociado, no muestra nada
if not agent:
    base_query = base_query.filter(PropertyAlert.id == -1)

# 3. Si tiene Agent, filtra por agent_id
else:
    base_query = base_query.filter(PropertyAlert.agent_id == agent.id)
```

---

## 📋 Casos de Uso

### Caso 1: Agente con Múltiples Propiedades
**Situación:**
- Agente Carlos tiene 15 propiedades asignadas
- Llegan 3 leads: 1 para Piso A, 1 para Casa B, 1 para Local C

**Resultado:**
- Carlos ve 3 alertas en su panel
- Badge muestra "3"
- Todas las alertas están vinculadas a propiedades donde él es el agente

---

### Caso 2: Propiedad Sin Agente
**Situación:**
- Admin crea una propiedad pero olvida asignar agente
- Llega un lead para esa propiedad

**Resultado:**
- Al intentar crear alerta, sistema muestra error:
  > "La propiedad no tiene agente asignado"
- Admin debe primero asignar un agente a la propiedad

---

### Caso 3: Admin Elimina Alerta
**Situación:**
- Alerta duplicada o lead inválido

**Resultado:**
- Admin ve botón "Eliminar" en lista y detalle
- Click → Confirmación JavaScript
- Si confirma → Alerta y seguimientos eliminados
- Flash message: "Alerta de Juan Pérez eliminada correctamente"

---

## 🔐 Permisos

| Acción | Admin | Agente |
|--------|-------|--------|
| Ver todas las alertas | ✅ | ❌ (solo las suyas) |
| Ver alertas de su propiedad | ✅ | ✅ |
| Crear alerta | ✅ | ❌ |
| Marcar como leída | ✅ | ✅ |
| Agregar seguimiento | ✅ | ✅ |
| Completar alerta | ✅ | ✅ |
| Eliminar alerta | ✅ | ❌ |
| Ver dashboard métricas | ✅ | ❌ |

---

## 🧪 Cómo Probar

### Test 1: Crear y Asignar Alerta
```bash
1. Login como admin
2. Ir a /alerts
3. Click "Nueva Alerta"
4. Seleccionar propiedad que tiene agente asignado
5. Llenar datos del lead
6. Crear
7. Verificar que alert.agent_id == property.agent_id
```

### Test 2: Agente Ve Solo Sus Alertas
```bash
1. Login como agente Carlos (carlos@inmobiliaria.com)
2. Ir a /alerts
3. Verificar que solo aparecen alertas de propiedades de Carlos
4. Badge muestra solo alertas no leídas de Carlos
```

### Test 3: Eliminar Alerta (Admin)
```bash
1. Login como admin
2. Ir a /alerts
3. Click "Eliminar" en cualquier alerta
4. Confirmar en diálogo
5. Verificar que alerta desaparece
6. Verificar en BD que seguimientos también se eliminaron (cascade)
```

---

## 📊 SQL para Verificar Asignaciones

```sql
-- Ver todas las alertas con su propiedad y agente
SELECT 
    pa.id AS alert_id,
    pa.lead_name,
    p.title AS propiedad,
    a.name AS agente,
    pa.status
FROM property_alerts pa
JOIN properties p ON pa.property_id = p.id
JOIN agents a ON pa.agent_id = a.id
ORDER BY pa.created_at DESC;

-- Verificar que todas las alertas tienen agent_id
SELECT COUNT(*) 
FROM property_alerts 
WHERE agent_id IS NULL;
-- Resultado esperado: 0

-- Ver alertas de un agente específico
SELECT pa.*, p.title
FROM property_alerts pa
JOIN properties p ON pa.property_id = p.id
WHERE pa.agent_id = (SELECT id FROM agents WHERE email = 'carlos@inmobiliaria.com')
ORDER BY pa.created_at DESC;
```

---

## ✅ Checklist de Verificación

- [x] Endpoint DELETE creado con validación admin
- [x] Botón eliminar en lista (solo admin)
- [x] Botón eliminar en detalle (solo admin)
- [x] Confirmación JavaScript antes de eliminar
- [x] Cascade delete de seguimientos
- [x] Asignación automática agent_id al crear alerta
- [x] Validación de propiedad tiene agente
- [x] Filtro por agent_id cuando agente se loguea
- [x] Badge muestra solo alertas del agente
- [x] get_agent_from_user vincula por email

---

## 🎉 Resultado Final

**Para el Admin:**
- Crea alertas seleccionando propiedad
- Sistema asigna automáticamente al agente correcto
- Puede eliminar alertas cuando sea necesario
- Ve todas las alertas en el dashboard

**Para el Agente:**
- Se loguea y ve solo alertas de SUS propiedades
- Badge muestra cuántas alertas sin leer tiene
- No puede ver alertas de otros agentes
- No puede eliminar alertas (solo admin)

**Ventajas:**
✅ Asignación automática = menos errores
✅ Filtrado automático = más seguridad
✅ Vinculación por email = fácil de gestionar
✅ Admin puede limpiar alertas duplicadas/inválidas
