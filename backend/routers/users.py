from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from database import get_db
from deps import client_ip, require_admin, require_permission
from access_control import ALL_PERMISSIONS, PERMISSION_GROUPS, permissions_for_role, permissions_for_user, serialize_permissions
from models import ROLE_ADMIN, ROLE_HR, Role, User
from schemas import RoleCreate, RoleOut, RoleUpdate, UserCreate, UserOut, UserUpdate
from security import hash_password
from services.audit_service import write_audit

router = APIRouter(prefix="/users", tags=["Users"])
def _to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role.name if user.role else "",
        is_active=user.is_active,
        created_at=user.created_at,
        permissions=permissions_for_user(user),
    )


def _role_out(role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        permissions=permissions_for_role(role),
        is_system=role.name in {ROLE_ADMIN, ROLE_HR},
    )


@router.get("/permission-catalog")
def permission_catalog(_: User = Depends(require_admin)):
    return PERMISSION_GROUPS


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_role_out(role) for role in db.query(Role).order_by(Role.id.asc()).all()]


@router.get("/assignable-roles", response_model=list[RoleOut])
def list_assignable_roles(
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    current_permissions = set(permissions_for_user(current))
    roles = db.query(Role).order_by(Role.id.asc()).all()
    if current.role and current.role.name == ROLE_ADMIN:
        return [_role_out(role) for role in roles]
    return [
        _role_out(role)
        for role in roles
        if role.name != ROLE_ADMIN
        and set(permissions_for_role(role)).issubset(current_permissions)
    ]


@router.post("/roles", response_model=RoleOut)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    role_name = payload.name.strip()
    if len(role_name) < 2:
        raise HTTPException(status_code=422, detail="Название роли слишком короткое")
    if role_name in {ROLE_ADMIN, ROLE_HR}:
        raise HTTPException(status_code=409, detail="Это системное имя роли")
    if db.query(Role).filter(Role.name == role_name).first():
        raise HTTPException(status_code=409, detail="Такая роль уже существует")
    unknown = set(payload.permissions) - ALL_PERMISSIONS
    if unknown:
        raise HTTPException(status_code=422, detail="Список прав содержит неизвестные разрешения")
    role = Role(name=role_name, permissions=serialize_permissions(payload.permissions))
    db.add(role)
    db.flush()
    write_audit(
        db,
        "Создана роль",
        user=current,
        object_type="role",
        object_id=role.id,
        details=role.name,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    if role.name == ROLE_ADMIN:
        raise HTTPException(status_code=409, detail="Системную роль Admin нельзя изменять")
    changes = []
    if payload.name is not None:
        new_name = payload.name.strip()
        if len(new_name) < 2:
            raise HTTPException(status_code=422, detail="Название роли слишком короткое")
        if role.name in {ROLE_ADMIN, ROLE_HR} and new_name != role.name:
            raise HTTPException(status_code=409, detail="Имя системной роли нельзя изменить")
        if new_name in {ROLE_ADMIN, ROLE_HR} and new_name != role.name:
            raise HTTPException(status_code=409, detail="Это системное имя роли")
        duplicate = db.query(Role).filter(Role.name == new_name, Role.id != role.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Такая роль уже существует")
        if new_name != role.name:
            changes.append(f"имя: {role.name} → {new_name}")
            role.name = new_name
    if payload.permissions is not None:
        unknown = set(payload.permissions) - ALL_PERMISSIONS
        if unknown:
            raise HTTPException(status_code=422, detail="Список прав содержит неизвестные разрешения")
        role.permissions = serialize_permissions(payload.permissions)
        changes.append("обновлён набор разрешений")
    write_audit(
        db,
        "Изменена роль",
        user=current,
        object_type="role",
        object_id=role.id,
        details="; ".join(changes),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    if role.name in {ROLE_ADMIN, ROLE_HR}:
        raise HTTPException(status_code=409, detail="Системную роль нельзя удалить")
    if db.query(User).filter(User.role_id == role.id).first():
        raise HTTPException(status_code=409, detail="Сначала переназначьте пользователей этой роли")
    write_audit(
        db,
        "Удалена роль",
        user=current,
        object_type="role",
        object_id=role.id,
        details=role.name,
        ip_address=client_ip(request),
    )
    db.delete(role)
    db.commit()
    return {"ok": True}


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), current: User = Depends(require_permission("users.manage"))):
    users = db.query(User).options(joinedload(User.role)).order_by(User.id.asc()).all()
    if not current.role or current.role.name != ROLE_ADMIN:
        current_permissions = set(permissions_for_user(current))
        users = [
            user
            for user in users
            if user.role
            and user.role.name != ROLE_ADMIN
            and set(permissions_for_role(user.role)).issubset(current_permissions)
        ]
    return [_to_out(user) for user in users]


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Пользователь уже существует")
    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        raise HTTPException(status_code=422, detail="Роль не найдена")
    if role.name == ROLE_ADMIN and (not current.role or current.role.name != ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Нельзя назначить системную роль Admin")
    if not set(permissions_for_role(role)).issubset(set(permissions_for_user(current))):
        raise HTTPException(status_code=403, detail="Нельзя назначить роль с более широкими правами")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        "Создан пользователь",
        user=current,
        object_type="user",
        object_id=user.id,
        details=f"{user.username} / {payload.role}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    user = db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not current.role or current.role.name != ROLE_ADMIN:
        if not user.role or user.role.name == ROLE_ADMIN:
            raise HTTPException(status_code=403, detail="Недостаточно прав для изменения этого пользователя")
        if not set(permissions_for_role(user.role)).issubset(set(permissions_for_user(current))):
            raise HTTPException(status_code=403, detail="Нельзя изменять пользователя с более широкими правами")
    details = []
    if payload.role:
        role = db.query(Role).filter(Role.name == payload.role).first()
        if not role:
            raise HTTPException(status_code=422, detail="Роль не найдена")
        if role.name == ROLE_ADMIN and (not current.role or current.role.name != ROLE_ADMIN):
            raise HTTPException(status_code=403, detail="Нельзя назначить системную роль Admin")
        if not set(permissions_for_role(role)).issubset(set(permissions_for_user(current))):
            raise HTTPException(status_code=403, detail="Нельзя назначить роль с более широкими правами")
        if user.id == current.id and role.id != current.role_id:
            raise HTTPException(status_code=409, detail="Нельзя изменить собственную роль")
        if user.role and user.role.name == ROLE_ADMIN and role.name != ROLE_ADMIN:
            active_admins = (
                db.query(User)
                .join(Role, User.role_id == Role.id)
                .filter(Role.name == ROLE_ADMIN, User.is_active == True)  # noqa: E712
                .count()
            )
            if active_admins <= 1:
                raise HTTPException(status_code=409, detail="Нельзя снять права с последнего активного Admin")
        details.append(f"роль: {user.role.name if user.role else ''} → {payload.role}")
        user.role_id = role.id
    if payload.is_active is not None:
        details.append(f"статус: {user.is_active} → {payload.is_active}")
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)
        details.append("пароль изменён")
    write_audit(
        db,
        "Изменена роль" if payload.role else "Изменён пользователь",
        user=current,
        object_type="user",
        object_id=user.id,
        details="; ".join(details),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("users.manage")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.id == current.id:
        raise HTTPException(status_code=409, detail="Нельзя удалить собственную учётную запись")
    if not current.role or current.role.name != ROLE_ADMIN:
        if not user.role or user.role.name == ROLE_ADMIN:
            raise HTTPException(status_code=403, detail="Недостаточно прав для удаления этого пользователя")
        if not set(permissions_for_role(user.role)).issubset(set(permissions_for_user(current))):
            raise HTTPException(status_code=403, detail="Нельзя удалять пользователя с более широкими правами")
    write_audit(
        db,
        "Удалён пользователь",
        user=current,
        object_type="user",
        object_id=user.id,
        details=user.username,
        ip_address=client_ip(request),
    )
    db.delete(user)
    db.commit()
    return {"ok": True}
