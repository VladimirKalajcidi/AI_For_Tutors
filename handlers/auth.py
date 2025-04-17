from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database.crud as crud
from keyboards.main_menu import get_main_menu
from states.auth_state import AuthStates, TeacherProfileStates
from utils.security import hash_password, check_password

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Hello! Please register or log in to use this bot.\nUse /register to sign up or /login to sign in.")



# ─── Регистрация ──────────────────────────────────────────────

@router.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    await state.set_state(AuthStates.register_login)
    await message.answer("Please enter a username for your account:")


@router.message(AuthStates.register_login)
async def process_register_login(message: types.Message, state: FSMContext):
    username = message.text.strip()
    existing = await crud.get_teacher_by_login(username)
    if existing:
        await message.answer("⚠️ This login already exists. Try another.")
        return
    await state.update_data(login=username)
    await state.set_state(AuthStates.register_password)
    await message.answer("Enter a password for your account:")


@router.message(AuthStates.register_password)
async def process_register_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    login = data["login"]
    password_hash = hash_password(password)

    # Проверяем, есть ли уже аккаунт с таким Telegram ID
    existing_telegram = await crud.get_teacher_by_telegram_id(message.from_user.id)
    if existing_telegram:
        await message.answer(
            "⚠️ You already have an account linked to this Telegram account.\n"
            "If you forgot your login, use /login to sign in.",
        )
        await state.clear()
        return

    try:
        teacher = await crud.create_teacher(
            login=login,
            password_hash=password_hash,
            telegram_id=message.from_user.id
        )
    except Exception as e:
        await message.answer("❌ Failed to register. Please try again or contact support.")
        await state.clear()
        return

    await state.update_data(teacher_id=teacher.teacher_id)
    await state.set_state(TeacherProfileStates.surname)
    await message.answer("✅ Registration successful! Let's fill out your profile.\nEnter your **surname**:", parse_mode="Markdown")


# ─── Анкета преподавателя ─────────────────────────────────────

@router.message(TeacherProfileStates.surname)
async def enter_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    await state.set_state(TeacherProfileStates.name)
    await message.answer("Enter your **name**:")


@router.message(TeacherProfileStates.name)
async def enter_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(TeacherProfileStates.patronymic)
    await message.answer("Enter your **patronymic** (middle name):")


@router.message(TeacherProfileStates.patronymic)
async def enter_patronymic(message: types.Message, state: FSMContext):
    await state.update_data(patronymic=message.text.strip())
    await state.set_state(TeacherProfileStates.birth_date)
    await message.answer("Enter your **birth date** (e.g., 1990-01-01):")


@router.message(TeacherProfileStates.birth_date)
async def enter_birth_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date=message.text.strip())
    await state.set_state(TeacherProfileStates.phone)
    await message.answer("Enter your **phone number**:")


@router.message(TeacherProfileStates.phone)
async def enter_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(TeacherProfileStates.email)
    await message.answer("Enter your **email** address:")


@router.message(TeacherProfileStates.email)
async def enter_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(TeacherProfileStates.subjects)
    await message.answer("Enter the **subjects** you teach (comma-separated):")


@router.message(TeacherProfileStates.subjects)
async def enter_subjects(message: types.Message, state: FSMContext):
    await state.update_data(subjects=message.text.strip())
    await state.set_state(TeacherProfileStates.occupation)
    await message.answer("Enter your **occupation** (e.g., tutor, teacher):")


@router.message(TeacherProfileStates.occupation)
async def enter_occupation(message: types.Message, state: FSMContext):
    await state.update_data(occupation=message.text.strip())
    await state.set_state(TeacherProfileStates.workplace)
    await message.answer("Enter your **workplace** (school, university, etc.):")


@router.message(TeacherProfileStates.workplace)
async def finish_profile(message: types.Message, state: FSMContext):
    await state.update_data(workplace=message.text.strip())
    data = await state.get_data()

    teacher = await crud.get_teacher_by_id(data["teacher_id"])
    teacher.surname = data["surname"]
    teacher.name = data["name"]
    teacher.patronymic = data["patronymic"]
    teacher.birth_date = data["birth_date"]
    teacher.phone = data["phone"]
    teacher.email = data["email"]
    teacher.subjects = data["subjects"]
    teacher.occupation = data["occupation"]
    teacher.workplace = data["workplace"]

    await crud.update_teacher(teacher)
    await message.answer("✅ Your profile has been saved!", reply_markup=get_main_menu())
    await state.clear()


# ─── Вход ─────────────────────────────────────────────────────


@router.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    await state.set_state(AuthStates.login_username)
    await message.answer("Enter your username:")


@router.message(AuthStates.login_username)
async def process_login_username(message: types.Message, state: FSMContext):
    login = message.text.strip()
    teacher = await crud.get_teacher_by_login(login)

    if not teacher:
        await message.answer("⚠️ No such user. Try again or register.")
        return

    await state.update_data(login=login)
    await state.set_state(AuthStates.login_password)
    await message.answer("Enter your password:")


@router.message(AuthStates.login_password)
async def process_login_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    teacher = await crud.get_teacher_by_login(data["login"])

    if not teacher or not check_password(message.text.strip(), teacher.password_hash):
        await message.answer("❌ Incorrect login or password.")
        await state.clear()
        return

    teacher.telegram_id = message.from_user.id
    await crud.update_teacher(teacher)
    await message.answer(f"✅ Welcome back, {teacher.name}!", reply_markup=get_main_menu())
    await state.clear()
