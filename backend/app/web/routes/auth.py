from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends
from fastapi import Form
from fastapi import HTTPException

from sqlalchemy.orm import Session

from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

from app.db.deps import get_db
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission

from app.services.auth_service import authenticate_user
from app.core.security import create_access_token
from app.services.user_service import create_user, delete_user
from app.schemas.user import UserCreate
from app.web.utils.flash import set_flash

router = APIRouter()

templates = Jinja2Templates(
    directory="app/web/templates"
)


@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "request": request
        }
    )


@router.get("/auth", response_class=HTMLResponse)
async def auth_page(
    request: Request,
    db: Session = Depends(get_db)
):
    from app.web.dependencies.auth import require_admin_role

    # Validar que solo admin pueda acceder
    admin_user = require_admin_role(request, db)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    users = db.query(User).all()

    roles = db.query(Role).all()

    permissions = db.query(Permission).all()

    current_user = request.state.user

    return templates.TemplateResponse(
        request=request,
        name="auth/home.html",
        context={
            "request": request,
            "users": users,
            "roles": roles,
            "permissions": permissions,
            "current_user": current_user
        }
    )



@router.post("/login")
async def login(
    request: Request,
    username: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)):

    # Validación amigable
    if not username or not password:

        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Todos los campos son obligatorios"
            }
        )

    user = authenticate_user(
        db,
        username,
        password
    )

    if not user:

        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Credenciales inválidas"
            }
        )

    token = create_access_token(
        {"sub": user.email}
    )

    response = RedirectResponse(
        url="/dashboard",
        status_code=302
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax"
    )

    return response


@router.get("/logout")
async def logout():

    response = RedirectResponse(
        url="/",
        status_code=302
    )

    response.delete_cookie("access_token")

    return response


@router.post("/auth/users/create")
async def create_user_endpoint(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role_id: int = Form(...),
    db: Session = Depends(get_db)
):
    from app.web.dependencies.auth import require_admin_role

    # Validar que solo admin pueda crear usuarios
    admin_user = require_admin_role(request, db)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    response = RedirectResponse(url="/auth", status_code=303)

    try:
        user_data = UserCreate(
            email=email,
            full_name=full_name,
            password=password,
            role_id=role_id
        )

        create_user(db, user_data)
        set_flash(response, "success", "Usuario creado correctamente")

    except HTTPException as e:
        set_flash(response, "error", e.detail)

    return response


@router.post("/auth/users/delete/{user_id}")
async def delete_user_endpoint(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    from app.web.dependencies.auth import require_admin_role

    # Validar que solo admin pueda eliminar usuarios
    admin_user = require_admin_role(request, db)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    response = RedirectResponse(url="/auth", status_code=303)

    try:
        # No permitir que el admin se elimine a sí mismo
        if admin_user.id == user_id:
            set_flash(response, "error", "No puedes eliminar tu propio usuario")
            return response

        delete_user(db, user_id)
        set_flash(response, "success", "Usuario eliminado correctamente")

    except HTTPException as e:
        set_flash(response, "error", e.detail)

    return response