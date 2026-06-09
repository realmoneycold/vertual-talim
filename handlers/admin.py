import asyncio
from aiogram import Router, Bot, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
from config import Config
from keyboards import admin_panel_keyboard

router = Router(name="admin")
db = Database()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_test_url = State()
    waiting_for_test_edit_url = State()

# Middleware/Helper to verify if a user is admin
def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

def get_user_card(idx: int, u: dict, page: int, mode: str) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates the detailed card text and action buttons for a single user."""
    username = f"@{u['username']}" if u['username'] else "Mavjud emas"
    status_emoji = {
        "approved": "🟢",
        "pending": "⏳",
        "rejected": "🔴",
        "banned": "🚫"
    }.get(u['status'], "❓")
    
    text = (
        f"👤 <b>Foydalanuvchi #{idx}</b>\n\n"
        f"• Ismi: <b>{u['full_name']}</b>\n"
        f"• ID: <code>{u['user_id']}</code>\n"
        f"• Username: {username}\n"
        f"• Holat: {status_emoji} <b>{u['status'].upper()}</b>"
    )
    
    kb = InlineKeyboardBuilder()
    if mode == "banned" or u['status'] == "banned":
        # Unban is just approving the user so they can access the bot
        kb.button(text="🔓 Blokdan chiqarish", callback_data=f"admin_act_{mode}_allow_{u['user_id']}_{idx}_{page}")
    else:
        if u['status'] == 'approved':
            kb.button(text="❌ Ruxsatni olish", callback_data=f"admin_act_{mode}_kick_{u['user_id']}_{idx}_{page}")
            kb.button(text="🚫 Bloklash", callback_data=f"admin_act_{mode}_ban_{u['user_id']}_{idx}_{page}")
        elif u['status'] == 'pending':
            kb.button(text="✅ Tasdiqlash", callback_data=f"admin_act_{mode}_allow_{u['user_id']}_{idx}_{page}")
            kb.button(text="❌ Rad etish", callback_data=f"admin_act_{mode}_deny_{u['user_id']}_{idx}_{page}")
            kb.button(text="🚫 Bloklash", callback_data=f"admin_act_{mode}_ban_{u['user_id']}_{idx}_{page}")
        elif u['status'] in ('rejected', 'banned'):
            kb.button(text="✅ Ruxsat berish", callback_data=f"admin_act_{mode}_allow_{u['user_id']}_{idx}_{page}")
            
    kb.button(text="⬅️ Orqaga", callback_data=f"admin_page_{mode}_{page}")
    kb.adjust(2, 1)
    return text, kb.as_markup()

def get_users_list_page(users: list[dict], page: int, mode: str, limit: int = 10) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates a text list of users for a specific page with selection and page-navigation buttons."""
    total_users = len(users)
    total_pages = (total_users + limit - 1) // limit if total_users > 0 else 1
    
    # Bound the page number safely
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total_users)
    
    page_users = users[start_idx:end_idx]
    
    title = "Foydalanuvchilar Ro'yxati" if mode == "all" else "Bloklanganlar Ro'yxati"
    text = f"👥 <b>{title} ({start_idx + 1}-{end_idx} / {total_users}):</b>\n\n"
    
    selection_kb = InlineKeyboardBuilder()
    
    # Row 1: Direct selection buttons for listed users (labelled by their list index)
    for index, u in enumerate(page_users, start=start_idx + 1):
        username = f"@{u['username']}" if u['username'] else "Mavjud emas"
        status_emoji = {
            "approved": "🟢",
            "pending": "⏳",
            "rejected": "🔴",
            "banned": "🚫"
        }.get(u['status'], "❓")
        
        text += (
            f"<b>{index}. {u['full_name']}</b> | ID: <code>{u['user_id']}</code>\n"
            f"   Username: {username} | Holat: {status_emoji} {u['status'].upper()}\n\n"
        )
        
        # Add button to manage this specific user
        selection_kb.button(text=f"{index}", callback_data=f"admin_manage_{mode}_{u['user_id']}_{index}_{page}")
        
    # Adjust selection buttons (up to 5 in a row)
    selection_kb.adjust(5)
    
    # Row 2: Pagination buttons (Prev, Page/Total, Next)
    pagination_kb = InlineKeyboardBuilder()
    if page > 1:
        pagination_kb.button(text="◀️ Oldingi", callback_data=f"admin_page_{mode}_{page - 1}")
    pagination_kb.button(text=f"📄 {page}/{total_pages}", callback_data="admin_noop")
    if page < total_pages:
        pagination_kb.button(text="Keyingi ▶️", callback_data=f"admin_page_{mode}_{page + 1}")
    pagination_kb.adjust(3)
    
    # Row 3: Return to main admin panel menu button
    admin_back_kb = InlineKeyboardBuilder()
    admin_back_kb.button(text="⬅️ Admin panelga qaytish", callback_data="admin_panel_menu")
    admin_back_kb.adjust(1)
    
    # Combine keyboards
    selection_kb.attach(pagination_kb)
    selection_kb.attach(admin_back_kb)
    return text, selection_kb.as_markup()

