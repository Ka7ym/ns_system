import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("NS_SECRET_KEY", "ns-system-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("NS_TOKEN_EXPIRE_MINUTES", "480"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "NS_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

MAX_UPLOAD_MB = int(os.environ.get("NS_MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
TESSERACT_CMD = os.environ.get("NS_TESSERACT_CMD", "")

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
GENERATED_DIR = os.path.join(PROJECT_ROOT, "generated_documents")
DOCS_DIR = GENERATED_DIR
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")
IDENTITY_DIR = os.path.join(UPLOADS_DIR, "identity")
BACKUPS_DIR = os.path.join(PROJECT_ROOT, "backups")
SETTINGS_PATH = os.path.join(BACKEND_DIR, "app_settings.json")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(IDENTITY_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)


def load_app_settings() -> dict:
    import json

    defaults = {"max_upload_mb": MAX_UPLOAD_MB, "tesseract_cmd": TESSERACT_CMD}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
                defaults.update(json.load(handle) or {})
        except (OSError, json.JSONDecodeError):
            pass
    return defaults


def save_app_settings(payload: dict) -> dict:
    import json

    current = load_app_settings()
    current.update({k: v for k, v in payload.items() if v is not None})
    with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
        json.dump(current, handle, ensure_ascii=False, indent=2)
    return current
