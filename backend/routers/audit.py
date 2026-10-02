from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from deps import require_permission
from models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
def list_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit.view")),
):
    query = db.query(AuditLog).order_by(AuditLog.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {u.id: u.username for u in db.query(User).all()}
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "username": users.get(item.user_id) if item.user_id else None,
                "action": item.action,
                "object_type": item.object_type,
                "object_id": item.object_id,
                "result": item.result,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }
