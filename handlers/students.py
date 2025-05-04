import os
import json
from datetime import datetime
from io import BytesIO

from sqlalchemy import select

import database.crud as crud
from database.db import async_session
from database.models import Student

from aiogram import Router, types, F, Bot
from aiogram.filters import Text, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from keyboards.main_menu import main_menu_kb
from keyboards.students import approve_kb
from keyboards.students import (
    students_list_keyboard,
    student_actions_keyboard,
    edit_student_keyboard,
    yandex_materials_keyboard,
    subject_keyboard,
    direction_keyboard,
    confirm_generation_keyboard,
)

from states.student_states import StudentStates

import services.storage_service as storage_service
from services.storage_service import generate_tex_pdf, upload_bytes_to_yandex

from services.gpt_service import (
    generate_diagnostic_test,
    generate_diagnostic_answer_key,
    check_solution,
    generate_study_plan,
    generate_assignment,
    generate_homework,
    generate_classwork,
    generate_learning_materials,
)

from services.report_service import append_to_text_report
from reportlab.pdfgen import canvas


router = Router()

@router.message(F.text == "➕ Добавить ученика")
@router.message(Command("add_student"))
async def add_student_start(message: types.Message, state: FSMContext):
    await message.answer("📚 Выберите предмет ученика:", reply_markup=subject_keyboard())
    await state.set_state(StudentStates.enter_subject)

@router.message(StudentStates.enter_subject)
async def process_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await message.answer("Теперь выберите направление обучения:", reply_markup=direction_keyboard())
    await state.set_state(StudentStates.enter_direction)

@router.message(StudentStates.enter_direction)
async def process_direction(message: Message, state: FSMContext):
    await state.update_data(direction=message.text.strip())
    await message.answer("Введите имя ученика:")
    await state.set_state(StudentStates.enter_name)

@router.message(StudentStates.enter_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer("Введите фамилию ученика:")
    await state.set_state(StudentStates.enter_surname)

@router.message(StudentStates.enter_surname)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    await message.answer("Введите класс ученика:")
    await state.set_state(StudentStates.enter_class)

@router.message(StudentStates.enter_class)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text.strip())
    await message.answer("Введите телефон ученика:")
    await state.set_state(StudentStates.enter_phone)

@router.message(StudentStates.enter_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("Введите телефон родителя ученика:")
    await state.set_state(StudentStates.enter_parent_phone)

@router.message(StudentStates.enter_parent_phone)
async def process_parent_phone(message: Message, state: FSMContext):
    await state.update_data(parent_phone=message.text.strip())
    await message.answer("Введите дополнительную информацию об ученике (например, особенности) или '-' если нет:")
    await state.set_state(StudentStates.enter_profile)

@router.message(StudentStates.enter_profile)
async def process_profile(message: Message, state: FSMContext):
    await state.update_data(profile=message.text.strip())
    await message.answer("Введите цель обучения ученика:")
    await state.set_state(StudentStates.enter_goal)

@router.message(StudentStates.enter_goal)
async def process_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text.strip())
    await message.answer("Введите уровень знаний ученика:")
    await state.set_state(StudentStates.enter_level)

    
import os
import re
import json
from io import BytesIO

from aiogram import Router, types
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

# ReportLab для fallback-PDF с кириллицей
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database.db import async_session
import database.crud as crud
from keyboards.main_menu import main_menu_kb
from keyboards.students import students_list_keyboard
from states.student_states import StudentStates

from services.gpt_service import generate_diagnostic_test, generate_diagnostic_answer_key
from services.storage_service import generate_tex_pdf, upload_bytes_to_yandex


# ─── Регистрация шрифта один раз ─────────────────────────────
_pdf_font_registered = False
def _register_cyrillic_font():
    global _pdf_font_registered
    if not _pdf_font_registered:
        # Убедитесь, что этот путь существует на вашем сервере
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        _pdf_font_registered = True

# ─── Утилита: fallback-PDF с поддержкой кириллицы ──────────────
def create_plain_text_pdf(text: str, filename: str) -> str:
    _register_cyrillic_font()
    output_dir = os.path.join("storage", "pdfs", "fallback")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{filename}.pdf")
    c = canvas.Canvas(path, pagesize=(595, 842))  # A4
    c.setFont('DejaVuSans', 12)
    y = 820
    for line in text.splitlines():
        c.drawString(40, y, line)
        y -= 16
        if y < 40:
            c.showPage()
            c.setFont('DejaVuSans', 12)
            y = 820
    c.save()
    return path

# ─── Основная функция ─────────────────────────────────────────
@router.message(StudentStates.enter_level)
async def process_level(message: Message, state: FSMContext, teacher):
    # 1) Создаём ученика
    data = await state.get_data()
    other_info = json.dumps({
        "profile": data.get("profile"),
        "goal":    data.get("goal"),
        "level":   message.text.strip()
    })
    async with async_session() as session:
        new_student = await crud.create_student(
            session=session,
            teacher_id=teacher.teacher_id,
            name=data.get("first_name"),
            surname=data.get("last_name"),
            class_=data.get("grade"),
            subject=data.get("subject"),
            direction=data.get("direction"),
            phone=data.get("phone"),
            parent_phone=data.get("parent_phone"),
            other_inf=other_info
        )
    await state.clear()

    # 2) Предварительное сообщение
    await message.answer(
        f"✅ Ученик {new_student.name} {new_student.surname} добавлен!\n"
        "Генерируем диагностический тест и ключ ответов, подождите…",
        reply_markup=main_menu_kb(teacher.language)
    )

    # 3) Получаем TeX от GPT
    diag_tex = await generate_diagnostic_test(
        new_student, model=teacher.model, language=teacher.language or "ru"
    )
    key_tex = await generate_diagnostic_answer_key(
        new_student, test_tex=diag_tex, model=teacher.model, language=teacher.language or "ru"
    )

    base = f"Diagnostic_{new_student.surname}_{new_student.name}"

    # 4) Компилируем TeX → PDF, или fallback
    try:
        diag_pdf = generate_tex_pdf(diag_tex, f"{base}_test")
    except RuntimeError:
        diag_pdf = create_plain_text_pdf(diag_tex, f"{base}_test_fallback")

    try:
        key_pdf = generate_tex_pdf(key_tex, f"{base}_key")
    except RuntimeError:
        key_pdf = create_plain_text_pdf(key_tex, f"{base}_key_fallback")

    # 5) Отправляем PDF
    await message.answer_document(FSInputFile(diag_pdf), caption="📊 Диагностический тест")
    await message.answer_document(FSInputFile(key_pdf),  caption="🔑 Ключ ответов к тесту")

    # 6) Загружаем на Яндекс.Диск (если нужно)
    if teacher.yandex_token:
        for category, path in [("Диагностика", diag_pdf), ("Диагностика_Ответы", key_pdf)]:
            buf = BytesIO(open(path, "rb").read())
            buf.seek(0)
            await upload_bytes_to_yandex(
                file_obj=buf,
                teacher=teacher,
                student=new_student,
                category=category,
                filename_base=os.path.splitext(os.path.basename(path))[0]
            )

    # 7) Сохраняем TeX в отчёт и показываем список учеников
    await crud.append_to_report(
        new_student.students_id,
        section="Диагностический тест",
        content=diag_tex
    )
    students = await crud.list_students(teacher)
    await message.answer(
        "📋 Обновлённый список учеников:",
        reply_markup=students_list_keyboard(students)
    )

    # 8) Предлагаем загрузить решения
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📝 Загрузить решение диагностического теста",
            callback_data=f"diagnostic_check:{new_student.students_id}"
        )
    ]])
    await message.answer(
        "Когда ученик выполнит тест, загрузите его решения для автоматической проверки:",
        reply_markup=kb
    )




