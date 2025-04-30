from aiogram.fsm.state import State, StatesGroup

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
    # subjects = State()    # не используем в начальной анкете
    # occupation = State()  # не используем в начальной анкете
    # workplace = State()   # не используем в начальной анкете

class TeacherStates(StatesGroup):
    editing_field = State()
