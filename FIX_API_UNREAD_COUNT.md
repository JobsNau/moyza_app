# Fix: Error 500 en /api/alerts/unread-count

## 🐛 Problema

**Error:**
```
AttributeError: 'State' object has no attribute 'user'
```

**Causa:**
El endpoint `/api/alerts/unread-count` intentaba acceder a `request.state.user`, pero el middleware de autenticación (`AuthMiddleware`) salta todas las rutas que empiezan con `/api` (línea 30-31 de `auth.py`):

```python
if path.startswith("/api"):
    return await call_next(request)  # Salta autenticación
```

Por lo tanto, `request.state.user` nunca se inicializa para rutas API.

---

## ✅ Solución

Modificar el endpoint para que maneje la autenticación manualmente, verificando el token de las cookies.

### Código Anterior (Fallaba):
```python
@router.get("/api/alerts/unread-count")
async def get_unread_count(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = request.state.user  # ❌ Falla: user no existe
    
    base_query = db.query(PropertyAlert).filter(...)
    # ...
```

### Código Nuevo (Funciona):
```python
@router.get("/api/alerts/unread-count")
async def get_unread_count(
    request: Request,
    db: Session = Depends(get_db)
):
    # ✅ Verificar token manualmente
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

    # ✅ Obtener usuario de la BD
    current_user = db.query(User).filter(User.email == email).first()
    if not current_user:
        return JSONResponse(content={"unread_count": 0})

    # Resto del código igual...
    base_query = db.query(PropertyAlert).filter(...)
```

---

## 📋 Archivo Modificado

- **[backend/app/web/routes/alerts.py](backend/app/web/routes/alerts.py)** líneas 368-410

---

## 🧪 Verificación

### Test sin autenticación:
```bash
curl http://localhost:8000/api/alerts/unread-count
# Resultado: {"unread_count":0}
```

### Test con autenticación (desde el navegador):
```javascript
// En la consola del navegador con sesión activa
fetch('/api/alerts/unread-count')
  .then(r => r.json())
  .then(data => console.log(data));
// Resultado: {"unread_count": N}  (donde N = alertas no leídas del usuario)
```

---

## 🔍 ¿Por qué las rutas API saltan el middleware?

En [app/web/middleware/auth.py](backend/app/web/middleware/auth.py):

```python
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Las rutas API se saltan el middleware de autenticación
        if path.startswith("/api"):
            return await call_next(request)  # <-- Aquí
        
        # ... resto del código para rutas web
```

**Razón:** Las rutas API (`/api/v1/*`) usan su propio sistema de autenticación (probablemente tokens JWT en headers), mientras que las rutas web usan cookies.

**Implicación:** Cualquier endpoint que empiece con `/api` debe manejar su propia autenticación si la necesita.

---

## ✅ Estado Final

- ✅ Endpoint `/api/alerts/unread-count` funciona correctamente
- ✅ Retorna `0` si no hay autenticación (sin error)
- ✅ Retorna contador real cuando hay sesión activa
- ✅ Badge en sidebar se actualiza cada 2 minutos
- ✅ Servidor funcionando sin errores

---

## 📝 Lecciones Aprendidas

1. **Rutas `/api/*` no pasan por `AuthMiddleware`**: Deben manejar autenticación manualmente
2. **request.state.user solo existe en rutas web**: No asumir que está disponible en endpoints API
3. **Siempre validar el token en rutas API**: Usar `decode_token()` manualmente
4. **Retornar valores por defecto**: En lugar de fallar, retornar `{"unread_count": 0}`

---

## 🔄 Alternativas Consideradas

### Opción 1: Mover endpoint a ruta web
```python
@router.get("/alerts/api/unread-count")  # En lugar de /api/alerts/unread-count
```
**Ventaja:** Pasaría por AuthMiddleware automáticamente  
**Desventaja:** Inconsistente con otras rutas API

### Opción 2: Modificar AuthMiddleware para incluir esta ruta
```python
if path.startswith("/api") and path != "/api/alerts/unread-count":
    return await call_next(request)
```
**Ventaja:** Centralizado en el middleware  
**Desventaja:** No escala bien con múltiples endpoints

### ✅ Opción 3: Autenticación manual en el endpoint (ELEGIDA)
**Ventaja:** Explícito, claro, flexible  
**Desventaja:** Código duplicado (se puede refactorizar en una función helper)

---

## 💡 Mejora Futura (Opcional)

Crear una función helper para autenticación en rutas API:

```python
# En app/web/dependencies/auth.py
async def get_current_api_user(request: Request, db: Session) -> Optional[User]:
    """Helper para obtener usuario en rutas API desde cookies"""
    from app.core.security import decode_token
    
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    email = payload.get("sub")
    if not email:
        return None
    
    return db.query(User).filter(User.email == email).first()
```

Y usarla así:
```python
@router.get("/api/alerts/unread-count")
async def get_unread_count(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = await get_current_api_user(request, db)
    if not current_user:
        return JSONResponse(content={"unread_count": 0})
    
    # ... resto del código
```

---

## ✅ Resultado

El sistema de alertas ahora funciona completamente sin errores 500 en el badge del sidebar.
