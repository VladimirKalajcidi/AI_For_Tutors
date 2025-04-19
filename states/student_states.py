from aiogram.fsm.state import State, StatesGroup

class StudentStates(StatesGroup):
    enter_name = State()
    enter_surname = State()
    enter_class = State()
    enter_subject = State()
    enter_phone = State()
    enter_parent_phone = State()
    enter_profile = State()
    waiting_for_file = State()
    editing_field = State() 
