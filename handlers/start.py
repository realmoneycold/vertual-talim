from aiogram import Router, Bot, types
from aiogram.filters import CommandStart, Command
from database import Database
from config import Config
from keyboards import get_courses_keyboard, admin_permission_keyboard

router = Router(name="start")
db = Database()

@router.message(CommandStart())
async def start_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    status = db.get_user_status(user_id)

    # 1. Check if user is banned
    if status == 'banned':
        await message.answer("🚫 Siz botdan foydalanishdan chetlashtirilgansiz.")
        return

    # 2. Check if user is approved (or is admin)
    if status == 'approved' or user_id in Config.ADMIN_IDS:
        await message.answer("Xush kelibsiz! Kursni tanlang 👇", reply_markup=get_courses_keyboard())
        return

    # 3. Check if user is already pending
    if status == 'pending':
        await message.answer("⏳ Sizning so'rovingiz hali ko'rib chiqilmoqda. Iltimos, kuting.")
        return

    # 4. If new user, create pending request
    db.add_pending_user(
        user_id=user_id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    await message.answer("🔒 Botdan foydalanish uchun administrator ruxsati kerak. So'rov yuborildi.")

    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    
    # Notify all admins
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 <b>Yangi so'rov!</b>\n\n"
                    f"👤 Ismi: {message.from_user.full_name}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"🔗 Username: {username}"
                ),
                parse_mode="HTML",
                reply_markup=admin_permission_keyboard(user_id)
            )
        except Exception as e:
            # Avoid crashing if one of the admins hasn't started the bot yet or blocked it
            import logging
            logging.error(f"Failed to send request notification to admin {admin_id}: {e}")

@router.message(Command("help", "yordam"))
async def help_handler(message: types.Message):
    await message.answer(
        "📚 <b>Botdan foydalanish bo'yicha yordam:</b>\n\n"
        "• <code>/start</code> - Botni qayta ishga tushirish va asosiy menyuga o'tish.\n"
        "• <code>/help</code> yoki <code>/yordam</code> - Ushbu yordam xabarini ko'rsatish.\n\n"
        "<i>Agar sizda ruxsat bo'lmasa, birinchi marta kirganingizda ruxsat so'rovi yuboriladi. Administratorlar tasdiqlashgandan so'ng bot faollashadi.</i>\n\n"
        "📞 <b>Aloqa va Yordam / Support Contact:</b>\n"
        "Agar biror muammo yuzaga kelsa, iltimos, administratorga murojaat qiling:\n"
        "If you are experiencing any problems, please contact: @Irgashev_Physics_Teacher",
        parse_mode="HTML"
    )
