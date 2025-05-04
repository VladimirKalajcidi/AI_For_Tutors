from aiogram.fsm.state import StatesGroup, State

class StudentStates(StatesGroup):
    # — Добавление нового ученика
    enter_subject      = State()
    enter_direction    = State()
    enter_name         = State()
    enter_surname      = State()
    enter_class        = State()
    enter_phone        = State()
    enter_parent_phone = State()
    enter_profile      = State()
    enter_goal         = State()
    enter_level        = State()

    # — Настройка регулярного расписания
    set_schedule_time  = State()
    enter_day_time     = State()

    # — Загрузка любого файла по ученику
    waiting_for_file   = State()

    # — Редактирование полей ученика и шаблона расписания
    editing_field      = State()
    editing_days       = State()

    # — Механизм подтверждения/открытой обратной связи по сгенерированным файлам
    confirm_generation = State()
    report_feedback    = State()

    # — Проверка решения учеником: сначала текст решения, потом эталон
    awaiting_solution  = State()
    awaiting_expected  = State()
    await_generation_feedback = State()
    # — Свободный чат с GPT по этому ученику
    chatting           = State()
    awaiting_solution_text     = State()   # ждем решение ученика
    awaiting_expected_solution = State()   # ждем эталон/критерии
    chatting_with_gpt          = State()   # в режиме диалога
        # Новый флоу для диагностического теста:
    awaiting_diagnostic_solution  = State()  # ждём загрузки решения диагностического теста
    awaiting_diagnostic_expected  = State()  # ждём эталон/ключ ответов