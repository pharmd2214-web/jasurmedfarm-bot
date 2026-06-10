"""
MedPlus Dorixona Telegram Boti
================================
Har 10 000 so'mga 1 bonus ball
100 ball = 10 000 so'm chegirma

Ishga tushirish:
  pip install python-telegram-bot==20.7
  python bot.py
"""

import os
import json
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)
import database as db

# ── SOZLAMALAR ─────────────────────────────────────
BOT_TOKEN   = "7984875283:AAEXJB6fIf8Mxawq62NReS1d9zThv83SEug"
ADMIN_IDS   = [8113695466]          # Admin Telegram ID'larini shu yerga kiriting
BALL_RATE   = 10_000               # Har necha so'mga 1 ball
BALL_VALUE  = 100                  # 1 ball = necha so'm

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── CONVERSATION STATES ────────────────────────────
(
    REGISTER_NAME, REGISTER_PHONE, REGISTER_ADDRESS,
    SEARCH_QUERY,
    CART_QTY,
    ORDER_ADDRESS, ORDER_BALLS,
    ADMIN_STATUS
) = range(8)

# ── YORDAMCHI: savat ───────────────────────────────
def get_cart(context) -> dict:
    return context.user_data.setdefault("cart", {})

def cart_total(cart: dict) -> int:
    total = 0
    for med_id, item in cart.items():
        total += item["price"] * item["qty"]
    return total

def cart_text(cart: dict) -> str:
    if not cart:
        return "🛒 Savat bo'sh"
    lines = ["🛒 *Savatingiz:*\n"]
    total = 0
    for med_id, item in cart.items():
        subtotal = item["price"] * item["qty"]
        total += subtotal
        lines.append(f"• {item['name']} × {item['qty']} = {subtotal:,} so'm")
    lines.append(f"\n💰 *Jami: {total:,} so'm*")
    lines.append(f"⭐ Yig'iladigan ball: *{total // BALL_RATE}*")
    return "\n".join(lines)

def balls_to_discount(balls: int) -> int:
    return balls * BALL_VALUE

# ── ASOSIY MENYU ───────────────────────────────────
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["💊 Dorilar katalogi", "🔍 Dori qidirish"],
        ["🛒 Savat",            "📋 Buyurtmalarim"],
        ["⭐ Bonus ballarim",   "👤 Profilim"],
        ["📞 Aloqa",            "ℹ️ Yordam"],
    ], resize_keyboard=True)

