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
    waiting_for_course_name = State()
    waiting_for_course_url = State()
    waiting_for_course_edit_url = State()

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


# --- helper tools for Courses Management ---
def get_courses_list_page(courses: list[dict], page: int, limit: int = 10) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates a text list of courses for a specific page with selection, addition, and navigation buttons."""
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
        url_status = f"<code>{c['webapp_url']}</code>" if c['webapp_url'] else "❌ Havola yo'q"
        text += f"<b>{index}. {c['name']}</b>\n   🔗 Havola: {url_status}\n\n"
        
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
    action_kb.button(text="➕ Kurs qo'shish", callback_data="admin_course_add_auto")
    action_kb.button(text="⬅️ Admin panelga qaytish", callback_data="admin_panel_menu")
    action_kb.adjust(1)
    
    selection_kb.attach(pagination_kb)
    selection_kb.attach(action_kb)
    return text, selection_kb.as_markup()

def get_course_card(idx: int, c: dict, page: int) -> tuple[str, types.InlineKeyboardMarkup]:
    """Generates the detailed card text and action buttons for a single course."""
    text = (
        f"📚 <b>Kurs #{idx} Tafsilotlari</b>\n\n"
        f"• Nomi: <b>{c['name']}</b>\n"
        f"• Havola: <code>{c['webapp_url'] or 'Kiritilmagan'}</code>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Havolani tahrirlash", callback_data=f"admin_course_edit_url_{c['id']}_{idx}_{page}")
    kb.button(text="❌ Kursni o'chirish", callback_data=f"admin_course_delete_{c['id']}_{idx}_{page}")
    kb.button(text="⬅️ Orqaga", callback_data=f"admin_course_page_{page}")
    kb.adjust(2, 1)
    return text, kb.as_markup()


# --- Courses View callbacks & handlers ---
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

@router.callback_query(F.data.startswith("admin_course_manage_"))
async def course_manage_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[3])
    idx = int(parts[4])
    page = int(parts[5])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    if not c:
        return await callback.answer("Kurs topilmadi!", show_alert=True)
        
    text, kb = get_course_card(idx, c, page)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_course_add_auto")
async def admin_course_add_auto_callback(callback: types.CallbackQuery, state: FSMContext):
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
    
    await state.update_data(course_name=course_name)
    await state.set_state(AdminStates.waiting_for_course_url)
    
    await callback.message.answer(
        f"➕ <b>Yangi kurs qo'shish:</b>\n\n"
        f"📚 Nomi: <b>{course_name}</b>\n\n"
        f"Iltimos, ushbu yangi kurs uchun test/webapp havolasini yuboring:\n"
        f"Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_course_url)
async def process_course_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Kurs qo'shish bekor qilindi.")
        return
        
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("⚠️ Noto'g'ri URL manzili formati (http:// yoki https:// bilan boshlanishi kerak). Qayta urinib ko'ring:")
        return
        
    data = await state.get_data()
    course_name = data["course_name"]
    
    success = db.add_course(name=course_name, description=f"{course_name} darslari va materiallari", webapp_url=url)
    await state.clear()
    
    if success:
        await message.answer(
            f"🎉 <b>Kurs muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📚 Nomi: {course_name}\n"
            f"🔗 Havola: {url}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Xatolik yuz berdi. Ushbu nomli kurs allaqachon mavjud bo'lishi mumkin.")

@router.callback_query(F.data.startswith("admin_course_edit_url_"))
async def admin_course_edit_url_callback(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[4])
    idx = int(parts[5])
    page = int(parts[6])
    
    courses = db.get_all_courses()
    c = next((item for item in courses if item["id"] == course_id), None)
    if not c:
        return await callback.answer("Kurs topilmadi!", show_alert=True)
        
    await state.set_state(AdminStates.waiting_for_course_edit_url)
    await state.update_data(edit_course_id=course_id, edit_idx=idx, edit_page=page)
    
    await callback.message.answer(
        f"🔗 <b>{c['name']} havolasini tahrirlash</b>\n\n"
        f"Iltimos, ushbu kurs uchun yangi test havolasini yuboring:\n"
        f"Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_course_edit_url)
async def process_course_edit_url(message: types.Message, state: FSMContext):
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
    course_id = data["edit_course_id"]
    
    success = db.update_course_url(course_id, url)
    await state.clear()
    
    if success:
        await message.answer("✅ <b>Kurs havolasi muvaffaqiyatli yangilandi!</b>", parse_mode="HTML")
    else:
        await message.answer("❌ Havolani yangilashda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("admin_course_delete_"))
async def admin_course_delete_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)
        
    parts = callback.data.split("_")
    course_id = int(parts[3])
    idx = int(parts[4])
    page = int(parts[5])
    
    success = db.delete_course(course_id)
    if success:
        await callback.answer("✅ Kurs o'chirildi!", show_alert=True)
        courses = db.get_all_courses()
        text, kb = get_courses_list_page(courses, page=page)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
    else:
        await callback.answer("❌ Kursni o'chirib bo'lmadi.", show_alert=True)


