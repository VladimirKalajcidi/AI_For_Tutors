from aiogram.fsm.state import State, StatesGroup

class ScheduleStates(StatesGroup):
    choose_student = State()
    enter_datetime = State()
    enter_endtime = State()  # Добавить эту строку