@router.message(Command("admin"))
async def admin_panel_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    users = db.get_all_users()
    total = len(users)
    approved = len([u for u in users if u["status"] == "approved"])
    pending = len([u for u in users if u["status"] == "pending"])
    banned = len([u for u in users if u["status"] == "banned"])

    stats_text = (
        f"⚙️ <b>Admin boshqaruv paneli</b>\n\n"
        f"📊 Bot statistikasi:\n"
        f"• Umumiy foydalanuvchilar: {total}\n"
        f"• Faol (Ruxsat berilgan): {approved}\n"
        f"• Kutayotganlar: {pending}\n"
        f"• Bloklanganlar: {banned}\n\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    await message.answer(stats_text, parse_mode="HTML", reply_markup=admin_panel_keyboard())

@router.callback_query(F.data == "admin_list_users")
async def list_users_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    users = db.get_all_users()
    if not users:
        await callback.message.answer("Hozircha foydalanuvchilar mavjud emas.")
        await callback.answer()
        return

    text, kb = get_users_list_page(users, page=1, mode="all")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_list_banned")
async def list_banned_users_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    banned_users = db.get_users_by_status("banned")
    if not banned_users:
        return await callback.answer("Hozircha bloklangan foydalanuvchilar mavjud emas.", show_alert=True)

    text, kb = get_users_list_page(banned_users, page=1, mode="banned")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_page_"))
async def list_users_page_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    parts = callback.data.split("_")
    mode = parts[2]
    page = int(parts[3])
    
    if mode == "all":
        users = db.get_all_users()
    else:
        users = db.get_users_by_status("banned")
        
    text, kb = get_users_list_page(users, page=page, mode=mode)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_manage_"))
async def manage_user_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    parts = callback.data.split("_")
    mode = parts[2]
    user_id = int(parts[3])
    idx = int(parts[4])
    page = int(parts[5])

    if mode == "all":
        users = db.get_all_users()
    else:
        users = db.get_users_by_status("banned")
        
    user_data = next((u for u in users if u["user_id"] == user_id), None)
    
    if not user_data:
        return await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)

    card_text, card_kb = get_user_card(idx, user_data, page, mode)
    await callback.message.edit_text(card_text, parse_mode="HTML", reply_markup=card_kb)
    await callback.answer()

