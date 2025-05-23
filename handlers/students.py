from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.handler import HandlerObject
import json
from aiogram.filters import StateFilter
import database.crud as crud
from keyboards.students import students_list_keyboard, student_actions_keyboard
from states.student_states import StudentStates
from keyboards.students import edit_student_keyboard, yandex_materials_keyboard  # в начало файла, если ещё не импортирован
from io import BytesIO
from services import storage_service
from services.storage_service import upload_bytes_to_yandex
from aiogram import Bot
from database.db import async_session
from database.models import Student
from sqlalchemy import select

router = Router()

@router.message(Text(text=["👨‍🎓 Ученики", "👨‍🎓 Students"]))
async def menu_students(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    students = await crud.list_students(teacher)
    if not students:
        await message.answer("No students yet. Use /add_student to add a student.")
    else:
        await message.answer("Your students:", reply_markup=students_list_keyboard(students))



@router.message(Command("add_student"))
async def cmd_add_student(message: Message, state: FSMContext, **data):
    await state.set_state(StudentStates.enter_name)
    await message.answer("Enter the new student's name:")


@router.callback_query(Text("add_student"))
async def callback_add_student(callback: CallbackQuery, state: FSMContext, **data):
    await callback.answer()
    await state.set_state(StudentStates.enter_name)
    await callback.message.edit_text("Enter the new student's name:")


@router.message(StudentStates.enter_name)
async def process_student_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(StudentStates.enter_surname)
    await message.answer("Enter the student's surname:")



@router.message(StudentStates.enter_surname)
async def process_student_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    await state.set_state(StudentStates.enter_class)
    await message.answer("Enter the student's class:")


@router.message(StudentStates.enter_class)
async def process_student_class(message: Message, state: FSMContext):
    await state.update_data(class_=message.text.strip())
    await state.set_state(StudentStates.enter_subject)
    await message.answer("Enter the subject for the student:")


@router.message(StudentStates.enter_subject)
async def process_subject_input(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await state.set_state(StudentStates.enter_phone)
    await message.answer("Enter the student's phone number:")




@router.message(StudentStates.enter_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(StudentStates.enter_parent_phone)
    await message.answer("Enter the parent's phone number:")


@router.message(StudentStates.enter_parent_phone)
async def process_parent_phone(message: Message, state: FSMContext):
    await state.update_data(parent_phone=message.text.strip())
    await state.set_state(StudentStates.enter_profile)
    await message.answer("Enter any additional info about the student (or '-' to skip):")


@router.message(StudentStates.enter_profile)
async def process_profile(message: Message, state: FSMContext):
    profile_text = message.text.strip()
    await state.update_data(profile=profile_text)
    await message.answer("🎯 Введите цель обучения:")
    await state.set_state(StudentStates.enter_goal)

@router.message(StudentStates.enter_goal)
async def process_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text.strip())
    await message.answer("📈 Введите уровень знаний ученика:")
    await state.set_state(StudentStates.enter_level)


@router.message(StudentStates.enter_level)
async def process_level(message: Message, state: FSMContext, **data):
    import json
    teacher = data.get("teacher")
    level = message.text.strip()

    student_data = await state.get_data()

    # Собираем structured JSON для other_inf
    other_inf = {
        "profile": student_data.get("profile"),
        "goal": student_data.get("goal"),
        "level": level,
    }

    new_student = await crud.create_student(
        teacher=teacher,
        name=student_data.get("name"),
        surname=student_data.get("surname"),
        class_=student_data.get("class_"),
        subject=student_data.get("subject"),
        phone=student_data.get("phone"),
        parent_phone=student_data.get("parent_phone"),
        other_inf=json.dumps(other_inf),
    )

    await message.answer(f"✅ Ученик '{new_student.name} {new_student.surname}' добавлен.")
    students = await crud.list_students(teacher)
    await message.answer("📋 Обновлённый список учеников:", reply_markup=students_list_keyboard(students))
    await state.clear()



@router.callback_query(Text(startswith="student:"))
async def callback_view_student(callback: types.CallbackQuery, **data):
    teacher = data.get("teacher")
    print("➡️ Вызван handler student:", teacher)
    if not teacher:
        await callback.answer("⚠️ Ошибка авторизации", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 2 or not parts[1].isdigit():
        await callback.answer("❌ Ошибка: ID ученика не передан.")
        return

    students_id = int(parts[1])

    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    # Распарсиваем other_inf (строка -> словарь)
    try:
        extra = json.loads(student.other_inf or "{}")
        goal = extra.get("goal", "—")
        level = extra.get("level", "—")
    except Exception:
        goal = level = "—"

    text = (
        f"👤 {student.name} {student.surname or ''}\n"
        f"🎯 Цель: {goal}\n"
        f"📈 Уровень: {level}\n"
        f"📚 Предмет: {student.subject or 'N/A'}\n"
        f"📅 Следующее занятие: {student.link_schedule.date if student.link_schedule else '—'}\n"
        f"📝 Тема: {student.report_student.next_lesson_topic if student.report_student else '—'}\n"
        f"📊 Прогресс: {student.report_student.progress if student.report_student else '—'}"
    )
    await callback.message.edit_text(text, reply_markup=student_actions_keyboard(student.students_id))



@router.callback_query(Text(startswith="back_students"))
async def back_to_students(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    await callback.answer()
    students = await crud.list_students(teacher)
    if not students:
        await callback.message.edit_text("No students yet.")
    else:
        await callback.message.edit_text("Your students:", reply_markup=students_list_keyboard(students))


@router.callback_query(Text(startswith="genplan:"))
async def callback_generate_plan(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("✏️ Generating study plan, please wait...")

    from services import gpt_service, storage_service
    plan_text = await gpt_service.generate_study_plan(student, language=teacher.language or "ru")
    pdf_path = storage_service.generate_plan_pdf(plan_text, student.name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"Study Plan for {student.name}"
        )
    except Exception:
        await callback.message.answer("📋 Study Plan:\n" + plan_text)

    if teacher.yandex_token:
        with open(pdf_path, "rb") as f:
            buffer = BytesIO(f.read())
            buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="План",
            filename_base="_"
        )

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )



@router.callback_query(Text(startswith="genassign:"))
async def callback_generate_assignment(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("✏️ Генерация задания, подождите...")

    from services.gpt_service import generate_assignment
    from services.storage_service import generate_text_pdf

    assignment_text = await generate_assignment(student, language=teacher.language or "ru")
    file_name = f"Assignment_{student.name}_{student.surname}"
    pdf_path = generate_text_pdf(assignment_text, file_name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📝 Assignment for {student.name}"
        )
    except Exception:
        await callback.message.answer(f"📑 Assignment:\n{assignment_text}")

    if teacher.yandex_token:
        with open(pdf_path, "rb") as f:
            buffer = BytesIO(f.read())
            buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Классная_работа",
            filename_base="_"
        )

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )





@router.callback_query(Text(startswith="upload:"))
async def callback_upload_file(callback: CallbackQuery, state: FSMContext, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    if not teacher.yandex_token:
        await callback.answer()
        await callback.message.answer("⚠️ Yandex Disk is not linked. Link it in Settings.")
        return

    await callback.answer()
    await state.set_state(StudentStates.waiting_for_file)
    await state.update_data(students_id=students_id)
    await callback.message.edit_text("📎 Send the file (document) to upload for this student.")



@router.message(StudentStates.waiting_for_file)
async def process_file_upload(message: Message, state: FSMContext, bot: Bot, **data):
    teacher = data.get("teacher")
    
    if not message.document:
        await message.answer("⚠️ Please upload a valid document file.")
        return

    state_data = await state.get_data()
    students_id = state_data.get("students_id")
    file_name = message.document.file_name or "file"

    # Получаем файл в память
    file = await bot.get_file(message.document.file_id)
    buffer = BytesIO()
    await bot.download_file(file.file_path, buffer)
    buffer.seek(0)

    # Получаем объект студента из БД
    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.students_id == students_id))
        student = result.scalar_one_or_none()

    if not student:
        await message.answer("❌ Ученик не найден.")
        await state.clear()
        return

    # Загружаем файл на Яндекс.Диск
    success = await upload_bytes_to_yandex(
        file_obj=buffer,
        teacher=teacher,
        student=student,
        category="Материалы",  # или другая категория
        filename_base=file_name.rsplit(".", 1)[0]
    )

    if success:
        await message.answer(f"✅ Файл '{file_name}' успешно загружен в Яндекс.Диск (категория: Материалы).")
    else:
        await message.answer("❌ Ошибка при загрузке файла на Я.Диск. Проверьте токен в настройках.")

    await state.clear()



@router.callback_query(Text(startswith="genhomework:"))
async def callback_generate_homework(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("📑 Генерация домашнего задания, подождите...")

    from services.gpt_service import generate_homework
    from services.storage_service import generate_text_pdf

    text = await generate_homework(student, language=teacher.language)
    file_name = f"Homework_{student.name}_{student.surname}"
    pdf_path = generate_text_pdf(text, file_name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📑 Домашнее задание для {student.name}"
        )
    except Exception:
        await callback.message.answer(f"📄 Homework:\n{text}")

    if teacher.yandex_token:
        with open(pdf_path, "rb") as f:
            buffer = BytesIO(f.read())
            buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Домашняя_работа",
            filename_base="_"
        )

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )


