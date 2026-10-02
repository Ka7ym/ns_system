from typing import Optional

from sqlalchemy.orm import Session

from models import AuditLog, EmployeeHistory, User


def add_history(
    db: Session,
    employee_id: int,
    action: str,
    description: str = "",
    user_id: Optional[int] = None,
) -> None:
    db.add(
        EmployeeHistory(
            employee_id=employee_id,
            action=action,
            description=description,
            created_by=user_id,
        )
    )


def add_audit(
    db: Session,
    action: str,
    object_type: Optional[str] = None,
    object_id: Optional[int] = None,
    result: str = "ok",
    details: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            result=result,
            details=details,
            ip_address=ip_address,
        )
    )


def write_audit(
    db: Session,
    action: str,
    *,
    user: Optional[User] = None,
    object_type: Optional[str] = None,
    object_id: Optional[int] = None,
    result: str = "ok",
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    add_audit(
        db,
        action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        details=details,
        user_id=user.id if user else None,
        ip_address=ip_address,
    )