@router.callback_query(F.data == "admin_panel_menu")
async def admin_panel_menu_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    users = db.get_all_users()
    total = len(users)
    approved = len([u for u in users if u["status"] == "approved"])
    pending = len([u for u in users if u["status"] == "pending"])
    banned = len([u for u in users if u["status"] == "banned"])

    stats_text = (
        f"⚙️ <b>Admin boshqaruv paneli</b>\n\n"
        f"📊 Bot statistikasi:\n"
        f"• Umumiy foydalanuvchilar: {total}\n"
        f"• Faol (Ruxsat berilgan): {approved}\n"
        f"• Kutayotganlar: {pending}\n"
        f"• Bloklanganlar: {banned}\n\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=admin_panel_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast_callback(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 <b>Barcha tasdiqlangan foydalanuvchilarga xabar yuborish.</b>\n\n"
        "Xabarni yuboring (matn, rasm, video va h.k. bo'lishi mumkin) yoki bekor qilish uchun /cancel deb yozing:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_message(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Broadcast bekor qilindi.")
        return

    await state.clear()
    await message.answer("⏳ Xabar yuborilmoqda...")

    # Get approved users only
    approved_users = db.get_users_by_status("approved")
    # Also send to admins if they are not in the approved users list yet
    targets = {u["user_id"] for u in approved_users} | set(Config.ADMIN_IDS)

    success_count = 0
    fail_count = 0

    for user_id in targets:
        try:
            # We can use message.copy_to() to preserve formatting, photos, videos, and captions
            await message.copy_to(chat_id=user_id)
            success_count += 1
            # Add small delay to avoid hitting Telegram flood limits (max 30 messages per second)
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await message.answer(
        f"📢 Broadcast yakunlandi!\n\n"
        f"✅ Muvaffaqiyatli: {success_count}\n"
        f"❌ Muvaffaqiyatsiz (botni bloklaganlar): {fail_count}"
    )

# --- Dynamic Actions (Allow, Deny, Ban, Kick) via Pagination detail ---
@router.callback_query(F.data.startswith("admin_act_"))
async def admin_action_callback(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)

    parts = callback.data.split("_")
    mode = parts[2]
    action = parts[3]
    user_id = int(parts[4])
    idx = int(parts[5])
    page = int(parts[6])

    notification_sent = False

    if action == "allow":
        if mode == "banned":
            # Unbanning: Set status to rejected so they must request authority again on /start
            db.reject_user(user_id, callback.from_user.id)
            try:
                await bot.send_message(user_id, "🔓 Siz botdan blokdan chiqarildingiz! Endi botdan foydalanish uchun ruxsat so'rashingiz mumkin. /start tugmasini bosing.")
                notification_sent = True
            except Exception:
                pass
        else:
            db.approve_user(user_id, callback.from_user.id)
            try:
                await bot.send_message(user_id, "🎉 Tabriklayman! Endi botdan foydalanishingiz mumkin. /start bosing.")
                notification_sent = True
            except Exception:
                pass
            
    elif action in ("deny", "kick"):
        db.reject_user(user_id, callback.from_user.id)
        try:
            await bot.send_message(user_id, "❌ Sizning botdan foydalanish ruxsatingiz bekor qilindi.")
            notification_sent = True
        except Exception:
            pass
            
    elif action == "ban":
        db.ban_user(user_id, callback.from_user.id)
        try:
            await bot.send_message(user_id, "🚫 Siz ushbu botdan butunlay bloklandingiz.")
            notification_sent = True
        except Exception:
            pass

    # Retrieve updated user list and data to refresh the text status and key buttons
    all_users = db.get_all_users()
    matched_user = next((u for u in all_users if u["user_id"] == user_id), None)
    
    if matched_user:
        new_text, new_kb = get_user_card(idx, matched_user, page, mode)
        try:
            await callback.message.edit_text(new_text, parse_mode="HTML", reply_markup=new_kb)
        except Exception:
            pass
            
    # Notify admin about result
    if action == "allow" and mode == "banned":
        status_msg = "🔓 Blokdan chiqarildi!"
    else:
        status_msg = {
            "allow": "🟢 Ruxsat berildi!",
            "deny": "🔴 Ruxsat rad etildi!",
            "kick": "❌ Ruxsat olib qo'yildi (Kicked)!",
            "ban": "🚫 Bloklandi (Banned)!"
        }.get(action, "Bajarildi!")

    await callback.answer(f"{status_msg} " + ("(Xabar yetkazildi)" if notification_sent else "(Foydalanuvchiga xabar yuborib bo'lmadi)"), show_alert=False)