@router.message(Text(text=["👨‍🎓 Ученики", "👨‍🎓 Students"]))
async def menu_students(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    # Проверка подписки
    from datetime import datetime
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        await message.answer("🔒 Подписка не активна. Продлите подписку, чтобы работать с учениками.")
        return
    students = await crud.list_students(teacher)
    if not students:
        await message.answer("❌ У вас пока нет учеников. Используйте /add_student, чтобы добавить ученика.")
    else:
        await message.answer("👨‍🎓 Ваши ученики:", reply_markup=students_list_keyboard(students))




@router.message(Command("add_student"))
async def cmd_add_student(message: Message, state: FSMContext):
    await add_student_start(message, state)

@router.callback_query(Text("add_student"))
async def callback_add_student(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await add_student_start(callback.message, state)


@router.callback_query(Text(startswith="student:"))
async def callback_view_student(callback: CallbackQuery, teacher, **data):
    # Получаем ID и сам объект ученика
    parts = callback.data.split(":")
    student_id = int(parts[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("❌ Ученик не найден.", show_alert=True)

    # Разбираем доп. информацию из JSON
    try:
        extra = json.loads(student.other_inf or "{}")
        goal = extra.get("goal", "—")
        level = extra.get("level", "—")
    except Exception:
        goal = level = "—"

    # Текст отчёта, который мы накапливаем в student.report_student
    report_text = student.report_student.strip() if student.report_student else "—"

    # Ограничиваем длину текста отчёта
    MAX_LENGTH = 3000
    trimmed = False
    if len(report_text) > MAX_LENGTH:
        report_text = report_text[:MAX_LENGTH] + "…"
        trimmed = True

    text = (
        f"👤 {student.name} {student.surname or ''}\n"
        f"🎯 Цель: {goal}\n"
        f"📈 Отчёт:\n{report_text}"
    )
    if trimmed:
        text += "\n\n⚠️ Полный отчёт обрезан из-за ограничения Telegram."

    await callback.message.edit_text(
        text,
        reply_markup=student_actions_keyboard(student.students_id),
        parse_mode=None
    )




@router.callback_query(Text(startswith="back_students"))
async def back_to_students(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    await callback.answer()
    students = await crud.list_students(teacher)
    if not students:
        await callback.message.edit_text("No students yet.")
    else:
        await callback.message.edit_text("Your students:", reply_markup=students_list_keyboard(students))

@router.callback_query(Text("check_solution"))
async def callback_start_check(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🖊️ Введите решение ученика для проверки:")
    await state.set_state(StudentStates.awaiting_solution)

@router.message(StateFilter(StudentStates.awaiting_solution_text))
async def process_solution_text(
    message: Message,
    state: FSMContext,
    teacher  # <- вот сюда Aiogram подставит teacher из middleware
):
    # 1) достаём из state, какой студент в контексте
    data = await state.get_data()
    student_id = data.get("student_id")
    if not student_id:
        await message.answer("❌ Не удалось найти студента в контексте.")
        await state.clear()
        return

    # 2) достаём студента из БД
    student = await crud.get_student(teacher, student_id)
    if not student:
        await message.answer("❌ Ученик не найден или не ваш.")
        await state.clear()
        return

    # 3) получаем решение ученика
    solution_text = message.text

    # 4) сохраняем решение в state и переводим FSM в ожидание эталона
    await state.update_data(solution_text=solution_text)
    await state.set_state(StudentStates.awaiting_expected_solution)

    await message.answer("📋 Спасибо! Теперь пришлите эталонный ответ или критерии оценки.")


@router.message(StateFilter(StudentStates.awaiting_expected_solution))
async def process_expected_solution(
    message: Message,
    state: FSMContext,
    teacher
):
    data = await state.get_data()
    student_id      = data.get("student_id")
    solution_text   = data.get("solution_text")
    expected_answer = message.text

    student = await crud.get_student(teacher, student_id)

    # 5) Передаём всё в GPT
    result = await check_solution(
        student=student,
        model=teacher.model,
        solution=solution_text,
        expected=expected_answer
    )

    await message.answer(f"🔍 Проверка:\n{result}")

    # 6) сбрасываем state (или возвращаем в главное меню)
    await state.clear()
    students = await crud.list_students(teacher)
    await message.answer("👨‍🎓 Ваши ученики:", reply_markup=students_list_keyboard(students))



@router.callback_query(Text(startswith="upload:"))
async def callback_upload_file(callback: CallbackQuery, state: FSMContext, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    if not teacher.yandex_token:
        await callback.answer()
        await callback.message.answer("⚠️ Яндекс.Диск не подключен. Подключите его в Настройках.")
        return
    await callback.answer()
    await state.set_state(StudentStates.waiting_for_file)
    await state.update_data(students_id=students_id)
    await callback.message.edit_text("📎 Отправьте файл (документ) для загрузки для этого ученика.")



@router.message(StudentStates.waiting_for_file)
async def process_file_upload(message: Message, state: FSMContext, bot: Bot, **data):
    teacher = data.get("teacher")
    if not message.document:
        await message.answer("⚠️ Пожалуйста, отправьте корректный файл-документ.")
        return
    state_data = await state.get_data()
    students_id = state_data.get("students_id")
    file_name = message.document.file_name or "file"
    file = await bot.get_file(message.document.file_id)
    buffer = BytesIO()
    await bot.download_file(file.file_path, buffer)
    buffer.seek(0)

    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.students_id == students_id))
        student = result.scalar_one_or_none()
    if not student:
        await message.answer("❌ Ученик не найден.")
        await state.clear()
        return
    success = await storage_service.upload_bytes_to_yandex(
        file_obj=buffer,
        teacher=teacher,
        student=student,
        category="Материалы",
        filename_base=file_name.rsplit(".", 1)[0]
    )
    if success:
        await message.answer(f"✅ Файл '{file_name}' успешно загружен в Яндекс.Диск (категория: Материалы).")
    else:
        await message.answer("❌ Ошибка при загрузке файла на Я.Диск. Проверьте токен в настройках.")
    await state.clear()






@router.callback_query(Text(startswith="edit_student:"))
async def callback_edit_student(callback: CallbackQuery):
    students_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text(
        "✏️ Выберите, что вы хотите изменить:",
        reply_markup=edit_student_keyboard(students_id)
    )

@router.callback_query(Text(startswith="edit_field:"))
async def callback_edit_field(callback: CallbackQuery, state: FSMContext):
    _, students_id, field = callback.data.split(":")
    await state.set_state(StudentStates.editing_field)  # <-- добавлено
    await state.update_data(students_id=int(students_id), field=field)
    await callback.answer()
    await callback.message.edit_text(f"✏️ Введите новое значение для поля: *{field}*", parse_mode="Markdown")


@router.message(StateFilter(StudentStates.editing_field))
async def process_student_field_edit(message: Message, state: FSMContext, **data):

    state_data = await state.get_data()
    students_id = state_data.get("students_id")
    field = state_data.get("field")
    teacher = data.get("teacher")

    if not students_id or not field:
        return  # не режим редактирования

    new_value = message.text.strip()
    await crud.update_student_field(teacher, students_id, field, new_value)
    await state.clear()
    await message.answer(f"✅ Поле *{field}* обновлено!", parse_mode="Markdown")

    student = await crud.get_student(teacher, students_id)
    other_inf = student.other_inf or "{}"
    try:
        info = json.loads(other_inf)
    except json.JSONDecodeError:
        info_text = other_inf    # если вдруг не JSON, покажем как есть
    else:
        parts = []
        if info.get("goal"):
            parts.append(f"🎯 Цель: {info['goal']}")
        if info.get("level"):
            parts.append(f"📈 Уровень: {info['level']}")
        if info.get("profile"):
            parts.append(f"📝 Профиль: {info['profile']}")
        info_text = "\n".join(parts) or "—"

    await message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n"
        f"ℹ️ Доп. информация:\n{info_text}",
        reply_markup=student_actions_keyboard(student.students_id)
    )


@router.callback_query(Text(startswith="delete_student:"))
async def callback_delete_student(callback: CallbackQuery):
    students_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text(
        "❗️Вы уверены, что хотите удалить ученика?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{students_id}")],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"student:{students_id}")]
        ])
    )

