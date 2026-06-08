from aiogram import Router, types, F
from database import Database
from config import Config
from keyboards import get_webapp_keyboard

router = Router(name="courses")
db = Database()

@router.message()
async def course_handler(message: types.Message):
    if not message.text:
        return
        
    # Dynamically match courses from the database
    courses = db.get_all_courses()
    course_names = {c['name'] for c in courses}
    
    if message.text in course_names:
        user_id = message.from_user.id
        status = db.get_user_status(user_id)
        
        # Allow access if they are approved or are admins
        is_allowed = (status == "approved") or (user_id in Config.ADMIN_IDS)
        
        if not is_allowed:
            if status == "banned":
                await message.answer("🚫 Siz botdan foydalanishdan chetlashtirilgansiz.")
            else:
                await message.answer("🔒 Sizda ruxsat yo'q! Avval ro'yxatdan o'tishingiz kerak. /start bosing.")
            return

        # Find matching course details
        course = next(c for c in courses if c['name'] == message.text)
        
        if course['webapp_url']:
            await message.answer(
                f"🩺 <b>{course['name']} darslari.</b>\n\n"
                f"Mavzularni ko'rish va o'rganish uchun quyidagi tugmani bosing:", 
                parse_mode="HTML",
                reply_markup=get_webapp_keyboard(course['webapp_url'])
            )
        else:
            await message.answer(
                f"📂 <b>{course['name']} materiallari</b>\n\n"
                f"Hozirda materiallar tayyorlanmoqda va tez orada yuklanadi! Bizni kuzatishda davom eting. ✨",
                parse_mode="HTML"
            )
