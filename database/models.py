from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, Time, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.orm import synonym


Base = declarative_base()


class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    surname = Column(String)
    name = Column(String)
    patronymic = Column(String)
    birth_date = Column(String)  # дата рождения хранится как текст (YYYY-MM-DD)
    phone = Column(String)
    email = Column(String)
    language = Column(String, default="ru")
    telegram_id = Column(Integer, unique=True)
    subjects = Column(String)
    occupation = Column(String)
    workplace = Column(String)
    subscription_expires = Column(String)  # дата окончания подписки (строка ISO-формата)
    link_schedule = Column(String)
    is_logged_in = Column(Boolean, default=True)
    yandex_token = Column(String, nullable=True)
    lessons_conducted = Column(Integer, default=0)
    tokens_limit = Column(Integer, default=0)

    # Отношения
    students = relationship("Student", back_populates="teacher", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")

    # Дополнительные поля тарифа
    model = Column(String)                   # выбранная GPT-модель тарифа
    students_count = Column(Integer, default=0)  # макс. число учеников по тарифу
    tokens_limit = Column(Integer, default=0)    # лимит токенов (например, на генерацию)

class Student(Base):
    __tablename__ = "students"

    students_id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    class_ = Column("class", String)
    subject = Column(String)        # новый
    direction = Column(String) 
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"))
    phone = Column(String)
    parent_phone = Column(String)
    other_inf = Column(Text)
    report_student = Column(Text)
    text_report        = synonym("report_student")
    link_schedule = Column(String)
    schedule_days = Column(Text, default="[]")
    teacher = relationship("Teacher", back_populates="students")
    lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan")
    prompt_tokens_total = Column(Integer, default=0)
    completion_tokens_total = Column(Integer, default=0)
    lessons_completed = Column(Integer, default=0)

    # Учёт генераций GPT
    generation_month = Column(String, default="")   # месяц учета генераций (формат YYYY-MM)
    monthly_gen_count = Column(Integer, default=0)  # количество генераций в текущем месяце

class Lesson(Base):
    __tablename__ = "lessons"

    lesson_id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"))
    students_id = Column(Integer, ForeignKey("students.students_id"))
    data_of_lesson = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    passed = Column(Boolean, default=False)
    is_regular = Column(Boolean, default=False)
    regular_interval = Column(String, default="")  # например, "weekly"

    teacher = relationship("Teacher", back_populates="lessons")
    student = relationship("Student", back_populates="lessons")