# --- Direct Direct-Request Approvals (allow_, deny_, ban_) from new user notifications ---
@router.callback_query(F.data.startswith(("allow_", "deny_", "ban_")))
async def direct_request_action_callback(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)

    parts = callback.data.split("_")
    action = parts[0]
    user_id = int(parts[1])

    notification_sent = False

    if action == "allow":
        db.approve_user(user_id, callback.from_user.id)
        await callback.message.edit_text(f"{callback.message.text}\n\n🟢 Tasdiqlandi (Ruxsat berildi)!")
        try:
            await bot.send_message(user_id, "🎉 Tabriklayman! Endi botdan foydalanishingiz mumkin. /start bosing.")
            notification_sent = True
        except Exception:
            pass
            
    elif action == "deny":
        db.reject_user(user_id, callback.from_user.id)
        await callback.message.edit_text(f"{callback.message.text}\n\n🔴 Rad etildi!")
        try:
            await bot.send_message(user_id, "❌ Afsuski, administrator ruxsat bermadi.")
            notification_sent = True
        except Exception:
            pass
            
    elif action == "ban":
        db.ban_user(user_id, callback.from_user.id)
        await callback.message.edit_text(f"{callback.message.text}\n\n🚫 Foydalanuvchi butunlay bloklandi!")
        try:
            await bot.send_message(user_id, "🚫 Siz ushbu botdan butunlay bloklandingiz.")
            notification_sent = True
        except Exception:
            pass

    status_msg = {
        "allow": "Tasdiqlandi!",
        "deny": "Rad etildi!",
        "ban": "Bloklandi!"
    }.get(action, "Bajarildi!")

    await callback.answer(f"✅ {status_msg} " + ("(Xabar yetkazildi)" if notification_sent else "(Xabar yetkazib bo'lmadi)"), show_alert=False)


