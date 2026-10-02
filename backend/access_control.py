import json

from models import ROLE_ADMIN, ROLE_HR, User


PERMISSION_GROUPS = {
    "dashboard": {"label": "Панель управления", "permissions": {"dashboard.view": "Просмотр"}},
    "employees": {
        "label": "Сотрудники",
        "permissions": {
            "employees.view": "Просмотр",
            "employees.create": "Создание",
            "employees.edit": "Изменение",
            "employees.archive": "Архивирование",
            "employees.export": "Экспорт",
        },
    },
    "documents": {
        "label": "Документы",
        "permissions": {
            "documents.view": "Просмотр",
            "documents.download": "Скачивание",
            "documents.generate": "Формирование",
            "documents.export": "Экспорт",
            "documents.clear": "Очистка списка",
        },
    },
    "absences": {
        "label": "Отпуска и отсутствия",
        "permissions": {
            "absences.view": "Просмотр",
            "absences.manage": "Добавление и изменение записей",
        },
    },
    "templates": {
        "label": "Шаблоны документов",
        "permissions": {
            "templates.view": "Просмотр",
            "templates.manage": "Загрузка и активация",
            "templates.archive": "Архивирование версии",
        },
    },
    "audit": {"label": "Журнал действий", "permissions": {"audit.view": "Просмотр"}},
    "users": {"label": "Пользователи и роли", "permissions": {"users.manage": "Управление"}},
    "settings": {"label": "Настройки", "permissions": {"settings.manage": "Управление"}},
    "references": {"label": "Справочники", "permissions": {"references.manage": "Управление"}},
    "errors": {"label": "Ошибки системы", "permissions": {"errors.view": "Просмотр"}},
    "ocr": {"label": "Распознавание удостоверений", "permissions": {"ocr.use": "Использование"}},
    "enbek": {"label": "Enbek", "permissions": {"enbek.view": "Просмотр раздела"}},
}

ALL_PERMISSIONS = frozenset(
    permission
    for group in PERMISSION_GROUPS.values()
    for permission in group["permissions"]
)

HR_DEFAULT_PERMISSIONS = frozenset({
    "dashboard.view",
    "employees.view",
    "employees.create",
    "employees.edit",
    "employees.archive",
    "employees.export",
    "documents.view",
    "documents.download",
    "documents.generate",
    "documents.export",
    "absences.view",
    "absences.manage",
    "templates.view",
    "templates.manage",
    "audit.view",
    "ocr.use",
    "enbek.view",
})


def permissions_for_role(role) -> list[str]:
    role_name = role.name if role else ""
    if role_name == ROLE_ADMIN:
        return sorted(ALL_PERMISSIONS)
    if role and role.permissions:
        try:
            stored = json.loads(role.permissions)
        except (TypeError, json.JSONDecodeError):
            stored = []
        if not isinstance(stored, list):
            return []
        return sorted({item for item in stored if isinstance(item, str)} & ALL_PERMISSIONS)
    if role_name == ROLE_HR:
        return sorted(HR_DEFAULT_PERMISSIONS)
    return []


def permissions_for_user(user: User) -> list[str]:
    return permissions_for_role(user.role)


def serialize_permissions(permissions: list[str]) -> str:
    return json.dumps(sorted(set(permissions) & ALL_PERMISSIONS), ensure_ascii=False)