async def send_main_menu(update: Update, text: str):
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ── /start ─────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if user:
        await send_main_menu(update,
            f"👋 Xush kelibsiz, *{user['full_name']}*!\n"
            f"⭐ Ballaringiz: *{user['balls']} ball*\n\n"
            "Nima buyurasiz?"
        )
    else:
        await update.message.reply_text(
            "🏥 *MedPlus Dorixona Botiga xush kelibsiz!*\n\n"
            "Dori buyurtma bering, uyingizga yetkazamiz.\n"
            "Har *10 000 so'm* xariddan *1 bonus ball* yig'asiz!\n\n"
            "Ro'yxatdan o'tish uchun *ismingizni* yuboring:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return REGISTER_PHONE

async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    context.user_data["reg_phone"] = phone
    await update.message.reply_text(
        "🏠 Yetkazib berish manzilingizni kiriting:\n"
        "_(Tuman, ko'cha, uy raqami)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return REGISTER_ADDRESS

async def register_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    full_name = context.user_data.get("reg_name", update.effective_user.full_name)
    phone     = context.user_data.get("reg_phone", "")
    address   = update.message.text.strip()

    db.create_user(user_id, full_name)
    db.update_user_field(user_id, "phone",   phone)
    db.update_user_field(user_id, "address", address)

    await send_main_menu(update,
        f"✅ Ro'yxatdan o'tdingiz!\n\n"
        f"👤 Ism: *{full_name}*\n"
        f"📱 Tel: {phone}\n"
        f"🏠 Manzil: {address}\n\n"
        "Endi dori buyurtma bera olasiz! 💊"
    )
    return ConversationHandler.END

# ── KATALOG ────────────────────────────────────────
async def show_catalogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meds = db.get_all_medicines()
    if not meds:
        await update.message.reply_text("😔 Hozircha dorilar mavjud emas.")
        return

    # Kategoriyalar bo'yicha guruhlash
    categories = {}
    for m in meds:
        cat = m["category"] or "Boshqa"
        categories.setdefault(cat, []).append(m)

    for cat, items in categories.items():
        buttons = []
        for m in items:
            buttons.append([InlineKeyboardButton(
                f"💊 {m['name']} — {m['price']:,} so'm",
                callback_data=f"med_{m['id']}"
            )])

        await update.message.reply_text(
            f"📂 *{cat}*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

# ── DORI QIDIRISH ──────────────────────────────────
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Dori nomini kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SEARCH_QUERY

async def search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    results = db.search_medicines(query)

    if not results:
        await update.message.reply_text(
            f"😔 *'{query}'* bo'yicha hech narsa topilmadi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(
        f"💊 {m['name']} — {m['price']:,} so'm",
        callback_data=f"med_{m['id']}"
    )] for m in results]

    await update.message.reply_text(
        f"🔍 *'{query}'* bo'yicha natijalar:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    await update.message.reply_text("Asosiy menyu:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

# ── DORI DETAIL ────────────────────────────────────
async def med_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    med_id = int(query.data.split("_")[1])
    m = db.get_medicine(med_id)
    if not m:
        await query.edit_message_text("❌ Dori topilmadi.")
        return

    text = (
        f"💊 *{m['name']}*\n"
        f"📂 Kategoriya: {m['category']}\n"
        f"💰 Narx: *{m['price']:,} so'm* / {m['unit']}\n"
        f"📦 Mavjud: {m['stock']} {m['unit']}\n"
        f"📝 {m['description']}\n\n"
        f"⭐ Bu dori uchun: *{m['price'] // BALL_RATE} ball* yig'asiz"
    )
    buttons = [
        [
            InlineKeyboardButton("➕ Savatga qo'shish", callback_data=f"add_{med_id}"),
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_catalogue")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    med_id = int(query.data.split("_")[1])
    m = db.get_medicine(med_id)
    if not m:
        return

    cart = get_cart(context)
    key  = str(med_id)
    if key in cart:
        if cart[key]["qty"] < m["stock"]:
            cart[key]["qty"] += 1
    else:
        cart[key] = {"name": m["name"], "price": m["price"], "qty": 1}

    total = cart_total(cart)
    await query.edit_message_text(
        f"✅ *{m['name']}* savatga qo'shildi!\n\n"
        f"{cart_text(cart)}\n\n"
        f"Davom etishingiz mumkin.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Savatni ko'rish",  callback_data="show_cart")],
            [InlineKeyboardButton("💊 Yana dori qo'shish", callback_data="back_catalogue")]
        ]),
        parse_mode="Markdown"
    )

# ── SAVAT ──────────────────────────────────────────
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = get_cart(context)
    msg  = cart_text(cart)

    buttons = []
    if cart:
        buttons = [
            [InlineKeyboardButton("✅ Buyurtma berish", callback_data="checkout")],
            [InlineKeyboardButton("🗑 Savatni tozalash",  callback_data="clear_cart")],
        ]
    else:
        buttons = [[InlineKeyboardButton("💊 Katalogga o'tish", callback_data="back_catalogue")]]

    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cart"] = {}
    await update.callback_query.answer("Savat tozalandi ✓")
    await update.callback_query.edit_message_text("🛒 Savat bo'shatildi.")

