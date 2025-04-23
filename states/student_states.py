from aiogram.fsm.state import StatesGroup, State

class StudentStates(StatesGroup):
    enter_name = State()
    enter_surname = State()
    enter_class = State()
    enter_subject = State()
    enter_phone = State()
    enter_parent_phone = State()
    enter_profile = State()
    set_schedule_time = State()  # новое состояние для ввода времени занятий
    enter_day_time = State()  # новое состояние ввода времени для дня


    # 🆕 добавь это:
    enter_goal = State()
    enter_level = State()

    waiting_for_file = State()
    editing_field = State()
    editing_days = State()