@router.callback_query(Text(startswith="confirm_delete:"))
async def callback_confirm_delete(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    await crud.delete_student(teacher, students_id)
    await callback.answer("🗑 Ученик удалён")

    students = await crud.list_students(teacher)
    if students:
        await callback.message.edit_text("📋 Список учеников обновлён:", reply_markup=students_list_keyboard(students))
    else:
        await callback.message.edit_text("У вас больше нет учеников.")


@router.callback_query(Text(startswith="yadisk:"))
async def callback_yadisk_menu(callback: CallbackQuery):
    students_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "📤 Выберите тип материала для загрузки:",
        reply_markup=yandex_materials_keyboard(students_id)
    )


@router.callback_query(Text(startswith="upload_material:"))
async def callback_select_material_type(callback: CallbackQuery, state: FSMContext):
    _, students_id, material_type = callback.data.split(":")
    await state.set_state(StudentStates.waiting_for_file)
    await state.update_data(students_id=int(students_id), material_type=material_type)
    await callback.message.edit_text("📎 Отправьте файл для загрузки на Яндекс.Диск.")

@router.message(StudentStates.waiting_for_file)
async def handle_file_upload(message: Message, state: FSMContext, teacher):
    data = await state.get_data()
    students_id = data.get("students_id")
    material_type = data.get("material_type")
    
    if not teacher.yandex_token:
        await message.answer("❌ Сначала подключите Яндекс.Диск в настройках.")
        return
    
    if not message.document:
        await message.answer("⚠️ Пришлите документ!")
        return

    from aiogram import Bot
    import io
    from database.db import AsyncSessionLocal
    from database.models import Student

    # Получаем файл
    bot: Bot = message.bot
    file = await bot.get_file(message.document.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, destination=buffer)
    buffer.seek(0)

    from sqlalchemy import select


    # Получаем объект ученика
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Student).where(Student.students_id == students_id))
        student = result.scalar_one_or_none()

    if not student:
        await message.answer("❌ Ученик не найден.")
        return

    # Названия папок по типу материала
    folder_map = {
        "homework": "Домашние работы",
        "assignment": "Классные работы",
        "theory": "Теория",
        "plan": "Планы",
        "report": "Отчёты",
        "checked": "Проверено"
    }
    category = folder_map.get(material_type, "Материалы")

    # Загружаем файл
    filename_base = message.document.file_name.rsplit(".", 1)[0]
    success = await storage_service.upload_bytes_to_yandex(
        file_obj=buffer,
        teacher=teacher,
        student=student,
        category=category,
        filename_base=filename_base
    )

    await state.clear()

    if success:
        await message.answer(f"✅ Файл загружен в папку `{category}` на Яндекс.Диске.")
    else:
        await message.answer("❌ Ошибка загрузки файла.")




