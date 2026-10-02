import os
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile

from config import IDENTITY_DIR, MAX_UPLOAD_BYTES, TEMPLATES_DIR

ALLOWED_IDENTITY = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "application/pdf": {".pdf"},
}

ALLOWED_TEMPLATE = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/zip": {".docx"},
}


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def validate_upload(file: UploadFile, kind: str) -> tuple[bytes, str, str]:
    mapping = ALLOWED_IDENTITY if kind == "identity" else ALLOWED_TEMPLATE
    filename = file.filename or ""
    ext = _ext(filename)
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    allowed_exts = set()
    for exts in mapping.values():
        allowed_exts.update(exts)
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    if content_type and content_type not in mapping and content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail="Недопустимый MIME-тип файла")
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Файл повреждён или пуст")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Файл превышает допустимый размер")
    if kind == "identity" and data[:2] not in (b"\xff\xd8", b"\x89P") and data[:4] != b"%PDF":
        if ext == ".pdf" and not data.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Файл повреждён")
        if ext in {".jpg", ".jpeg"} and data[:2] != b"\xff\xd8":
            raise HTTPException(status_code=400, detail="Файл повреждён")
        if ext == ".png" and data[:8] != b"\x89PNG\r\n\x1a\n":
            raise HTTPException(status_code=400, detail="Файл повреждён")
    if kind == "template" and not data.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="Шаблон должен быть файлом DOCX")
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return data, safe_name, ext


def save_bytes(data: bytes, directory: str, filename: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def save_identity(data: bytes, filename: str) -> str:
    return save_bytes(data, IDENTITY_DIR, filename)


def save_template(data: bytes, filename: str) -> str:
    return save_bytes(data, TEMPLATES_DIR, filename)


def client_ip(request) -> Optional[str]:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