# --- helper tools for Courses & Tests Management ---
def get_courses_list_page(courses: list[dict], page: int, limit: int = 10) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates a text list of courses (folders) with selection, addition, and navigation buttons."""
    total_courses = len(courses)
    total_pages = (total_courses + limit - 1) // limit if total_courses > 0 else 1
    
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total_courses)
    
    page_courses = courses[start_idx:end_idx]
    
    text = f"📚 <b>Kurslar Ro'yxati ({start_idx + 1}-{end_idx} / {total_courses}):</b>\n\n"
    
    selection_kb = InlineKeyboardBuilder()
    
    # Direct selection index buttons
    for index, c in enumerate(page_courses, start=start_idx + 1):
        text += f"<b>{index}. {c['name']}</b> (Mavjuda darsliklar va testlar papkasi)\n\n"
        selection_kb.button(text=f"{index}", callback_data=f"admin_course_manage_{c['id']}_{index}_{page}")
        
    selection_kb.adjust(5)
    
    # Pagination
    pagination_kb = InlineKeyboardBuilder()
    if page > 1:
        pagination_kb.button(text="◀️ Oldingi", callback_data=f"admin_course_page_{page - 1}")
    pagination_kb.button(text=f"📄 {page}/{total_pages}", callback_data="admin_noop")
    if page < total_pages:
        pagination_kb.button(text="Keyingi ▶️", callback_data=f"admin_course_page_{page + 1}")
    pagination_kb.adjust(3)
    
    # Options
    action_kb = InlineKeyboardBuilder()
    action_kb.button(text="➕ Kurs qo'shish (folder)", callback_data="admin_course_add_auto")
    action_kb.button(text="⬅️ Admin panelga qaytish", callback_data="admin_panel_menu")
    action_kb.adjust(1)
    
    selection_kb.attach(pagination_kb)
    selection_kb.attach(action_kb)
    return text, selection_kb.as_markup()

def get_course_tests_list_page(course: dict, tests: list[dict], course_idx: int, course_page: int, test_page: int = 1, limit: int = 10) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates a list of tests for a specific course with test selection, addition, and pagination buttons."""
    total_tests = len(tests)
    total_pages = (total_tests + limit - 1) // limit if total_tests > 0 else 1
    
    test_page = max(1, min(test_page, total_pages))
    start_idx = (test_page - 1) * limit
    end_idx = min(start_idx + limit, total_tests)
    
    page_tests = tests[start_idx:end_idx]
    
    text = f"📂 <b>{course['name']} ichidagi testlar ({start_idx + 1}-{end_idx} / {total_tests}):</b>\n\n"
    if not tests:
        text += "<i>Hozircha testlar mavjud emas. Yangi test qo'shish uchun pastdagi tugmani bosing!</i>\n\n"
        
    selection_kb = InlineKeyboardBuilder()
    for index, t in enumerate(page_tests, start=start_idx + 1):
        text += f"<b>{index}. {t['name']}</b>\n   🔗 Havola: <code>{t['webapp_url']}</code>\n\n"
        selection_kb.button(text=f"{index}", callback_data=f"admin_test_manage_{t['id']}_{course['id']}_{course_idx}_{course_page}_{index}_{test_page}")
        
    selection_kb.adjust(5)
    
    # Pagination for tests list
    pagination_kb = InlineKeyboardBuilder()
    if test_page > 1:
        pagination_kb.button(text="◀️ Oldingi testlar", callback_data=f"admin_test_page_{course['id']}_{course_idx}_{course_page}_{test_page - 1}")
    pagination_kb.button(text=f"📄 {test_page}/{total_pages}", callback_data="admin_noop")
    if test_page < total_pages:
        pagination_kb.button(text="Keyingi testlar ▶️", callback_data=f"admin_test_page_{course['id']}_{course_idx}_{course_page}_{test_page + 1}")
    pagination_kb.adjust(3)
    
    action_kb = InlineKeyboardBuilder()
    action_kb.button(text="➕ Test qo'shish", callback_data=f"admin_test_add_{course['id']}_{course_idx}_{course_page}")
    action_kb.button(text="❌ Kursni o'chirish", callback_data=f"admin_course_delete_from_list_{course['id']}_{course_idx}_{course_page}")
    action_kb.button(text="⬅️ Kurslar ro'yxatiga qaytish", callback_data=f"admin_course_page_{course_page}")
    action_kb.adjust(1)
    
    selection_kb.attach(pagination_kb)
    selection_kb.attach(action_kb)
    return text, selection_kb.as_markup()