@router.callback_query(Text(startswith="edit_days:"))
async def callback_edit_days(callback: CallbackQuery, state: FSMContext):
    students_id = int(callback.data.split(":")[1])
    await state.set_state(StudentStates.editing_days)
    await state.update_data(students_id=students_id, selected_days=[])

    buttons = [
        [types.InlineKeyboardButton(text=day, callback_data=f"toggle_day:{day}") for day in ["Mon", "Tue", "Wed"]],
        [types.InlineKeyboardButton(text=day, callback_data=f"toggle_day:{day}") for day in ["Thu", "Fri", "Sat"]],
        [types.InlineKeyboardButton(text="✅ Сохранить", callback_data="save_days"),
         types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"student:{students_id}")]
    ]
    await callback.message.edit_text(
        "Выберите дни занятий (нажмите несколько раз для выбора/отмены):",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(Text(startswith="toggle_day:"))
async def toggle_day_selection(callback: CallbackQuery, state: FSMContext):
    day = callback.data.split(":")[1]
    await state.update_data(current_day=day)
    await callback.message.answer(f"🕓 Укажите время занятий в формате HH:MM-HH:MM для {day}:")
    await state.set_state(StudentStates.enter_day_time)


@router.callback_query(Text("save_days"))
async def save_schedule_days(callback: CallbackQuery, state: FSMContext, **data):
    from datetime import time
    teacher = data.get("teacher")
    state_data = await state.get_data()
    students_id = state_data.get("students_id")
    schedule = state_data.get("schedule_data", {})

    for day, time_range in schedule.items():
        start_h, start_m = map(int, time_range["start"].split(":"))
        end_h, end_m = map(int, time_range["end"].split(":"))
        await crud.set_student_schedule_template(
            teacher=teacher,
            student_id=students_id,
            days=[day],
            start_time=time(start_h, start_m),
            end_time=time(end_h, end_m)
        )

    await state.clear()
    await callback.message.answer("✅ Дни и время занятий обновлены!", reply_markup=student_actions_keyboard(students_id))



@router.message(StudentStates.set_schedule_time)
async def process_schedule_time(message: Message, state: FSMContext, **data):
    import json
    from database import crud
    from datetime import time

    teacher = data.get("teacher")
    input_time = message.text.strip()
    try:
        start_str, end_str = input_time.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        start_time = time(start_h, start_m)
        end_time = time(end_h, end_m)
    except Exception:
        await message.answer("❌ Неверный формат времени. Укажите как HH:MM-HH:MM (например, 16:00-17:30).")
        return

    state_data = await state.get_data()
    students_id = state_data.get("students_id")
    days = state_data.get("selected_days", [])

    # 🗓️ Сохраняем расписание в БД через crud
    await crud.set_student_schedule_template(
        teacher=teacher,
        student_id=students_id,
        days=days,
        start_time=start_time,
        end_time=end_time
    )

    await message.answer("✅ Регулярное расписание обновлено!", reply_markup=student_actions_keyboard(students_id))
    await state.clear()


@router.message(StudentStates.enter_day_time)
async def process_day_time(message: Message, state: FSMContext):
    input_time = message.text.strip()
    data = await state.get_data()
    day = data.get("current_day")
    schedule = data.get("schedule_data", {})

    try:
        start_str, end_str = input_time.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        schedule[day] = {"start": f"{start_h:02}:{start_m:02}", "end": f"{end_h:02}:{end_m:02}"}
        await state.update_data(schedule_data=schedule)
    except Exception:
        await message.answer("❌ Неверный формат. Пример: 16:00-17:30")
        return

    await message.answer("✅ Время сохранено. Выберите ещё день или нажмите «Сохранить».")
    await state.set_state(StudentStates.editing_days)


from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from services.gpt_service import generate_report
from services.storage_service import generate_tex_pdf, upload_bytes_to_yandex
from database.db import async_session
from database.models import Student
from states.student_states import StudentStates

# 1) Начало генерации — показываем PDF и спрашиваем «Всё ли хорошо?»
@router.callback_query(Text(startswith="reports:"))
async def callback_generate_report_start(callback: CallbackQuery, teacher, state: FSMContext):
    await callback.answer()
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # проверка подписки/лимита — оставляем как было
    from datetime import datetime
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires)
    except:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)
    if (student.monthly_gen_count or 0) >= 50:
        return await callback.answer("⚠️ Лимит генераций исчерпан.", show_alert=True)

    await callback.message.edit_text("📑 Генерация отчёта, пожалуйста ждите...")
    # сама генерация
    tex = await generate_report(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex",
    )
    pdf_path = generate_tex_pdf(tex, f"Report_{student.name}_{student.surname}")
    # сохраняем в state
    await state.update_data(student_id=student_id, tex=tex, pdf_path=pdf_path)
    # отправляем PDF
    await callback.message.answer_document(FSInputFile(pdf_path),
                                           caption=f"📑 Отчёт по {student.name}")
    # кнопки «Да/Нет»
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Сгенерировать отчёт", callback_data=f"reports_do:{student_id}")],
        [InlineKeyboardButton(text="✅ Всё хорошо",          callback_data=f"reports_confirm:{student_id}")],
        [InlineKeyboardButton(text="🔙 Назад",               callback_data=f"student:{student_id}")],
    ])
    await callback.message.answer("Всё ли хорошо в отчёте?", reply_markup=kb)
    await state.set_state(StudentStates.report_confirm)


# 2) Если «Да» — финализируем (загружаем на ЯДиск) и выходим из FSM
@router.callback_query(Text(startswith="reports_confirm:"))
async def callback_report_confirm(callback: CallbackQuery, teacher, state: FSMContext):
    await callback.answer("✅ Отчёт подтверждён. Загружаю на Я.Диск...")
    data = await state.get_data()
    pdf_path = data.get("pdf_path")
    student_id = data.get("student_id")
    # загружаем
    async with async_session() as session:
        student = await session.get(Student, student_id)
    if teacher.yandex_token and pdf_path and student:
        from io import BytesIO
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Отчёты",
            filename_base="Report"
        )
        await callback.message.answer("📂 Отчёт загружен на Я.Диск.")
    await state.clear()


# 3) Если «Исправить» — просим текст замечаний и переходим в состояние report_feedback
@router.callback_query(Text(startswith="reports_feedback:"))
async def callback_report_feedback_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    student_id = int(callback.data.split(":")[1])
    await state.update_data(student_id=student_id)
    await callback.message.answer("📝 Напишите, что нужно исправить в отчёте:")
    await state.set_state(StudentStates.report_feedback)


