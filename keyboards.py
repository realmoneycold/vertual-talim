from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import Config
from database import Database

db = Database()

def get_courses_keyboard(page: int = 1, limit: int = 6) -> types.ReplyKeyboardMarkup:
    """Returns a paginated reply keyboard for courses (6 per page) with navigation."""
    courses = db.get_all_courses()
    total_courses = len(courses)
    total_pages = (total_courses + limit - 1) // limit if total_courses > 0 else 1
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total_courses)
    page_courses = courses[start_idx:end_idx]
    
    builder = ReplyKeyboardBuilder()
    for course in page_courses:
        builder.button(text=course['name'])
    builder.adjust(2)
    
    nav_builder = ReplyKeyboardBuilder()
    if page > 1:
        nav_builder.button(text="◀️ Oldingi")
    if page < total_pages:
        nav_builder.button(text="Keyingi ▶️")
    nav_builder.adjust(2)
    
    builder.attach(nav_builder)
    return builder.as_markup(resize_keyboard=True)

def get_tests_inline_keyboard(course_id: int, page: int = 1, limit: int = 10) -> types.InlineKeyboardMarkup:
    """Returns a paginated inline keyboard with dynamic test buttons for the selected course."""
    kb = InlineKeyboardBuilder()
    tests = db.get_tests_for_course(course_id)
    total_tests = len(tests)
    total_pages = (total_tests + limit - 1) // limit if total_tests > 0 else 1
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total_tests)
    page_tests = tests[start_idx:end_idx]
    
    for t in page_tests:
        kb.button(text=t['name'], callback_data=f"user_test_select_{course_id}_{t['id']}")
    kb.adjust(2)
    
    # Pagination
    nav_kb = InlineKeyboardBuilder()
    if page > 1:
        nav_kb.button(text="◀️ Oldingi", callback_data=f"user_test_page_{course_id}_{page - 1}")
    nav_kb.button(text=f"📄 {page}/{total_pages}", callback_data="user_test_noop")
    if page < total_pages:
        nav_kb.button(text="Keyingi ▶️", callback_data=f"user_test_page_{course_id}_{page + 1}")
    nav_kb.adjust(3)
    
    kb.attach(nav_kb)
    return kb.as_markup()

def get_webapp_keyboard(webapp_url: str = Config.WEBAPP_URL) -> types.InlineKeyboardMarkup:
    """Returns the inline keyboard to open WebApp."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📱 Mavzuni WebApp'da ochish", 
        web_app=types.WebAppInfo(url=webapp_url)
    )
    return kb.as_markup()

def admin_permission_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Returns the inline keyboard for admin approvals, rejections, and bans."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ruxsat berish", callback_data=f"allow_{user_id}")
    kb.button(text="❌ Rad etish", callback_data=f"deny_{user_id}")
    kb.button(text="🚫 Bloklash", callback_data=f"ban_{user_id}")
    kb.adjust(2, 1) # First row: 2 buttons (Allow, Deny), Second row: 1 button (Ban)
    return kb.as_markup()

def admin_panel_keyboard() -> types.InlineKeyboardMarkup:
    """Returns the admin panel control buttons with Courses management button."""
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Foydalanuvchilar Ro'yxati", callback_data="admin_list_users")
    kb.button(text="🚫 Bloklanganlar Ro'yxati", callback_data="admin_list_banned")
    kb.button(text="📚 Kurslar", callback_data="admin_list_courses_view")
    kb.button(text="📢 Xabar yuborish (Broadcast)", callback_data="admin_broadcast")
    kb.adjust(1)
    return kb.as_markup()
