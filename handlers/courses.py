from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from database import Database
from config import Config
from keyboards import get_courses_keyboard, get_webapp_keyboard, get_tests_inline_keyboard

router = Router(name="courses")
db = Database()

# --- Handle Oldingi / Keyingi Reply Keyboard Pagination ---
@router.message(F.text.in_({"◀️ Oldingi", "Keyingi ▶️"}))
async def courses_navigation_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    status = db.get_user_status(user_id)
    
    # Check if approved
    is_allowed = (status == "approved") or (user_id in Config.ADMIN_IDS)
    if not is_allowed:
        return
        
    data = await state.get_data()
    current_page = data.get("course_page", 1)
    
    courses = db.get_all_courses()
    total_courses = len(courses)
    limit = 6
    total_pages = (total_courses + limit - 1) // limit if total_courses > 0 else 1
    
    if message.text == "Keyingi ▶️":
        new_page = min(current_page + 1, total_pages)
    else:
        new_page = max(current_page - 1, 1)
        
    await state.update_data(course_page=new_page)
    
    await message.answer(
        f"📄 <b>Sahifa {new_page}/{total_pages}</b>\n\n"
        "Kurslardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_courses_keyboard(page=new_page)
    )

# --- Handle Selecting a Course from reply keyboard ---
@router.message()
async def course_handler(message: types.Message, state: FSMContext):
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
            # Instead of opening the webapp directly, ask them to choose a test!
            await message.answer(
                f"📝 <b>Iltimos, testni tanlang:</b>",
                parse_mode="HTML",
                reply_markup=get_tests_inline_keyboard(course['id'])
            )
        else:
            await message.answer(
                f"📂 <b>{course['name']} materiallari</b>\n\n"
                f"Hozirda materiallar tayyorlanmoqda va tez orada yuklanadi! Bizni kuzatishda davom eting. ✨",
                parse_mode="HTML"
            )

# --- Handle Inline Test Selection Callbacks ---
@router.callback_query(F.data.startswith("user_test_select_"))
async def user_test_select_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    course_id = int(parts[3])
    test_num = int(parts[4])
    
    # Retrieve course details from db
    courses = db.get_all_courses()
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return await callback.answer("Kurs topilmadi!", show_alert=True)
        
    # Safely construct the webapp URL with test parameter
    base_url = course['webapp_url']
    if "?" in base_url:
        webapp_url_with_param = f"{base_url}&test={test_num}"
    else:
        webapp_url_with_param = f"{base_url}?test={test_num}"
        
    await callback.message.answer(
        f"🩺 <b>{course['name']} darslari, {test_num} - test.</b>\n\n"
        f"Mavzularni ko'rish va o'rganish uchun quyidagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=get_webapp_keyboard(webapp_url_with_param)
    )
    await callback.answer()