# 4) Обработка текста замечаний — регенерируем отчёт и снова спрашиваем подтверждение
@router.message(StateFilter(StudentStates.report_feedback))
async def process_report_feedback(message: Message, state: FSMContext, teacher):
    feedback = message.text.strip()
    data = await state.get_data()
    student_id = data.get("student_id")
    student = await crud.get_student(teacher, student_id)
    if not student:
        await message.answer("⚠️ Ученик не найден.")
        return await state.clear()

    await message.answer("🔄 Применяю ваши замечания и генерирую новый отчёт...")
    tex = await generate_report(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex",
        feedback=feedback
    )
    pdf_path = generate_tex_pdf(tex, f"Report_{student.name}_{student.surname}")
    # обновляем state
    await state.update_data(tex=tex, pdf_path=pdf_path)
    # отправляем новый PDF
    await message.answer_document(FSInputFile(pdf_path),
                                  caption="📑 Новый вариант отчёта")
    # снова кнопки «Да/Нет»
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Всё хорошо", callback_data=f"reports_confirm:{student_id}")],
        [InlineKeyboardButton("✏️ Ещё правки", callback_data=f"reports_feedback:{student_id}")]
    ])
    await message.answer("Всё ли теперь устраивает?", reply_markup=kb)
    await state.set_state(StudentStates.report_confirm)


    



# Генерация учебного плана (study_plan) — добавлена логика подтверждения и сохранения .tex:
@router.callback_query(Text(startswith="genplan:"))
async def callback_generate_plan(callback: CallbackQuery, teacher, **data):
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # Проверка подписки
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)

    # Проверка лимита генераций
    current_count = student.monthly_gen_count or 0
    if current_count >= teacher.tokens_limit:
        return await callback.answer("⚠️ Лимит генераций для этого ученика исчерпан.", show_alert=True)

    await callback.answer()

    

    await callback.message.edit_text("✏️ Генерация учебного плана, пожалуйста ждите...")

    tex_code = await generate_study_plan(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex"
    )

    # Сохранение .tex
    tex_dir = os.path.join(BASE_DIR, "storage", "tex", "study_plan")
    os.makedirs(tex_dir, exist_ok=True)
    filename_base = f"study_plan_{student.name}_{student.surname or ''}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tex_path = os.path.join(tex_dir, f"{filename_base}_{timestamp}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_code)

    file_name = f"Plan_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex_code, file_name)
    await callback.message.answer_document(
        document=types.FSInputFile(pdf_path),
        caption=f"📋 Учебный план для {student.name}"
    )

    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer, teacher=teacher,
            student=student,
            category="План",
            filename_base="Plan"
        )

    await append_to_text_report(
        teacher_id=teacher.teacher_id,
        student_id=student.students_id,
        section="План",
        content=tex_code
    )

    from keyboards.students import confirm_generation_keyboard
    kb = confirm_generation_keyboard(student_id, "study_plan")
    await callback.message.answer("🧐 Вам всё нравится в этом учебном плане?", reply_markup=kb)

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n",
        reply_markup=student_actions_keyboard(student.students_id)
    )
    # инкремент счётчика...


    # 9) Инкремент генераций и уведомления
    new_count = await crud.increment_generation_count(teacher, student.students_id)
    if new_count == 41:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* осталось 10 генераций в этом месяце.",
            parse_mode="Markdown"
        )
    elif new_count == 50:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* достигнут лимит генераций на месяц.",
            parse_mode="Markdown"
        )



@router.callback_query(Text(startswith="genassign:"))
async def callback_generate_assignment(callback: CallbackQuery, state: FSMContext, teacher, **data):
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # 1) Проверка подписки
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)

    # 2) Проверка лимита генераций
    current_count = student.monthly_gen_count or 0
    if current_count >= 50:
        return await callback.answer("⚠️ Лимит генераций для этого ученика исчерпан.", show_alert=True)

    await callback.answer()
    await callback.message.edit_text("✏️ Генерация задания, пожалуйста ждите...")

    # 3) Генерация TeX-кода задания
    tex_code = await generate_assignment(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex"
    )

    # 4) Компиляция TeX → PDF
    file_name = f"Assignment_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex_code, file_name)

    # 5) Отправка PDF в чат (или фоллбек на TeX)
    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📝 Задание для {student.name}"
        )
    except Exception:
        await callback.message.answer("🚨 Не удалось собрать PDF, вот TeX-код:\n" + tex_code)

    # 6) Сохранение на Яндекс.Диске
    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Классная_работа",
            filename_base="Assignment"
        )

    # 7) Добавляем запись в текстовый отчёт
    await append_to_text_report(
        teacher_id=teacher.teacher_id,
        student_id=student.students_id,
        section="Классная работа",
        content=tex_code
    )
    
    # 8) Спрашиваем у преподавателя, всё ли его устраивает
# 8) Спрашиваем у преподавателя, всё ли его устраивает
    from keyboards.students import confirm_generation_keyboard

    kb = confirm_generation_keyboard(student_id, category="assignment")
    await callback.message.answer("🧐 Вам всё нравится в этом задании?", reply_markup=kb)


    # 9) Отправляем карточку ученика с кнопками
    try:
        extra = json.loads(student.other_inf or "{}")
        parts = []
        if extra.get("goal"):
            parts.append(f"🎯 Цель: {extra['goal']}")
        if extra.get("level"):
            parts.append(f"📈 Уровень: {extra['level']}")
        if extra.get("profile"):
            parts.append(f"📝 Профиль: {extra['profile']}")
        info_text = "\n".join(parts) or "—"
    except Exception:
        info_text = student.other_inf or "—"

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n"
        f"ℹ️ Доп. информация:\n{info_text}",
        reply_markup=student_actions_keyboard(student.students_id)
    )

    # 10) Инкремент счётчика и предупреждения
    new_count = await crud.increment_generation_count(teacher, student.students_id)
    if new_count == 41:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* осталось 10 генераций в этом месяце.",
            parse_mode="Markdown"
        )
    elif new_count == 50:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* достигнут лимит генераций на месяц.",
            parse_mode="Markdown"
        )



# --- handlers/students.py ---

