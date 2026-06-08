import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- SOZLAMALAR ---
BOT_TOKEN = "8534683301:AAHWT4tuoix6uc9RMazpwNC_NhLXaBlFXBs"
ADMIN_IDS = [672335191, 6438818927]
ALLOWED_USERS_FILE = "allowed_users.txt"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- RUXSATLARNI BOSHQARISH ---
def get_allowed_users():
    if not os.path.exists(ALLOWED_USERS_FILE):
        return set(ADMIN_IDS)
    with open(ALLOWED_USERS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()} | set(ADMIN_IDS)

def save_user(user_id):
    with open(ALLOWED_USERS_FILE, "a") as f:
        f.write(f"{user_id}\n")

# --- KLAVIATURALAR ---
def get_courses_keyboard():
    kb = ReplyKeyboardBuilder()
    # 1 dan 3 gacha kurslar
    for i in range(1, 4):
        kb.button(text=f"{i}-kurs 📚")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def get_webapp_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Mavzuni WebApp'da ochish", 
              web_app=types.WebAppInfo(url="https://gleaming-frangipane-336680.netlify.app/"))
    return kb.as_markup()

def admin_permission_keyboard(user_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ruxsat berish", callback_data=f"allow_{user_id}")
    kb.button(text="❌ Rad etish", callback_data=f"deny_{user_id}")
    return kb.as_markup()

# --- HANDLERLAR ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    if message.from_user.id in get_allowed_users():
        await message.answer("Xush kelibsiz! Kursni tanlang 👇", reply_markup=get_courses_keyboard())
    else:
        await message.answer("🔒 Botdan foydalanish uchun administrator ruxsati kerak. So'rov yuborildi.")
        
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Yangi so'rov!</b>\n\n"
                f"👤 Ismi: {message.from_user.full_name}\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n"
                f"🔗 Username: {username}",
                parse_mode="HTML",
                reply_markup=admin_permission_keyboard(message.from_user.id)
            )

@dp.callback_query(F.data.startswith(("allow_", "deny_")))
async def admin_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)

    action, user_id = callback.data.split("_")
    user_id = int(user_id)

    if action == "allow":
        save_user(user_id)
        await callback.message.edit_text(f"{callback.message.text}\n\n🟢 Ruxsat berildi!")
        await bot.send_message(user_id, "🎉 Tabriklayman! Endi botdan foydalanishingiz mumkin. /start bosing.")
    else:
        await callback.message.edit_text(f"{callback.message.text}\n\n🔴 Rad etildi!")
        await bot.send_message(user_id, "❌ Afsuski, administrator ruxsat bermadi.")
    await callback.answer()

@dp.message(F.text.regexp(r"([1-3])-kurs 📚"))
async def course_handler(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        return await message.answer("🔒 Sizda ruxsat yo'q!")
    
    kurs = message.text[0]
    if kurs == "3":
        await message.answer("🩺 3-kurs: Propedevtika darslari. Tugmani bosing:", reply_markup=get_webapp_keyboard())
    else:
        await message.answer(f"📂 {kurs}-kurs materiallari ustida ishlamoqdamiz. Tez orada yuklanadi!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
