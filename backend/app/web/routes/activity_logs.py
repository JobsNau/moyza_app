from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.web.template_env import templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.db.deps import get_db
from app.models.user_activity_log import UserActivityLog
from app.models.user import User

router = APIRouter()


@router.get("/activity-logs", response_class=HTMLResponse)
async def activity_logs(request: Request, db: Session = Depends(get_db)):
    from app.web.dependencies.auth import require_admin_role

    admin_user = require_admin_role(request, db)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    # Últimos 200 registros con usuario
    logs = (
        db.query(UserActivityLog)
        .options(joinedload(UserActivityLog.user))
        .order_by(desc(UserActivityLog.created_at))
        .limit(200)
        .all()
    )

    # Stats por usuario: total requests y última actividad
    user_stats = (
        db.query(
            UserActivityLog.user_id,
            User.full_name,
            User.email,
            func.count(UserActivityLog.id).label("total_requests"),
            func.max(UserActivityLog.created_at).label("last_seen"),
        )
        .outerjoin(User, User.id == UserActivityLog.user_id)
        .filter(UserActivityLog.user_id.isnot(None))
        .group_by(UserActivityLog.user_id, User.full_name, User.email)
        .order_by(desc("last_seen"))
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="activity_logs/list.html",
        context={
            "request": request,
            "logs": logs,
            "user_stats": user_stats,
            "current_user": request.state.user,
        },
    )