from datetime import datetime
import os
# BASE_DIR — корневая папка проекта (один уровень вверх от текущего файла)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Пример: обработчик генерации домашнего задания с сохранением .tex и корректным confirm:
@router.callback_query(Text(startswith="genhomework:"))
async def callback_generate_homework(callback: CallbackQuery, teacher, **data):
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # Проверка подписки
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)

    # Проверка лимита генераций
    current_count = student.monthly_gen_count or 0
    if current_count >= teacher.tokens_limit:
        return await callback.answer("⚠️ Лимит генераций для этого ученика исчерпан.", show_alert=True)

    await callback.answer()


    await callback.message.edit_text("📑 Генерация домашнего задания, пожалуйста ждите...")

    # 1) Генерация TeX-кода домашки через GPT
    tex_code = await generate_homework(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex"
    )

    # --- Сохранение LaTeX-кода в локальное хранилище для фидбека ---
    tex_dir = os.path.join(BASE_DIR, "storage", "tex", "homework")
    os.makedirs(tex_dir, exist_ok=True)  # создавать директорию рекурсивно:contentReference[oaicite:5]{index=5}
    filename_base = f"homework_{student.name}_{student.surname or ''}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tex_path = os.path.join(tex_dir, f"{filename_base}_{timestamp}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_code)

    # 2) Компиляция TeX → PDF и отправка в чат
    file_name = f"Homework_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex_code, file_name)
    await callback.message.answer_document(
        document=types.FSInputFile(pdf_path),  # отправляем PDF-файл как InputFile:contentReference[oaicite:6]{index=6}
        caption=f"📑 Домашнее задание для {student.name}"
    )

    # 3) Загрузка на Яндекс.Диск (если есть токен)
    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer, teacher=teacher,
            student=student,
            category="Домашняя_работа",
            filename_base="Homework"
        )

    # 4) Добавление в текстовый отчёт на Яндекс.Диске
    await append_to_text_report(
        teacher_id=teacher.teacher_id,
        student_id=student.students_id,
        section="Домашняя работа",
        content=tex_code
    )

    # 5) Спрашиваем преподавателя, нужно ли исправить
    from keyboards.students import confirm_generation_keyboard
    kb = confirm_generation_keyboard(student_id, "homework")
    await callback.message.answer("🧐 Вам всё нравится в этом домашнем задании?", reply_markup=kb)

    # 6) Отправка карточки ученика и завершение
    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n",
        reply_markup=student_actions_keyboard(student.students_id)
    )
    # Инкремент счетчика генераций (остальное без изменений)


    # 8) Инкремент счётчика и оповещения
    new_count = await crud.increment_generation_count(teacher, student.students_id)
    if new_count == teacher.tokens_limit - 9:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* осталось 10 генераций в этом месяце.",
            parse_mode="Markdown"
        )
    elif new_count == teacher.tokens_limit:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* достигнут лимит генераций на месяц.",
            parse_mode="Markdown"
        )



# Аналогично для контрольной работы (classwork):
@router.callback_query(Text(startswith="genclasswork:"))
async def callback_generate_classwork(callback: CallbackQuery, teacher, **data):
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # Проверка подписки
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)

    # Проверка лимита генераций
    current_count = student.monthly_gen_count or 0
    if current_count >= teacher.tokens_limit:
        return await callback.answer("⚠️ Лимит генераций для этого ученика исчерпан.", show_alert=True)

    await callback.answer()


    await callback.message.edit_text("🧪 Генерация контрольной работы, пожалуйста ждите...")

    tex_code = await generate_classwork(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex"
    )

    tex_dir = os.path.join(BASE_DIR, "storage", "tex", "classwork")
    os.makedirs(tex_dir, exist_ok=True)
    filename_base = f"classwork_{student.name}_{student.surname or ''}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tex_path = os.path.join(tex_dir, f"{filename_base}_{timestamp}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_code)

    file_name = f"Classwork_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex_code, file_name)
    await callback.message.answer_document(
        document=types.FSInputFile(pdf_path),
        caption=f"🧪 Контрольная для {student.name}"
    )

    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer, teacher=teacher,
            student=student,
            category="Контрольная_работа",
            filename_base="Classwork"
        )

    await append_to_text_report(
        teacher_id=teacher.teacher_id,
        student_id=student.students_id,
        section="Контрольная работа",
        content=tex_code
    )

    from keyboards.students import confirm_generation_keyboard
    kb = confirm_generation_keyboard(student_id, "classwork")
    await callback.message.answer("🧐 Вам всё нравится в этой контрольной работе?", reply_markup=kb)

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n",
        reply_markup=student_actions_keyboard(student.students_id)
    )
    # инкремент счётчика...


    # 8) Инкремент счётчика и оповещения
    new_count = await crud.increment_generation_count(teacher, student.students_id)
    if new_count == teacher.tokens_limit - 9:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* осталось 10 генераций в этом месяце.",
            parse_mode="Markdown"
        )
    elif new_count == teacher.tokens_limit:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* достигнут лимит генераций на месяц.",
            parse_mode="Markdown"
        )



@router.callback_query(Text(startswith="genmaterials:"))
async def callback_generate_materials(callback: CallbackQuery, state: FSMContext, teacher, **data):
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.answer("⚠️ Ученик не найден.", show_alert=True)

    # 1) Проверка подписки
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < datetime.now():
        return await callback.answer("🔒 Подписка не активна.", show_alert=True)

    # 2) Проверка лимита генераций
    current_count = student.monthly_gen_count or 0
    if current_count >= teacher.tokens_limit:
        return await callback.answer("⚠️ Лимит генераций для этого ученика исчерпан.", show_alert=True)

    await callback.answer()
    await callback.message.edit_text("📚 Подбор обучающих материалов, пожалуйста ждите...")

    # 3) Генерация TeX-кода материалов
    tex_code = await generate_learning_materials(
        student,
        model=teacher.model,
        language=teacher.language or "ru",
        output_format="tex"
    )

    # 4) Компиляция TeX → PDF
    file_name = f"Materials_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex_code, file_name)

    # 5) Отправка PDF или фоллбек на TeX
    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📚 Обучающие материалы для {student.name}"
        )
    except Exception:
        await callback.message.answer("🚨 Не удалось собрать PDF, вот TeX-код:\n" + tex_code)

    # 6) Сохранение на Яндекс.Диске
    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Обучающие_материалы",
            filename_base="Materials"
        )

    # 7) Добавляем запись в текстовый отчёт
    await append_to_text_report(
        teacher_id=teacher.teacher_id,
        student_id=student.students_id,
        section="Обучающие материалы",
        content=tex_code
    )

    # 8) Спрашиваем у преподавателя, всё ли его устраивает
    from keyboards.students import confirm_generation_keyboard

    kb = confirm_generation_keyboard(student_id, category="assignment")
    await callback.message.answer("🧐 Вам всё нравится в этом задании?", reply_markup=kb)


    # 9) Отправляем карточку ученика с кнопками
    try:
        extra = json.loads(student.other_inf or "{}")
        parts = []
        if extra.get("goal"):
            parts.append(f"🎯 Цель: {extra['goal']}")
        if extra.get("level"):
            parts.append(f"📈 Уровень: {extra['level']}")
        if extra.get("profile"):
            parts.append(f"📝 Профиль: {extra['profile']}")
        info_text = "\n".join(parts) or "—"
    except Exception:
        info_text = student.other_inf or "—"

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Предмет: {student.subject or '—'}\n"
        f"ℹ️ Доп. информация:\n{info_text}",
        reply_markup=student_actions_keyboard(student.students_id)
    )

    # 10) Инкремент счётчика и оповещения
    new_count = await crud.increment_generation_count(teacher, student.students_id)
    if new_count == teacher.tokens_limit - 9:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* осталось 10 генераций в этом месяце.",
            parse_mode="Markdown"
        )
    elif new_count == teacher.tokens_limit:
        await callback.message.answer(
            f"⚠️ Для ученика *{student.name}* достигнут лимит генераций на месяц.",
            parse_mode="Markdown"
        )

