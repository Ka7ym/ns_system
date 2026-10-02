from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from database import get_db
from access_control import permissions_for_user
from models import ROLE_ADMIN, ROLE_HR, User
from security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == int(payload["sub"]))
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь недоступен")
    request.state.current_user = user
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else ""
        if role_name not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return checker


def require_permission(permission: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if permission not in permissions_for_user(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return checker


require_hr = require_roles(ROLE_ADMIN, ROLE_HR)
require_admin = require_roles(ROLE_ADMIN)


def client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for") if request else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request and request.client else None
