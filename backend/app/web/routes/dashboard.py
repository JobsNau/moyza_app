from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.deps import get_db
from fastapi.responses import RedirectResponse

from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates

from app.web.dependencies.auth import get_current_web_user

from app.models.user import User

router = APIRouter()

templates = Jinja2Templates(
    directory="app/web/templates"
)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):

    from app.web.dependencies.auth import require_admin_role

    # Validar que solo admin pueda acceder
    admin_user = require_admin_role(request, db)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    current_user = request.state.user

    return templates.TemplateResponse(
        request=request,
        name="dashboard/home.html",
        context={
            "request": request,
            "current_user": current_user
        }
    )