@router.callback_query(Text(startswith="genclasswork:"))
async def callback_generate_classwork(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("🧪 Генерация контрольной работы, подождите...")

    from services.gpt_service import generate_classwork
    from services.storage_service import generate_text_pdf

    text = await generate_classwork(student, language=teacher.language)
    file_name = f"Classwork_{student.name}_{student.surname}"
    pdf_path = generate_text_pdf(text, file_name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"🧪 Контрольная для {student.name}"
        )
    except Exception:
        await callback.message.answer(f"📄 Classwork:\n{text}")

    if teacher.yandex_token:
        with open(pdf_path, "rb") as f:
            buffer = BytesIO(f.read())
            buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Контрольная_работа",
            filename_base="_"
        )

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )

@router.callback_query(Text(startswith="genmaterials:"))
async def callback_generate_materials(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    students_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, students_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("📚 Подбор обучающих материалов, подождите...")

    from services.gpt_service import generate_learning_materials
    from services.storage_service import generate_text_pdf

    text = await generate_learning_materials(student, language=teacher.language)
    file_name = f"Materials_{student.name}_{student.surname}"
    pdf_path = generate_text_pdf(text, file_name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📚 Обучающие материалы для {student.name}"
        )
    except Exception:
        await callback.message.answer(f"📄 Learning Materials:\n{text}")

    if teacher.yandex_token:
        with open(pdf_path, "rb") as f:
            buffer = BytesIO(f.read())
            buffer.seek(0)
        await upload_bytes_to_yandex(
            file_obj=buffer,
            teacher=teacher,
            student=student,
            category="Обучающие_материалы",
            filename_base="_"
        )

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )



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
    await message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(students_id)
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
    from sqlalchemy import select
    from services.storage_service import upload_bytes_to_yandex

    # Получаем файл
    bot: Bot = message.bot
    file = await bot.get_file(message.document.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, destination=buffer)
    buffer.seek(0)

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
    success = await upload_bytes_to_yandex(
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


...

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
