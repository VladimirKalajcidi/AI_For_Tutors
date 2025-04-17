from aiogram import Router, types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yookassa import Configuration, Payment
import config
import database.crud as crud

router = Router()


@router.message(Text(text=["💳 Оплата"]))
async def payment_menu(message: types.Message):
    await message.answer(
        "💳 *Платёжный раздел*\n\n"
        "Тут будет информация о подписке, доступе и способах оплаты.\n"
        "Вы можете выбрать тариф или продлить подписку.",
        parse_mode="Markdown"
    )


# Configure YooKassa credentials if provided
if config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY:
    Configuration.account_id = str(config.YOOKASSA_SHOP_ID)
    Configuration.secret_key = str(config.YOOKASSA_SECRET_KEY)

@router.message(Text(text=["Оплата", "Subscription"]))
async def menu_payment(message: types.Message, teacher):
    from datetime import datetime
    now = datetime.now()
    if teacher.subscription_expires and teacher.subscription_expires > now:
        exp_date = teacher.subscription_expires.strftime("%Y-%m-%d")
        status_text = f"Subscription active until {exp_date}."
    else:
        status_text = "No active subscription."
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Pay Subscription", callback_data="pay"))
    await message.answer(status_text, reply_markup=kb)

@router.callback_query(Text("pay"))
async def callback_pay(callback: types.CallbackQuery, teacher):
    # Create a payment for subscription
    amount = {"value": "500.00", "currency": "RUB"}  # example amount
    payment = Payment.create({
        "amount": amount,
        "confirmation": {"type": "redirect", "return_url": "https://example.com/return"},
        "capture": True,
        "description": "TutorBot Subscription"
    })
    pay_url = payment.confirmation.confirmation_url
    payment_id = payment.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💳 Pay Now", url=pay_url)],
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"checkpay:{payment_id}")]
    ])
    await callback.message.edit_text("Complete the payment by clicking [Pay Now], then press [I've Paid].", reply_markup=kb)
    await callback.answer()

@router.callback_query(Text(startswith="checkpay:"))
async def callback_check_payment(callback: types.CallbackQuery, teacher):
    payment_id = callback.data.split(":")[1]
    try:
        res = Payment.find_one(payment_id)
    except Exception:
        await callback.answer("Unable to check payment status right now.", show_alert=True)
        return
    if res.status == "succeeded":
        from datetime import datetime, timedelta
        teacher.subscription_expires = datetime.now() + timedelta(days=config.SUBSCRIPTION_DURATION_DAYS)
        teacher = await crud.update_teacher(teacher)
        exp_date = teacher.subscription_expires.strftime("%Y-%m-%d")
        await callback.message.edit_text(f"✅ Payment successful! Subscription active until {exp_date}.")
    elif res.status in ("pending", "waiting_for_capture"):
        await callback.answer("Payment not completed yet. Please finish payment and try again.", show_alert=True)
    else:
        await callback.answer(f"Payment status: {res.status}", show_alert=True)
