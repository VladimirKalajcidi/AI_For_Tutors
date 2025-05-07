from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database.crud as crud
from keyboards.main_menu import get_main_menu
from states.auth_state import AuthStates, TeacherProfileStates
from utils.security import hash_password, check_password
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот *AI For Tutors* – помощник для репетиторов.\n"
        "Я помогу вам вести базу учеников, расписание и создавать учебные материалы с помощью GPT.\n\n"
        "Чтобы начать, пожалуйста, зарегистрируйтесь или войдите в аккаунт.\n"
        "Используйте команду /register для регистрации или /login для входа.",
        parse_mode="Markdown"
    )


async def prompt_connect_yadisk(chat_id: int, bot: Bot, language: str = "ru"):
    text = (
        "🚀 <b>Подключите ваш Яндекс.Диск</b>\n\n"
        "Чтобы надёжно хранить и мгновенно получать доступ ко всем учебным материалам:\n"
        "• 📁 <b>Резервное копирование</b> ваших PDF-планов, тестов и отчётов\n"
        "• 📲 Доступ <b>из любого устройства</b> по ссылке\n"
        "• 🔗 Лёгкий обмен материалами через публичные ссылки\n"
        "• ☁️ Экономия места в чате — файлы хранятся в облаке, а не в Telegram\n\n"
        "Нажмите кнопку ниже, чтобы авторизовать Яндекс.Диск и начать."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ InlineKeyboardButton(
            text="🔗 Подключить Яндекс.Диск",
            callback_data="link_yandex_disk"        # <-- здесь
        ) ]
    ])
    await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

# ─── Регистрация ──────────────────────────────────────────────

@router.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    await state.set_state(AuthStates.register_login)
    await message.answer("📋 Введите логин для вашего аккаунта:")


@router.message(AuthStates.register_login)
async def process_register_login(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if await crud.get_teacher_by_login(username):
        await message.answer("⚠️ Такой логин уже существует. Попробуйте другой.")
        return
    await state.update_data(login=username)
    await state.set_state(AuthStates.register_password)
    await message.answer("🔑 Введите пароль для своего аккаунта:")


@router.message(AuthStates.register_password)
async def process_register_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    login = data["login"]
    password_hash = hash_password(password)

    # Проверяем, не привязан ли уже Telegram
    if await crud.get_teacher_by_telegram_id(message.from_user.id):
        await message.answer(
            "⚠️ У вас уже есть аккаунт, связанный с этим Telegram.\n"
            "Если вы забыли логин, используйте /login для входа."
        )
        await state.clear()
        return

    try:
        teacher = await crud.create_teacher(
            login=login,
            password_hash=password_hash,
            telegram_id=message.from_user.id
        )
    except Exception:
        await message.answer("❌ Не удалось зарегистрироваться. Попробуйте позже.")
        await state.clear()
        return

    await state.update_data(teacher_id=teacher.teacher_id)
    await state.set_state(TeacherProfileStates.surname)
    await message.answer(
        "✅ Регистрация успешна! Давайте заполним ваш профиль.\n"
        "ℹ️ Введите вашу фамилию:",
        parse_mode="Markdown"
    )


# ─── Анкета преподавателя ─────────────────────────────────────

@router.message(TeacherProfileStates.surname)
async def enter_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    await state.set_state(TeacherProfileStates.name)
    await message.answer("Введите ваше имя:")


@router.message(TeacherProfileStates.name)
async def enter_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(TeacherProfileStates.patronymic)
    await message.answer("Введите ваше отчество (если нет, отправьте '-'):")


@router.message(TeacherProfileStates.patronymic)
async def enter_patronymic(message: types.Message, state: FSMContext):
    await state.update_data(patronymic=message.text.strip())
    await state.set_state(TeacherProfileStates.birth_date)
    await message.answer("Введите вашу дату рождения (например, 24.12.1843):")


@router.message(TeacherProfileStates.birth_date)
async def enter_birth_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date=message.text.strip())
    await state.set_state(TeacherProfileStates.phone)
    await message.answer("Введите ваш номер телефона (с кодом страны, например: +7 ):")


@router.message(TeacherProfileStates.phone)
async def enter_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(TeacherProfileStates.email)
    await message.answer("Введите ваш email:")


@router.message(TeacherProfileStates.email)
async def enter_email(
    message: types.Message,
    state: FSMContext,
    bot: Bot,
):
    # Сохраняем данные профиля
    await state.update_data(email=message.text.strip())
    data = await state.get_data()
    teacher = await crud.get_teacher_by_id(data["teacher_id"])
    if not teacher:
        await message.answer("❌ Ошибка сохранения профиля.")
        await state.clear()
        return

    teacher.surname    = data["surname"]
    teacher.name       = data["name"]
    teacher.patronymic = data.get("patronymic", "")
    teacher.birth_date = data["birth_date"]
    teacher.phone      = data["phone"]
    teacher.email      = data["email"]
    await crud.update_teacher(teacher)
    await state.clear()

    # 1) Подтверждаем
    await message.answer("✅ Профиль сохранён!")

    # 2) Если Я.Диск не подключён — просим подключить
    if not teacher.yandex_token:
        await prompt_connect_yadisk(message.chat.id, bot, teacher.language)

    # 3) Затем — выбор модели GPT
    models_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Мощная модель", callback_data="choose_model:gpt-4.1-mini"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Самая сильная нейросеть", callback_data="choose_model:o4-mini"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Более слабая модель", callback_data="choose_model:gpt-4o-mini"
                )
            ]

    ])
    await message.answer(
        "💳 Выберите модель GPT для вашей подписки:",
        reply_markup=models_kb
    )


# ─── Вход ─────────────────────────────────────────────────────

@router.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    await state.set_state(AuthStates.login_username)
    await message.answer("🔑 Введите ваш логин:")


@router.message(AuthStates.login_username)
async def process_login_username(message: types.Message, state: FSMContext):
    login = message.text.strip()
    teacher = await crud.get_teacher_by_login(login)
    if not teacher:
        await message.answer(
            "⚠️ Логин не найден. Попробуйте снова или зарегистрируйтесь."
        )
        return
    await state.update_data(login=login)
    await state.set_state(AuthStates.login_password)
    await message.answer("Введите ваш пароль:")


@router.message(AuthStates.login_password)
async def process_login_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    teacher = await crud.get_teacher_by_login(data["login"])
    if not teacher or not check_password(message.text.strip(), teacher.password_hash):
        await message.answer("❌ Неверный логин или пароль.")
        await state.clear()
        return

    teacher.telegram_id = message.from_user.id
    await crud.update_teacher(teacher)
    await state.clear()

    await message.answer(
        f"✅ С возвращением, {teacher.name}!",
        reply_markup=get_main_menu(teacher.language)
    )