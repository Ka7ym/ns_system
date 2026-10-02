from database import Base, SessionLocal, engine
from models import EMPLOYEE_STATUS_ACTIVE, Employee


def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Employee).count() == 0:
        employees = [
            {
                "full_name": "Иванов Иван Иванович",
                "iin": "010203456789",
                "birth_date": 1980,
                "position": "Инженер",
                "salary": 450000,
                "department": "Производственный отдел",
                "start_date": "2023-01-10",
                "status": EMPLOYEE_STATUS_ACTIVE,
            },
            {
                "full_name": "Петров Петр Петрович",
                "iin": "020304567890",
                "birth_date": 1982,
                "position": "Бухгалтер",
                "salary": 380000,
                "department": "Финансовый отдел",
                "start_date": "2022-05-15",
                "status": EMPLOYEE_STATUS_ACTIVE,
            },
            {
                "full_name": "Серикова Айгуль Маратовна",
                "iin": "030405678901",
                "birth_date": 1990,
                "position": "HR-менеджер",
                "salary": 420000,
                "department": "Отдел кадров",
                "start_date": "2021-11-01",
                "status": EMPLOYEE_STATUS_ACTIVE,
            },
            {
                "full_name": "Касымов Арман Бекович",
                "iin": "040506789012",
                "birth_date": 1985,
                "position": "Программист",
                "salary": 600000,
                "department": "IT отдел",
                "start_date": "2020-03-20",
                "status": EMPLOYEE_STATUS_ACTIVE,
            },
            {
                "full_name": "Нурланова Дана Ерланкызы",
                "iin": "050607890123",
                "birth_date": 1992,
                "position": "Юрист",
                "salary": 480000,
                "department": "Юридический отдел",
                "start_date": "2023-08-01",
                "status": EMPLOYEE_STATUS_ACTIVE,
            },
        ]

        for emp_data in employees:
            db.add(Employee(**emp_data))

        db.commit()
    db.close()


if __name__ == "__main__":
    seed_db()
