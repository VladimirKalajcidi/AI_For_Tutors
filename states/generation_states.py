from aiogram.fsm.state import State, StatesGroup

class GenerationStates(StatesGroup):
    confirm_generation = State()
