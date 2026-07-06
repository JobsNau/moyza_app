from fastapi import Request
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from app.db.deps import get_db

from app.core.security import decode_token

from app.models.user import User


def get_current_web_user(
    request: Request,
    db: Session = Depends(get_db)
):

    token = request.cookies.get("access_token")

    if not token:

        return RedirectResponse(url="/", status_code=302)

    payload = decode_token(token)

    if not payload:

        return RedirectResponse(url="/", status_code=302)

    email = payload.get("sub")

    if not email:

        return RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:

        return RedirectResponse(url="/", status_code=302)

    return user


def require_admin_role(
    request: Request,
    db: Session = Depends(get_db)
):
    """Valida que el usuario tenga rol de admin (asumiendo role.name = 'Admin')"""
    from app.web.utils.flash import set_flash

    user = get_current_web_user(request, db)

    # Si get_current_web_user retorna RedirectResponse, propagarlo
    if isinstance(user, RedirectResponse):
        return user

    # Validar que el usuario tenga rol admin
    if not user.role or user.role.name.lower() != 'admin':
        response = RedirectResponse(url="/dashboard", status_code=303)
        set_flash(response, "error", "Acceso denegado. Solo administradores pueden acceder a esta sección.")
        return response

    return user