def get_test_card(t: dict, course_name: str, course_idx: int, course_page: int, test_idx: int, test_page: int) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates the detailed card text and action buttons for a single test."""
    text = (
        f"📝 <b>Test Tafsilotlari</b>\n\n"
        f"• Kurs: <b>{course_name}</b>\n"
        f"• Test: <b>{t['name']}</b>\n"
        f"• Havola: <code>{t['webapp_url']}</code>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Havolani tahrirlash", callback_data=f"admin_test_edit_url_{t['id']}_{t['course_id']}_{course_idx}_{course_page}_{test_idx}_{test_page}")
    kb.button(text="❌ Testni o'chirish", callback_data=f"admin_test_delete_{t['id']}_{t['course_id']}_{course_idx}_{course_page}_{test_idx}_{test_page}")
    kb.button(text="⬅️ Orqaga", callback_data=f"admin_test_list_{t['course_id']}_{course_idx}_{course_page}_{test_page}")
    kb.adjust(2, 1)
    return text, kb.as_markup()


# --- Courses Folders View callbacks & handlers ---
@router.callback_query(F.data == "admin_list_courses_view")
async def list_courses_view_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    courses = db.get_all_courses()
    text, kb = get_courses_list_page(courses, page=1)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_course_page_"))
async def course_page_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    page = int(callback.data.split("_")[3])
    courses = db.get_all_courses()
    text, kb = get_courses_list_page(courses, page=page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "admin_course_add_auto")
async def admin_course_add_auto_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    courses = db.get_all_courses()
    
    # Extract numbers to determine next incrementing course
    numbers = []
    for c in courses:
        import re
        match = re.search(r"(\d+)-kurs", c['name'])
        if match:
            numbers.append(int(match.group(1)))
            
    next_number = max(numbers) + 1 if numbers else len(courses) + 1
    course_name = f"{next_number}-kurs 📚"
    
    # Add course folder immediately without asking for a link!
    success = db.add_course(name=course_name, description=f"{course_name} materiallari va darslari", webapp_url=None)
    
    if success:
        await callback.answer(f"🎉 Yangi {course_name} muvaffaqiyatli yaratildi!", show_alert=True)
        # Refresh current page view
        courses = db.get_all_courses()
        text, kb = get_courses_list_page(courses, page=999) # go to last page
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.answer("❌ Xatolik yuz berdi. Kurs yaratilmadi.", show_alert=True)


# --- Tests list & navigation inside Course Folder callbacks ---
@router.callback_query(F.data.startswith("admin_course_manage_"))
async def course_manage_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[3])
    course_idx = int(parts[4])
    course_page = int(parts[5])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    if not c:
        return await callback.answer("Kurs topilmadi!", show_alert=True)
        
    tests = db.get_tests_for_course(course_id)
    text, kb = get_course_tests_list_page(c, tests, course_idx, course_page, test_page=1)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_test_page_"))
async def test_page_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[3])
    course_idx = int(parts[4])
    course_page = int(parts[5])
    test_page = int(parts[6])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    if not c:
        return await callback.answer("Kurs topilmadi!", show_alert=True)
        
    tests = db.get_tests_for_course(course_id)
    text, kb = get_course_tests_list_page(c, tests, course_idx, course_page, test_page=test_page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_test_list_"))
async def test_list_callback(callback: types.CallbackQuery):
    # Back button from a test card
    parts = callback.data.split("_")
    course_id = int(parts[3])
    course_idx = int(parts[4])
    course_page = int(parts[5])
    test_page = int(parts[6])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    tests = db.get_tests_for_course(course_id)
    
    text, kb = get_course_tests_list_page(c, tests, course_idx, course_page, test_page=test_page)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_test_manage_"))
async def test_manage_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    test_id = int(parts[3])
    course_id = int(parts[4])
    course_idx = int(parts[5])
    course_page = int(parts[6])
    test_idx = int(parts[7])
    test_page = int(parts[8])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    
    tests = db.get_tests_for_course(course_id)
    t = next((item for item in tests if item["id"] == test_id), None)
    if not t:
        return await callback.answer("Test topilmadi!", show_alert=True)
        
    text, kb = get_test_card(t, c["name"], course_idx, course_page, test_idx, test_page)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# --- Add Test to Course Flow ---
@router.callback_query(F.data.startswith("admin_test_add_"))
async def admin_test_add_callback(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[3])
    course_idx = int(parts[4])
    course_page = int(parts[5])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    
    tests = db.get_tests_for_course(course_id)
    next_test_number = len(tests) + 1
    test_name = f"{next_test_number} - test"
    
    await state.set_state(AdminStates.waiting_for_test_url)
    await state.update_data(
        add_course_id=course_id,
        add_test_name=test_name,
        add_course_idx=course_idx,
        add_course_page=course_page
    )
    
    await callback.message.answer(
        f"➕ <b>Test qo'shish</b>\n\n"
        f"• Kurs: <b>{c['name']}</b>\n"
        f"• Yangi test: <b>{test_name}</b>\n\n"
        f"Iltimos, ushbu test uchun havola (URL) yuboring:\n"
        f"Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_test_url)
async def process_test_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Test qo'shish bekor qilindi.")
        return
        
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ Noto'g'ri URL manzili formati (http:// yoki https:// bilan boshlanishi kerak). Qayta urinib ko'ring:")
        return
        
    data = await state.get_data()
    course_id = data["add_course_id"]
    test_name = data["add_test_name"]
    
    # Save test to database
    success = db.add_test(course_id=course_id, name=test_name, webapp_url=url)
    await state.clear()
    
    if success:
        await message.answer(
            f"🎉 <b>Test muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📝 Nomi: {test_name}\n"
            f"🔗 Havola: {url}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Xatolik yuz berdi. Ushbu nomli test allaqachon mavjud bo'lishi mumkin.")


# --- Edit Test Link Flow ---
@router.callback_query(F.data.startswith("admin_test_edit_url_"))
async def admin_test_edit_url_callback(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    test_id = int(parts[4])
    course_id = int(parts[5])
    course_idx = int(parts[6])
    course_page = int(parts[7])
    test_idx = int(parts[8])
    test_page = int(parts[9])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    
    tests = db.get_tests_for_course(course_id)
    t = next((item for item in tests if item["id"] == test_id), None)
    if not t:
        return await callback.answer("Test topilmadi!", show_alert=True)
        
    await state.set_state(AdminStates.waiting_for_test_edit_url)
    await state.update_data(
        edit_test_id=test_id,
        edit_course_id=course_id,
        edit_course_idx=course_idx,
        edit_course_page=course_page,
        edit_test_idx=test_idx,
        edit_test_page=test_page
    )
    
    await callback.message.answer(
        f"🔗 <b>{c['name']} - {t['name']} havolasini tahrirlash</b>\n\n"
        f"Iltimos, ushbu test uchun yeni havolani yuboring:\n"
        f"Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_test_edit_url)
async def process_test_edit_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Tahrirlash bekor qilindi.")
        return
        
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ Noto'g'ri URL manzili formati (http:// yoki https:// bilan boshlanishi kerak). Qayta urinib ko'ring:")
        return
        
    data = await state.get_data()
    test_id = data["edit_test_id"]
    
    success = db.update_test_url(test_id, url)
    await state.clear()
    
    if success:
        await message.answer("✅ <b>Test havolasi muvaffaqiyatli yangilandi!</b>", parse_mode="HTML")
    else:
        await message.answer("❌ Havolani yangilashda xatolik yuz berdi.")


# --- Delete Test Callbacks ---
@router.callback_query(F.data.startswith("admin_test_delete_"))
async def admin_test_delete_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    test_id = int(parts[3])
    course_id = int(parts[4])
    course_idx = int(parts[5])
    course_page = int(parts[6])
    test_idx = int(parts[7])
    test_page = int(parts[8])
    
    success = db.delete_test(test_id, course_id)
    if success:
        await callback.answer("✅ Test o'chirildi va qolganlari qayta tartiblandi!", show_alert=True)
        courses = db.get_all_courses()
        c = next((item for item in courses if item["id"] == course_id), None)
        tests = db.get_tests_for_course(course_id)
        
        text, kb = get_course_tests_list_page(c, tests, course_idx, course_page, test_page=test_page)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
    else:
        await callback.answer("❌ Testni o'chirib bo'lmadi.", show_alert=True)


# --- Delete Course from Tests List ---
@router.callback_query(F.data.startswith("admin_course_delete_from_list_"))
async def admin_course_delete_from_list_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[5])
    course_page = int(parts[7])
    
    success = db.delete_course(course_id)
    if success:
        await callback.answer("✅ Kurs va uning ichidagi barcha testlar o'chirildi!", show_alert=True)
        courses = db.get_all_courses()
        text, kb = get_courses_list_page(courses, page=course_page)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
    else:
        await callback.answer("❌ Kursni o'chirib bo'lmadi.", show_alert=True)
