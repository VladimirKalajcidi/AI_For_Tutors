from aiogram import Router, types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import config
import database.crud as crud

router = Router()

@router.message(Text(text=["💳 Оплата"]))
async def payment_menu(message: types.Message, **data):
    teacher = data.get("teacher")
    if not teacher:
        await message.answer("❌ Вы не авторизованы. Пожалуйста, зарегистрируйтесь или войдите в аккаунт.")
        return

    from datetime import datetime
    now = datetime.now()
    exp_date = None
    if teacher.subscription_expires:
        try:
            exp_date = datetime.fromisoformat(teacher.subscription_expires)
        except Exception:
            exp_date = None

    if exp_date and exp_date > now:
        exp_str = exp_date.strftime("%d.%m.%Y")
        status_text = (
            f"🔓 Подписка активна до {exp_str}.\n"
            f"Текущий тариф: {teacher.model or '—'}, "
            f"{teacher.students_count or 0} учеников, "
            f"{teacher.tokens_limit or 0} токенов."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Изменить/Продлить подписку", callback_data="change_plan")]
        ])
        await message.answer(status_text, reply_markup=kb)
    else:
        await send_model_selection(message)

@router.callback_query(Text("change_plan"))
async def callback_change_plan(callback: types.CallbackQuery):
    await callback.answer()
    await send_model_selection(callback.message)

async def send_model_selection(message: types.Message):
    models_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="GPT-3.5 Turbo", callback_data="choose_model:gpt-3.5-turbo")],
        [InlineKeyboardButton(text="O3-Mini (быстрый)", callback_data="choose_model:o3-mini")],
        [InlineKeyboardButton(text="GPT-4 (mini)", callback_data="choose_model:gpt-4o-mini")],
        [InlineKeyboardButton(text="GPT-4 (max)", callback_data="choose_model:gpt-4o")],
    ])
    await message.answer("💳 Выберите модель GPT для новой подписки:", reply_markup=models_kb)

@router.callback_query(Text(startswith="choose_model:"))
async def callback_choose_model(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    model = callback.data.split(":")[1]
    await state.update_data(selected_model=model)

    students_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 ученик", callback_data="choose_students:1")],
        [InlineKeyboardButton(text="5 учеников", callback_data="choose_students:5")],
        [InlineKeyboardButton(text="10 учеников", callback_data="choose_students:10")],
        [InlineKeyboardButton(text="15 учеников", callback_data="choose_students:15")],
        [InlineKeyboardButton(text="20 учеников", callback_data="choose_students:20")],
        [InlineKeyboardButton(text="25+ учеников", callback_data="choose_students:25")],
    ])
    await callback.message.edit_text("👥 Выберите количество учеников:", reply_markup=students_kb)

@router.callback_query(Text(startswith="choose_students:"))
async def callback_choose_students(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    students_count = int(callback.data.split(":")[1])
    await state.update_data(selected_students=students_count)

    tokens_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2000 токенов", callback_data="choose_tokens:2000")],
        [InlineKeyboardButton(text="5000 токенов", callback_data="choose_tokens:5000")],
        [InlineKeyboardButton(text="10000 токенов", callback_data="choose_tokens:10000")],
        [InlineKeyboardButton(text="15000 токенов", callback_data="choose_tokens:15000")],
    ])
    await callback.message.edit_text("🔢 Выберите месячный лимит токенов на одного ученика:", reply_markup=tokens_kb)

