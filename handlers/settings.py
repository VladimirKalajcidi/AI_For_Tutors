from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import database.crud as crud
from states.auth_state import AuthStates
from keyboards.main_menu import get_main_menu

router = Router()

@router.message(Text(text=["⚙️ Настройки", "⚙️ Settings"]))
async def menu_settings(message: types.Message, teacher):

    buttons = [
        [InlineKeyboardButton(text="🔗 Яндекс.Диск", callback_data="link_yandex")],
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🌐 Change Language", callback_data="set_lang")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Settings:", reply_markup=kb)

@router.callback_query(Text("set_lang"))
async def callback_set_lang(callback: types.CallbackQuery, teacher):
    await callback.answer()
    new_lang = "en" if teacher.language == "ru" else "ru"
    teacher.language = new_lang
    await crud.update_teacher(teacher)
    await callback.message.edit_text(f"Language changed to {'English' if new_lang=='en' else 'Russian'}.")
    # Send updated main menu in new language
    await callback.message.answer("Main menu:", reply_markup=get_main_menu(new_lang))

@router.callback_query(Text("link_disk"))
async def callback_link_disk(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AuthStates.register_password)  # reuse state for input
    await state.update_data(linking="yandex")
    await callback.message.edit_text("Please send your Yandex Disk OAuth token:")

@router.message(AuthStates.register_password)
async def process_link_token(message: types.Message, state: FSMContext, teacher):
    data = await state.get_data()
    if data.get("linking") == "yandex":
        token = message.text.strip()
        import yadisk
        client = yadisk.Client(token=token)
        try:
            if client.check_token():
                teacher.yandex_token = token
                await crud.update_teacher(teacher)
                await message.answer("✅ Yandex Disk linked successfully!")
            else:
                await message.answer("❌ Invalid token. Please try again:")
                return
        except Exception:
            await message.answer("❌ Error verifying token. Please try again.")
            return
        await state.clear()

@router.callback_query(Text("do_logout"))
async def callback_do_logout(callback: types.CallbackQuery, teacher):
    await callback.answer()
    teacher.is_logged_in = False
    await crud.update_teacher(teacher)
    await callback.message.edit_text("You have been logged out.")
