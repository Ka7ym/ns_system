from database import engine, Base, SessionLocal
from models import ROLE_ADMIN, ROLE_HR, Role, User
from security import hash_password, is_bcrypt_hash
from access_control import HR_DEFAULT_PERMISSIONS, serialize_permissions
from services.document_service import ensure_builtin_templates


def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    if db.query(Role).count() == 0:
        admin_role = Role(name=ROLE_ADMIN)
        hr_role = Role(name=ROLE_HR, permissions=serialize_permissions(list(HR_DEFAULT_PERMISSIONS)))
        db.add(admin_role)
        db.add(hr_role)
        db.commit()
        db.refresh(admin_role)
        admin_user = User(username="admin", password_hash=hash_password("admin"), role_id=admin_role.id)
        db.add(admin_user)
        db.refresh(hr_role)
        if db.query(User).filter(User.username == "hr").first() is None:
            db.add(User(username="hr", password_hash=hash_password("hr12345"), role_id=hr_role.id))
        db.commit()
    else:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin and not is_bcrypt_hash(admin.password_hash):
            admin.password_hash = hash_password("admin")
            db.commit()
            print("Rehashed default admin password with bcrypt.")
        hr_role = db.query(Role).filter(Role.name == ROLE_HR).first()
        if hr_role and not hr_role.permissions:
            hr_role.permissions = serialize_permissions(list(HR_DEFAULT_PERMISSIONS))
            db.commit()
        if hr_role and db.query(User).filter(User.username == "hr").first() is None:
            db.add(User(username="hr", password_hash=hash_password("hr12345"), role_id=hr_role.id))
            db.commit()

    admin = db.query(User).filter(User.username == "admin").first()
    ensure_builtin_templates(db, admin.id if admin else None)
    db.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    init_db()