@router.callback_query(Text(startswith="choose_tokens:"))
async def callback_choose_tokens(callback: types.CallbackQuery, teacher, state: FSMContext):
    await callback.answer()
    tokens_per_student = int(callback.data.split(":")[1])
    data = await state.get_data()
    model = data["selected_model"]
    students = data["selected_students"]

    cost_factor = {
        "gpt-3.5-turbo": 1.0,
        "o3-mini": 0.5,
        "gpt-4o-mini": 30.0,
        "gpt-4o": 60.0
    }
    base_rate_per_1000 = 0.16
    factor = cost_factor.get(model, 1.0)
    monthly_tokens = 24 * tokens_per_student * students
    estimated_cost_rub = (monthly_tokens / 1000) * base_rate_per_1000 * factor
    price = int(estimated_cost_rub * 20)

    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{model}:{students}:{tokens_per_student}:{price}")]
    ])
    pay_message = (
        f"💰 *Стоимость подписки: {price} руб/месяц.*\n"
        f"Для оплаты переведите *{price} руб.* на карту *Тбанка +7 903 076 44 46*.\n"
        f"После отправки денег нажмите кнопку 'Я оплатил'."
    )
    await callback.message.edit_text(pay_message, parse_mode="Markdown", reply_markup=pay_kb)

@router.callback_query(Text(startswith="paid:"))
async def callback_user_paid(callback: types.CallbackQuery, teacher, **data):
    await callback.answer("⌛ Ожидание подтверждения от администрации...", show_alert=True)
    _, model, students_str, tokens_str, price_str = callback.data.split(":")
    students = int(students_str)
    tokens_limit = int(tokens_str)
    price = int(price_str)

    bot = data["bot"]
    admin_id = config.ADMIN_TG_ID
    teacher_name = f"{teacher.name} {teacher.surname}".strip()
    text = (
        f"💳 Пользователь *{teacher_name}* запросил подписку:\n"
        f"Модель: {model}, Ученики: {students}, Токенов: {tokens_limit}\n"
        f"Сумма оплаты: {price} руб.\n\n"
        f"Подтвердить оплату?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"admin_confirm:{teacher.teacher_id}:{model}:{students}:{tokens_limit}")],
        [InlineKeyboardButton(text="❌ Нет", callback_data=f"admin_reject:{teacher.teacher_id}")]
    ])
    await bot.send_message(admin_id, text, parse_mode="Markdown", reply_markup=kb)

@router.callback_query(Text(startswith="admin_confirm:"))
async def callback_admin_confirm(callback: types.CallbackQuery, **data):
    if callback.from_user.id != config.ADMIN_TG_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, teacher_id, model, students_str, tokens_str = callback.data.split(":")
    students = int(students_str)
    tokens_limit = int(tokens_str)
    from datetime import datetime, timedelta
    teacher = await crud.get_teacher_by_id(int(teacher_id))
    if teacher:
        now = datetime.now()
        try:
            exp_old = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
        except Exception:
            exp_old = None
        new_exp = (exp_old + timedelta(days=config.SUBSCRIPTION_DURATION_DAYS)) if (exp_old and exp_old > now) else (now + timedelta(days=config.SUBSCRIPTION_DURATION_DAYS))
        teacher.subscription_expires = new_exp.isoformat()
        teacher.model = model
        teacher.students_count = students
        teacher.tokens_limit = tokens_limit
        await crud.update_teacher(teacher)

        bot = data["bot"]
        exp_str = new_exp.strftime("%d.%m.%Y")
        await bot.send_message(
            teacher.telegram_id,
            f"✅ Оплата подтверждена! Подписка активна до {exp_str}.\n"
            f"Теперь вам доступен полный функционал. Рекомендуем подключить Яндекс.Диск в настройках."
        )
    await callback.message.edit_text("✔️ Подписка подтверждена.")

@router.callback_query(Text(startswith="admin_reject:"))
async def callback_admin_reject(callback: types.CallbackQuery, **data):
    if callback.from_user.id != config.ADMIN_TG_ID:
        await callback.answer()
        return
    teacher_id = int(callback.data.split(":")[1])
    teacher = await crud.get_teacher_by_id(teacher_id)
    if teacher:
        bot = data["bot"]
        await bot.send_message(
            teacher.telegram_id,
            "❌ Платёж не подтверждён. Пожалуйста, убедитесь в правильности суммы и повторите попытку или обратитесь в поддержку @mx_hertx."
        )
    await callback.message.edit_text("Оплата отклонена.")