# ── CHECKOUT ───────────────────────────────────────
async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = get_cart(context)
    if not cart:
        await query.edit_message_text("🛒 Savat bo'sh!")
        return ConversationHandler.END

    user = db.get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ Avval /start orqali ro'yxatdan o'ting.")
        return ConversationHandler.END

    context.user_data["checkout_user"] = user
    saved_address = user.get("address", "")

    buttons = []
    if saved_address:
        buttons.append([InlineKeyboardButton(
            f"📍 Saqlangan: {saved_address[:40]}",
            callback_data="use_saved_address"
        )])
    buttons.append([InlineKeyboardButton("✏️ Yangi manzil kiritish", callback_data="new_address")])

    await query.edit_message_text(
        f"{cart_text(cart)}\n\n📍 Yetkazib berish manzilini tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ORDER_ADDRESS

async def use_saved_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = context.user_data["checkout_user"]
    context.user_data["order_address"] = user["address"]
    return await _ask_balls(update, context)

async def new_address_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🏠 Yetkazib berish manzilini kiriting:")
    return ORDER_ADDRESS

async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_address"] = update.message.text.strip()
    return await _ask_balls(update, context, via_message=True)

async def _ask_balls(update, context, via_message=False):
    user  = context.user_data["checkout_user"]
    cart  = get_cart(context)
    total = cart_total(cart)
    balls = user.get("balls", 0)

    if balls >= 100:
        max_discount = balls_to_discount(balls)
        text = (
            f"⭐ Sizda *{balls} ball* bor ({max_discount:,} so'm chegirma)\n\n"
            f"💰 Jami to'lov: *{total:,} so'm*\n\n"
            f"Nechta ball ishlatmoqchisiz? (0 dan {balls} gacha)\n"
            f"_(Har 1 ball = {BALL_VALUE} so'm chegirma)_"
        )
        buttons = [
            [InlineKeyboardButton(f"⭐ Barchasini ishlatish ({balls} ball)", callback_data=f"balls_{balls}")],
            [InlineKeyboardButton("⏩ Balllarsiz davom etish", callback_data="balls_0")],
        ]
        if via_message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        context.user_data["balls_used"] = 0
        return await _confirm_order(update, context, via_message)

    return ORDER_BALLS

async def receive_balls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    balls_used = int(query.data.split("_")[1])
    user = context.user_data["checkout_user"]
    balls_used = min(balls_used, user["balls"])
    context.user_data["balls_used"] = balls_used
    return await _confirm_order(update, context)

async def _confirm_order(update, context, via_message=False):
    cart       = get_cart(context)
    total      = cart_total(cart)
    balls_used = context.user_data.get("balls_used", 0)
    discount   = balls_to_discount(balls_used)
    final      = max(0, total - discount)
    earned     = final // BALL_RATE
    address    = context.user_data.get("order_address", "—")

    text = (
        f"📋 *Buyurtma tasdiqlash*\n\n"
        f"{cart_text(cart)}\n\n"
        f"📍 Manzil: {address}\n"
        f"{'⭐ Chegirma: ' + str(balls_used) + ' ball = ' + str(discount) + ' som' + chr(10) if balls_used else ''}"
        f"💳 To'lanadigan summa: *{final:,} so'm*\n"
        f"🎁 Yig'iladigan ball: *+{earned} ball*\n\n"
        f"Yetkazib berish: *30–60 daqiqa*"
    )
    buttons = [
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_order")],
    ]
    if via_message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    return ORDER_BALLS

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cart       = get_cart(context)
    total      = cart_total(cart)
    balls_used = context.user_data.get("balls_used", 0)
    discount   = balls_to_discount(balls_used)
    final      = max(0, total - discount)
    earned     = final // BALL_RATE
    address    = context.user_data.get("order_address", "—")

    items_str = json.dumps(
        [{"name": v["name"], "qty": v["qty"], "price": v["price"]} for v in cart.values()],
        ensure_ascii=False
    )

    order_id = db.create_order(
        user_id, items_str, final, discount, balls_used, earned, address
    )

    # Zahira kamaytirish
    for med_id, item in cart.items():
        db.reduce_stock(int(med_id), item["qty"])

    # Ball hisoblash
    if balls_used > 0:
        db.use_balls(user_id, balls_used)
    db.add_balls(user_id, earned, final)

    # Savatni tozalash
    context.user_data["cart"] = {}

    user = db.get_user(user_id)

    await query.edit_message_text(
        f"🎉 *Buyurtma #{order_id} qabul qilindi!*\n\n"
        f"📍 Manzil: {address}\n"
        f"💰 Summa: {final:,} so'm\n"
        f"⭐ Yangi ballingiz: *{user['balls']} ball*\n\n"
        f"⏰ Yetkazib berish: 30–60 daqiqa\n"
        f"📞 Muammo bo'lsa: +998 71 123 45 67",
        parse_mode="Markdown"
    )

    # Adminlarga xabar
    items_readable = "\n".join([f"• {v['name']} × {v['qty']}" for v in cart.values()])
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🔔 *Yangi buyurtma #{order_id}*\n\n"
                f"👤 Mijoz: {user['full_name']} (ID: {user_id})\n"
                f"📱 Tel: {user.get('phone','—')}\n"
                f"📍 Manzil: {address}\n\n"
                f"💊 Dorilar:\n{items_readable}\n\n"
                f"💰 Jami: {final:,} so'm\n"
                f"⭐ Ball ishlatildi: {balls_used}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Qabul qilindi", callback_data=f"admin_accept_{order_id}")],
                    [InlineKeyboardButton("🚚 Yetkazildi",    callback_data=f"admin_done_{order_id}")],
                    [InlineKeyboardButton("❌ Bekor qilish",  callback_data=f"admin_cancel_{order_id}")],
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            log.warning(f"Admin xabari yuborilmadi: {e}")

    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Bekor qilindi")
    await update.callback_query.edit_message_text("❌ Buyurtma bekor qilindi.")
    return ConversationHandler.END

