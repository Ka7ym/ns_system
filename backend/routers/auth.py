from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from database import get_db
from access_control import permissions_for_user
from models import User
from schemas import LoginRequest, PasswordChange, TokenResponse, UserOut
from security import create_access_token, hash_password, is_bcrypt_hash, verify_password
from services.audit_service import add_audit
from services.file_service import client_ip
from deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).options(joinedload(User.role)).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        add_audit(db, "Вход в систему", "user", result="error", details="Неверный логин или пароль", ip_address=client_ip(request))
        db.commit()
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    if not is_bcrypt_hash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.add(user)
    role = user.role.name if user.role else ""
    token = create_access_token(user.id, user.username, role)
    add_audit(db, "Вход в систему", "user", user.id, user_id=user.id, ip_address=client_ip(request))
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "permissions": permissions_for_user(user),
        },
    }


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.name if user.role else "",
        "is_active": user.is_active,
        "created_at": user.created_at,
        "permissions": permissions_for_user(user),
    }


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    user.password_hash = hash_password(payload.new_password)
    add_audit(db, "Изменён пароль", "user", user.id, user_id=user.id, ip_address=client_ip(request))
    db.commit()
    return {"ok": True}
