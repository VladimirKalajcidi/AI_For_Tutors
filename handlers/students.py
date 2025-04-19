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
from keyboards.students import edit_student_keyboard  # в начало файла, если ещё не импортирован


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
async def process_profile(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    profile = message.text.strip()
    if profile == "-":
        profile = ""
    await state.update_data(other_inf=profile)

    student_data = await state.get_data()

    new_student = await crud.create_student(
        teacher=teacher,
        name=student_data.get("name"),
        surname=student_data.get("surname"),
        class_=student_data.get("class_"),
        subject=student_data.get("subject"),
        phone=student_data.get("phone"),
        parent_phone=student_data.get("parent_phone"),
        other_inf=student_data.get("other_inf"),
    )

    await message.answer(f"✅ Student '{new_student.name} {new_student.surname}' added.")
    students = await crud.list_students(teacher)
    await message.answer("Updated student list:", reply_markup=students_list_keyboard(students))
    await state.clear()


@router.callback_query(Text(startswith="student:"))
async def callback_view_student(callback: types.CallbackQuery, **data):
    teacher = data.get("teacher")
    print("➡️ Вызван handler student:", teacher)
    if not teacher:
        await callback.answer("⚠️ Ошибка авторизации", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
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
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("✏️ Generating study plan, please wait...")

    from services import gpt_service, storage_service
    plan_text = await gpt_service.generate_study_plan(student, language=teacher.language)
    pdf_path = storage_service.generate_plan_pdf(plan_text, student.name)
    file_name = f"StudyPlan_{student.name}.pdf"

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"Study Plan for {student.name}"
        )
    except Exception:
        await callback.message.answer("📋 Study Plan:\n" + plan_text)

    if hasattr(teacher, "yandex_token") and teacher.yandex_token:
        success = await storage_service.upload_file(pdf_path, teacher, file_name, folder="plans")
        await callback.message.answer("📁 Plan saved to Yandex Disk." if success else "⚠️ Failed to upload to Yandex Disk.")

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )



@router.callback_query(Text(startswith="genassign:"))
async def callback_generate_assignment(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
    if not student:
        await callback.answer("Student not found.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("✏️ Генерация задания, подождите...")

    from services.gpt_service import generate_assignment
    from services.storage_service import generate_text_pdf

    assignment_text = await generate_assignment(student, language=teacher.language)
    file_name = f"Assignment_{student.name}_{student.surname}"
    pdf_path = generate_text_pdf(assignment_text, file_name)

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(pdf_path),
            caption=f"📝 Assignment for {student.name}"
        )
    except Exception:
        await callback.message.answer(f"📑 Assignment:\n{assignment_text}")

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )



@router.callback_query(Text(startswith="upload:"))
async def callback_upload_file(callback: CallbackQuery, state: FSMContext, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    if not teacher.yandex_token:
        await callback.answer()
        await callback.message.answer("⚠️ Yandex Disk is not linked. Link it in Settings.")
        return

    await callback.answer()
    await state.set_state(StudentStates.waiting_for_file)
    await state.update_data(student_id=student_id)
    await callback.message.edit_text("📎 Send the file (document) to upload for this student.")

@router.message(StudentStates.waiting_for_file)
async def process_file_upload(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    if not message.document:
        await message.answer("⚠️ Please upload a valid document file.")
        return

    student_id = (await state.get_data()).get("student_id")
    file_name = message.document.file_name or "file"
    import io
    buffer = io.BytesIO()
    await message.document.download(destination_file=buffer)
    buffer.seek(0)

    from services import storage_service
    success = await storage_service.upload_bytes(buffer, teacher, file_name, folder=f"student_{student_id}")
    await message.answer(f"✅ File '{file_name}' uploaded to Yandex Disk." if success else "⚠️ Upload failed. Check your cloud token.")
    await state.clear()

@router.callback_query(Text(startswith="genhomework:"))
async def callback_generate_homework(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
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

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )


@router.callback_query(Text(startswith="genclasswork:"))
async def callback_generate_classwork(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
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

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )

@router.callback_query(Text(startswith="genmaterials:"))
async def callback_generate_materials(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    student = await crud.get_student(teacher, student_id)
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

    await callback.message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student.students_id)
    )


@router.callback_query(Text(startswith="edit_student:"))
async def callback_edit_student(callback: CallbackQuery):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text(
        "✏️ Выберите, что вы хотите изменить:",
        reply_markup=edit_student_keyboard(student_id)
    )

@router.callback_query(Text(startswith="edit_field:"))
async def callback_edit_field(callback: CallbackQuery, state: FSMContext):
    _, student_id, field = callback.data.split(":")
    await state.set_state(StudentStates.editing_field)  # <-- добавлено
    await state.update_data(student_id=int(student_id), field=field)
    await callback.answer()
    await callback.message.edit_text(f"✏️ Введите новое значение для поля: *{field}*", parse_mode="Markdown")


@router.message(StateFilter(StudentStates.editing_field))
async def process_student_field_edit(message: Message, state: FSMContext, **data):

    state_data = await state.get_data()
    student_id = state_data.get("student_id")
    field = state_data.get("field")
    teacher = data.get("teacher")

    if not student_id or not field:
        return  # не режим редактирования

    new_value = message.text.strip()
    await crud.update_student_field(teacher, student_id, field, new_value)
    await state.clear()
    await message.answer(f"✅ Поле *{field}* обновлено!", parse_mode="Markdown")

    student = await crud.get_student(teacher, student_id)
    await message.answer(
        f"👤 {student.name} {student.surname or ''}\n"
        f"📚 Subject: {student.subject or 'N/A'}\n"
        f"ℹ️ Info: {student.other_inf or 'No additional info.'}",
        reply_markup=student_actions_keyboard(student_id)
    )

@router.callback_query(Text(startswith="delete_student:"))
async def callback_delete_student(callback: CallbackQuery):
    student_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.edit_text(
        "❗️Вы уверены, что хотите удалить ученика?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{student_id}")],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"student:{student_id}")]
        ])
    )

@router.callback_query(Text(startswith="confirm_delete:"))
async def callback_confirm_delete(callback: CallbackQuery, **data):
    teacher = data.get("teacher")
    student_id = int(callback.data.split(":")[1])
    await crud.delete_student(teacher, student_id)
    await callback.answer("🗑 Ученик удалён")

    students = await crud.list_students(teacher)
    if students:
        await callback.message.edit_text("📋 Список учеников обновлён:", reply_markup=students_list_keyboard(students))
    else:
        await callback.message.edit_text("У вас больше нет учеников.")

