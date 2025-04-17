from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.handler import HandlerObject

import database.crud as crud
from keyboards.students import students_list_keyboard, student_actions_keyboard
from states.student_states import StudentStates

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
async def callback_view_student(callback: types.CallbackQuery, **kwargs):
    teacher = kwargs.get("teacher")
    if not teacher:
        await callback.answer("⚠️ Ошибка авторизации", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    profile = await crud.get_student_full_profile(teacher, student_id)
    if not profile:
        await callback.answer("Student not found.", show_alert=True)
        return

    student = profile["student"]

    # Извлекаем level и goal из other_inf
    try:
        extra = json.loads(student.other_inf or "{}")
        level = extra.get("level", "не указано")
        goal = extra.get("goal", "не указано")
    except Exception:
        level = goal = "не указано"

    progress = profile["progress"] or "не указано"
    next_topic = profile["next_topic"] or "не указана"
    next_date = profile["next_date"] or "не указана"

    text = (
        f"👤 <b>{student.name} {student.surname}</b>\n"
        f"🎯 Цель: <i>{goal}</i>\n"
        f"🧠 Уровень: <i>{level}</i>\n"
        f"📈 Прогресс: <i>{progress}</i>\n"
        f"📘 Следующая тема: <i>{next_topic}</i>\n"
        f"📅 Следующее занятие: <i>{next_date}</i>"
    )
    await callback.message.edit_text(text, reply_markup=student_actions_keyboard(student.students_id), parse_mode="HTML")



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

    if teacher.yandex_token:
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
    await callback.message.edit_text("✏️ Generating assignment, please wait...")

    from services import gpt_service
    questions, answers = await gpt_service.generate_assignment(student, language=teacher.language)

    await callback.message.answer(f"📑 *Assignment Questions:*\n{questions}\n\n*Answers:*\n{answers}", parse_mode="Markdown")
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
