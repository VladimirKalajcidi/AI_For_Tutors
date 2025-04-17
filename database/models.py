from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Teacher(Base):
    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    surname = Column(String)
    name = Column(String)
    patronymic = Column(String)
    birth_date = Column(String)  # Храним как TEXT для совместимости с SQLite
    phone = Column(String)
    email = Column(String)
    language = Column(String, default="ru")      # "ru" or "en"
    telegram_id = Column(Integer, unique=True)
    subjects = Column(String)  # Можно сделать отдельной таблицей, если потребуется
    occupation = Column(String)
    workplace = Column(String)
    subscription_expires = Column(String)  # Можно привести к Date, если планируешь сравнения
    link_schedule = Column(String)
    is_logged_in = Column(Boolean, default=True)
    

    students = relationship("Student", back_populates="teacher", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    students_id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    class_ = Column("class", String)  # "class" — зарезервированное слово, используем псевдоним
    subject = Column(String)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"))
    phone = Column(String)
    parent_phone = Column(String)
    other_inf = Column(Text)
    report_student = Column(Text)
    link_schedule = Column(String)

    teacher = relationship("Teacher", back_populates="students")
    lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    lesson_id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"))
    students_id = Column(Integer, ForeignKey("students.students_id"))
    data_of_lesson = Column(String)  # Можно DateTime, если будешь работать с датами
    passed = Column(Boolean)  # 0/1, но мапим в Python булево
    link_report = Column(String)
    link_HW = Column(String)
    link_HW_verified = Column(String)
    link_test = Column(String)
    link_test_verified = Column(String)
    link_plan = Column(String)

    teacher = relationship("Teacher", back_populates="lessons")
    student = relationship("Student", back_populates="lessons")