@router.callback_query(Text(startswith="check_solution:"))
async def cb_check_solution(callback: CallbackQuery, state: FSMContext, teacher):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text("🔍 Отправьте решение ученика (текстом).")
    await state.update_data(student_id=student_id)
    await state.set_state(StudentStates.awaiting_solution)

@router.message(StateFilter(StudentStates.awaiting_solution))
async def process_solution(message: Message, state: FSMContext):
    await state.update_data(solution=message.text)
    await message.answer("✏️ Теперь отправьте правильный ответ или критерии оценки.")
    await state.set_state(StudentStates.awaiting_expected)

@router.message(StateFilter(StudentStates.awaiting_expected))
async def process_expected(message: Message, state: FSMContext, teacher):
    data = await state.get_data()
    student = await crud.get_student(teacher, data["student_id"])
    from services.gpt_service import ask_gpt
    prompt = (
        f"Проверь решение ученика:\n\n"
        f"Решение: {data['solution']}\n"
        f"Эталон: {message.text}\n"
        f"Дай подробный разбор ошибок и рекомендации."
    )
    result = await ask_gpt(prompt,
                           system_prompt="Ты — эксперт-педагог, оценивающий ответы учеников.",
                           model=teacher.model,
                           student_id=student.students_id)
    await message.answer(f"✅ Оценка:\n{result}")
    await state.clear()


@router.callback_query(Text(startswith="chat_gpt:"))
async def cb_chat_gpt(callback: CallbackQuery, state: FSMContext, teacher):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text("💬 Введите ваш вопрос от имени преподавателя:")
    await state.update_data(student_id=student_id)
    await state.set_state(StudentStates.chatting)

@router.message(StateFilter(StudentStates.chatting))
async def process_chat(message: Message, state: FSMContext, teacher):
    data = await state.get_data()
    student = await crud.get_student(teacher, data["student_id"])
    from services.gpt_service import chat_with_gpt
    response = await chat_with_gpt(
        student,
        model=teacher.model,
        user_message=message.text,
        language=teacher.language or "ru"
    )
    await message.answer(response)
    # Остаёмся в состоянии: если хочется выход по /cancel, можно ловить его отдельно


from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Text

# 1) Обработчик кнопки «Проверить решение»
@router.callback_query(Text(startswith="check_solution:"))
async def callback_check_solution(callback: CallbackQuery, state: FSMContext, teacher):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text(
        "🔍 Пожалуйста, пришлите решение ученика для проверки.",
        reply_markup=None
    )
    await state.set_state(StudentStates.awaiting_solution_text)
    await state.update_data(student_id=student_id)

# 2) Получили текст решения
@router.message(StateFilter(StudentStates.awaiting_solution_text))
async def process_solution_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(solution_text=message.text)
    await message.answer("✅ Спасибо! Теперь пришлите эталонный ответ или критерии оценки.")
    await state.set_state(StudentStates.awaiting_expected_solution)

# 3) Получили эталон, запускаем GPT-проверку
@router.message(StateFilter(StudentStates.awaiting_expected_solution))
async def process_expected_solution(message: Message, state: FSMContext, teacher):
    data = await state.get_data()
    student = await crud.get_student(teacher, data["student_id"])
    expected = message.text
    solution = data["solution_text"]
    from services.gpt_service import ask_gpt
    prompt = (
        f"Ученик дал такой ответ: {solution}\n"
        f"Правильный ответ/критерии: {expected}\n"
        "Оцени и прокомментируй."
    )
    review = await ask_gpt(prompt,
                           system_prompt="Ты эксперт по проверке работ.",
                           model=teacher.model,
                           student_id=student.students_id)
    await message.answer(f"📝 Проверка:\n{review}")
    await state.clear()

@router.callback_query(Text(startswith="chat_gpt:"))
async def callback_chat_gpt(callback: CallbackQuery, state: FSMContext, teacher):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text("💬 Вводите ваши вопросы по ученику.")
    await state.set_state(StudentStates.chatting_with_gpt)
    await state.update_data(student_id=student_id)

@router.message(StateFilter(StudentStates.chatting_with_gpt))
async def process_chat_gpt(message: Message, state: FSMContext, teacher):
    data = await state.get_data()
    student = await crud.get_student(teacher, data["student_id"])
    from services.gpt_service import chat_with_gpt
    reply = await chat_with_gpt(
        student,
        model=teacher.model,
        user_message=message.text,
        language="ru"
    )
    await message.answer(reply)
    # остаёмся в том же состоянии, чтобы продолжать диалог

from aiogram.filters import Text
from aiogram.types import CallbackQuery

