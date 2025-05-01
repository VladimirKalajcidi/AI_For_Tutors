from aiogram.fsm.state import StatesGroup, State

class StudentStates(StatesGroup):
    enter_name = State()
    enter_surname = State()
    enter_class = State()
    enter_subject = State()
    enter_direction = State()  # ✅ добавлено
    enter_phone = State()
    enter_parent_phone = State()
    enter_profile = State()
    enter_goal = State()
    enter_level = State()
    set_schedule_time = State()
    enter_day_time = State()
    waiting_for_file = State()
    editing_field = State()
    editing_days = State()

