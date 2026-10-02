# NS SYSTEM

Внутренняя HR-система ТОО «НС Система».

## Стек

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- База: SQLite (`backend/hr_system.db`)
- Документы: python-docx + загружаемые шаблоны DOCX
- OCR: локальный Tesseract (без внешних AI-сервисов)

## Запуск Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs

Миграции выполняются автоматически при старте (`migrate_db.py` + `create_all`).

Учётная запись по умолчанию: `admin` / `admin` (пароль хранится как bcrypt-хеш).

## Запуск Frontend

```bash
cd frontend
npm install
npm run dev
```

Интерфейс: http://localhost:5173

## OCR

Нужен установленный [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).  
Если движок не найден, система покажет статус «OCR требует настройки» и позволит ввести данные вручную. Фиктивные результаты не возвращаются.

Для удостоверений Казахстана используются языковые модели `kaz`, `rus` и `eng`, несколько режимов сегментации страницы и альтернативная обработка контраста. PDF обрабатывается постранично. Распознанные ФИО и ИИН остаются редактируемыми и перед оформлением должны быть сверены HR с оригиналом.

Опционально: `NS_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

Для Windows скачайте официальный установщик Tesseract и запустите его от имени администратора. После установки перезапустите backend. Система автоматически проверяет стандартный путь `C:\Program Files\Tesseract-OCR\tesseract.exe`.

## Production / HTTPS / локальная сеть

Development: HTTP на localhost допустим.  
Production: заверните backend за nginx/IIS с TLS. Задайте:

- `NS_SECRET_KEY`
- `NS_CORS_ORIGINS` (например `https://hr.company.local`)

Персональные данные остаются в корпоративной инфраструктуре (SQLite, файлы в `uploads/`, `templates/`, `generated_documents/`).

## Резервное копирование

Раздел «Настройки» → «Создать backup» собирает zip: БД + документы + шаблоны + uploads. Автоматический backup — через планировщик ОС на `POST /api/backups`.