@router.callback_query(Text(startswith="reports_confirm:"))
async def callback_reports_confirm(
    callback: CallbackQuery,
    teacher,  # берётся через middleware
    **data
):
    await callback.answer("Отлично, без изменений.", show_alert=True)

    student_id = int(callback.data.split(":", 1)[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        return await callback.message.edit_text("❌ Ученик не найден.")

    # Отобразим карточку ученика обратно
    from keyboards.students import student_actions_keyboard
    other_inf = student.other_inf or "{}"
    # (парсим goal/level как у вас было)
    text = (
        f"👤 {student.name} {student.surname}\n"
        f"📚 Предмет: {student.subject}\n"
        f"ℹ️ Доп. информация:\n"
        # ... ваш формат показа доп. инфо ...
    )
    await callback.message.edit_text(
        text,
        reply_markup=student_actions_keyboard(student.students_id)
    )


from aiogram.filters import Text
from aiogram.types import CallbackQuery

@router.callback_query(Text(startswith="confirm_yes:"))
async def on_confirm_yes(callback: CallbackQuery, **data):
    try:
        _, student_id_str, category = callback.data.split(":")
        student_id = int(student_id_str)
    except ValueError:
        return await callback.answer("⚠️ Ошибка в формате данных.", show_alert=True)

    await callback.answer("✅ Отлично! Задание принято.")
    await callback.message.edit_reply_markup()  # убираем кнопки

    # Можно добавить запись "Подтверждено преподавателем", если нужно


@router.callback_query(Text(startswith="confirm_no:"))
async def on_confirm_no(callback: CallbackQuery, state: FSMContext):
    _, student_id_str, category = callback.data.split(":", 2)
    student_id = int(student_id_str)

    await callback.answer()
    await state.update_data(student_id=student_id, category=category)
    await state.set_state(StudentStates.await_generation_feedback)
    await callback.message.answer("✏️ Напишите, что нужно исправить в последней генерации:")



@router.message(StateFilter(StudentStates.await_generation_feedback))
async def process_generation_feedback(
    message: Message,
    state: FSMContext,
    teacher  # передаётся через middleware
):
    from services.storage_service import generate_tex_pdf, upload_bytes_to_yandex
    from services.gpt_service import (
        generate_homework,
        generate_assignment,
        generate_classwork,
        generate_study_plan,
        generate_learning_materials,
    )
    from keyboards.students import confirm_generation_keyboard
    from database import crud
    from io import BytesIO
    from aiogram.types import FSInputFile

    # 1. Получаем данные из state
    data = await state.get_data()
    student_id = data.get("student_id")
    category = data.get("category", "homework")  # по умолчанию — homework
    feedback = message.text.strip()

    # 2. Получаем студента
    student = await crud.get_student(teacher, student_id)
    if not student:
        await message.answer("❌ Ученик не найден.")
        return await state.clear()

    # 3. Выбираем нужную функцию генерации
    generator_map = {
        "homework": generate_homework,
        "assignment": generate_assignment,
        "classwork": generate_classwork,
        "study_plan": generate_study_plan,
        "materials": generate_learning_materials,
    }
    generator = generator_map.get(category)
    if not generator:
        await message.answer("❌ Неизвестный тип генерации.")
        return await state.clear()

    # 4. Генерация нового документа с учётом фидбека
    await message.answer("🔄 Генерирую новый документ с учётом ваших правок...")
    tex = await generator(
        student,
        model=teacher.model,
        language=teacher.language,
        output_format="tex",
        feedback=feedback
    )

    # 5. Компиляция в PDF
    base_name_map = {
        "homework": "Homework",
        "assignment": "Assignment",
        "classwork": "Classwork",
        "study_plan": "Plan",
        "materials": "Materials",
    }
    base_name = base_name_map.get(category, "Generated")
    file_name = f"{base_name}_{student.name}_{student.surname or ''}"
    pdf_path = generate_tex_pdf(tex, file_name)

    # 6. Отправка PDF преподавателю
    await message.answer_document(FSInputFile(pdf_path), caption=f"📝 Обновлённое {category.replace('_', ' ')}")

    # 7. Загрузка в Яндекс.Диск (если настроено)
    if teacher.yandex_token:
        buffer = BytesIO(open(pdf_path, "rb").read())
        buffer.seek(0)
        folder_map = {
            "homework": "Домашняя_работа",
            "assignment": "Классная_работа",
            "classwork": "Контрольная_работа",
            "study_plan": "План",
            "materials": "Обучающие_материалы",
        }
        folder = folder_map.get(category, "Материалы")
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category=folder,
            filename_base=base_name
        )

    # 8. Добавление в отчёт
    await crud.append_to_report(
        student_id=student.students_id,
        section=f"{category.capitalize()} (исправлено)",
        content=tex
    )

    # 9. Спрашиваем подтверждение снова
    kb = confirm_generation_keyboard(student.students_id, category)
    await message.answer("✅ Готово! Всё устраивает или внести ещё правки?", reply_markup=kb)

    # 10. Очищаем state
    await state.clear()




@router.callback_query(Text(startswith="diagnostic_check:"))
async def on_diagnostic_check(callback: CallbackQuery, state: FSMContext, **data):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.answer("📎 Пришлите, пожалуйста, документ с решением ученика.")
    await state.update_data(diagnostic_student=student_id)
    await state.set_state(StudentStates.awaiting_diagnostic_solution)


@router.message(StudentStates.awaiting_diagnostic_solution)
async def handle_diagnostic_solution(message: Message, state: FSMContext, **data):
    if not message.document:
        return await message.answer("⚠️ Пожалуйста, пришлите документ с решением.")

    student_id = (await state.get_data())["diagnostic_student"]
    teacher    = data["teacher"]

    # 1) Скачиваем файл и читаем как текст
    file = await message.bot.get_file(message.document.file_id)
    b   = BytesIO()
    await message.bot.download_file(file.file_path, b)
    text_solution = b.getvalue().decode('utf-8', errors='ignore')

    # 2) Берём ответ-ключ (текст), который мы сгенерировали ранее:
    #    его можно хранить в базе или в локальном кэше. 
    #    Для простоты: вызываем ту же функцию ключей.
    from services.gpt_service import generate_diagnostic_answer_key, check_solution
    key_text = await generate_diagnostic_answer_key(
        student=await crud.get_student_by_id_and_teacher(student_id, teacher.teacher_id),
        model=teacher.model,
        language=teacher.language
    )

    # 3) Проверяем решение через GPT
    analysis = await check_solution(
        student=await crud.get_student_by_id_and_teacher(student_id, teacher.teacher_id),
        model=teacher.model,
        solution=text_solution,
        expected=key_text,
        language=teacher.language
    )

    # 4) Добавляем в отчёт
    await crud.append_to_report(student_id, "Проверка диагностического теста", analysis)

    await message.answer("✅ Результаты проверки добавлены в отчёт.")
    await state.clear()