# ── ADMIN PANEL ────────────────────────────────────
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    parts     = query.data.split("_")
    action    = parts[1]
    order_id  = int(parts[2])

    status_map = {"accept": "qabul qilindi", "done": "yetkazildi", "cancel": "bekor qilindi"}
    status = status_map.get(action, "noma'lum")
    db.update_order_status(order_id, status)

    emoji = {"accept": "✅", "done": "🚚", "cancel": "❌"}.get(action, "")
    await query.edit_message_text(
        query.message.text + f"\n\n{emoji} *Holat: {status}*",
        parse_mode="Markdown"
    )
    await query.answer(f"Buyurtma #{order_id}: {status}")

# ── PROFIL ─────────────────────────────────────────
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Avval /start bosing.")
        return

    discount_available = balls_to_discount(user["balls"])
    await update.message.reply_text(
        f"👤 *Profilingiz*\n\n"
        f"📛 Ism: {user['full_name']}\n"
        f"📱 Tel: {user.get('phone','—')}\n"
        f"🏠 Manzil: {user.get('address','—')}\n\n"
        f"⭐ Ball: *{user['balls']} ball*\n"
        f"💰 Chegirma: *{discount_available:,} so'm*\n"
        f"🛒 Jami xarid: {user['total_spent']:,} so'm",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ── BONUS ──────────────────────────────────────────
async def show_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ Avval /start bosing.")
        return

    balls   = user["balls"]
    disc    = balls_to_discount(balls)
    next_b  = BALL_RATE - (user["total_spent"] % BALL_RATE)

    await update.message.reply_text(
        f"⭐ *Bonus tizimi*\n\n"
        f"Sizda: *{balls} ball* = *{disc:,} so'm* chegirma\n\n"
        f"📊 *Qoidalar:*\n"
        f"• Har {BALL_RATE:,} so'm xariddan → *1 ball*\n"
        f"• 1 ball = *{BALL_VALUE} so'm* chegirma\n"
        f"• Keyingi ball uchun: *{next_b:,} so'm* xarid qiling\n\n"
        f"💡 Ballarni buyurtma berishda ishlatishingiz mumkin!",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ── BUYURTMALAR TARIXI ─────────────────────────────
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = db.get_user_orders(update.effective_user.id)
    if not orders:
        await update.message.reply_text(
            "📋 Hali buyurtma bermagansiz.",
            reply_markup=main_menu_keyboard()
        )
        return

    status_emoji = {
        "yangi": "🆕", "qabul qilindi": "✅",
        "yetkazildi": "🚚", "bekor qilindi": "❌"
    }
    text = "📋 *So'nggi buyurtmalaringiz:*\n\n"
    for o in orders:
        emoji  = status_emoji.get(o["status"], "❓")
        date   = o["created_at"][:16]
        text  += f"{emoji} *#{o['id']}* — {o['total']:,} so'm — {o['status']}\n"
        text  += f"   📅 {date}\n\n"

    await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ── ALOQA & YORDAM ─────────────────────────────────
async def show_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Aloqa*\n\n"
        "☎️ Tel: +998 71 123 45 67\n"
        "📱 Telegram: @medplus_uz\n"
        "🕐 Ish vaqti: 08:00–22:00\n"
        "📍 Toshkent sh., Chilonzor tumani",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Yordam*\n\n"
        "1️⃣ *Dori buyurtma:* Katalog → Dori tanlang → Savatga → Buyurtma bering\n"
        "2️⃣ *Qidiruv:* 'Dori qidirish' → Nomi yozing\n"
        "3️⃣ *Bonus:* Har 10 000 so'mga 1 ball yig'asiz\n"
        "4️⃣ *Chegirma:* Checkout vaqtida ballarni ishlating\n\n"
        "❓ Savolingiz bo'lsa: 📞 +998 71 123 45 67",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def back_catalogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    meds = db.get_all_medicines()
    buttons = [[InlineKeyboardButton(
        f"💊 {m['name']} — {m['price']:,} so'm",
        callback_data=f"med_{m['id']}"
    )] for m in meds]
    await update.callback_query.edit_message_text(
        "💊 *Dorilar katalogi:*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ── NOMA'LUM XABAR ────────────────────────────────
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "katalog" in text.lower() or "dorilar" in text.lower():
        await show_catalogue(update, context)
    elif "savat" in text.lower():
        await show_cart(update, context)
    elif "profil" in text.lower():
        await show_profile(update, context)
    elif "bonus" in text.lower() or "ball" in text.lower():
        await show_bonus(update, context)
    elif "buyurtma" in text.lower():
        await show_orders(update, context)
    elif "aloqa" in text.lower():
        await show_contact(update, context)
    elif "yordam" in text.lower():
        await show_help(update, context)
    else:
        await update.message.reply_text(
            "Tushunmadim 🤔 Quyidagi menyudan tanlang:",
            reply_markup=main_menu_keyboard()
        )

# ── MAIN ───────────────────────────────────────────
def main():
    db.init_db()
    log.info("✅ Ma'lumotlar bazasi tayyor.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Ro'yxatdan o'tish
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REGISTER_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_PHONE:   [
                MessageHandler(filters.CONTACT, register_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone),
            ],
            REGISTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_address)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )

    # Qidiruv
    search_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🔍 Dori qidirish"), search_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_execute)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )

    # Checkout
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            ORDER_ADDRESS: [
                CallbackQueryHandler(use_saved_address, pattern="^use_saved_address$"),
                CallbackQueryHandler(new_address_prompt, pattern="^new_address$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
            ],
            ORDER_BALLS: [
                CallbackQueryHandler(receive_balls, pattern="^balls_"),
                CallbackQueryHandler(confirm_order, pattern="^confirm_order$"),
                CallbackQueryHandler(cancel_order,  pattern="^cancel_order$"),
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )

    app.add_handler(reg_conv)
    app.add_handler(search_conv)
    app.add_handler(checkout_conv)

    # Inline tugmalar
    app.add_handler(CallbackQueryHandler(med_detail,      pattern="^med_"))
    app.add_handler(CallbackQueryHandler(add_to_cart,     pattern="^add_"))
    app.add_handler(CallbackQueryHandler(show_cart,       pattern="^show_cart$"))
    app.add_handler(CallbackQueryHandler(clear_cart,      pattern="^clear_cart$"))
    app.add_handler(CallbackQueryHandler(back_catalogue,  pattern="^back_catalogue$"))
    app.add_handler(CallbackQueryHandler(admin_action,    pattern="^admin_"))

    # Menyu tugmalari
    app.add_handler(MessageHandler(filters.Regex("💊 Dorilar katalogi"), show_catalogue))
    app.add_handler(MessageHandler(filters.Regex("🛒 Savat"),            show_cart))
    app.add_handler(MessageHandler(filters.Regex("📋 Buyurtmalarim"),    show_orders))
    app.add_handler(MessageHandler(filters.Regex("⭐ Bonus ballarim"),   show_bonus))
    app.add_handler(MessageHandler(filters.Regex("👤 Profilim"),         show_profile))
    app.add_handler(MessageHandler(filters.Regex("📞 Aloqa"),            show_contact))
    app.add_handler(MessageHandler(filters.Regex("ℹ️ Yordam"),           show_help))

    # Boshqa xabarlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    log.info("🤖 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
