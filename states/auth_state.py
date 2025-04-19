from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.state import StatesGroup, State


class AuthStates(StatesGroup):
    register_login = State()
    register_password = State()
    login_username = State()
    login_password = State()


class TeacherProfileStates(StatesGroup):
    surname = State()
    name = State()
    patronymic = State()
    birth_date = State()
    phone = State()
    email = State()
    subjects = State()
    occupation = State()
    workplace = State()

class TeacherStates(StatesGroup):
    editing_field = State()
