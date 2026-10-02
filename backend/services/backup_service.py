import datetime
import os
import zipfile

from sqlalchemy.orm import Session

from config import BACKUPS_DIR, DOCS_DIR, PROJECT_ROOT, TEMPLATES_DIR, UPLOADS_DIR
from database import DB_PATH
from models import Backup, User


def create_backup(db: Session, user: User | None) -> Backup:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ns_system_backup_{stamp}.zip"
    output = os.path.join(BACKUPS_DIR, filename)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        if os.path.exists(DB_PATH):
            archive.write(DB_PATH, arcname="database/hr_system.db")
        for folder, prefix in (
            (DOCS_DIR, "generated_documents"),
            (TEMPLATES_DIR, "templates"),
            (UPLOADS_DIR, "uploads"),
        ):
            if not os.path.exists(folder):
                continue
            for root, _, files in os.walk(folder):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, PROJECT_ROOT)
                    archive.write(full, arcname=os.path.join(prefix, os.path.relpath(full, folder)))
                    _ = rel
    record = Backup(
        file_name=filename,
        file_path=output,
        created_by=user.id if user else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
