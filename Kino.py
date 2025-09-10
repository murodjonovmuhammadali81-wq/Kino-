import telebot
from telebot import types
import json
import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo   # Toshkent vaqti uchun

# --- SOZLAMALAR ---
TOKEN = "7726285360:AAHhFsbdW_UPBWI_RIuzHnx4K5Dp63i4vRw"
CHANNEL_ID = "@kinofvf"
ADMIN_ID = 7134233049   # ✅ Sening ID'ing

DB_FILE = "films.json"
USERS_FILE = "users.json"
STATS_FILE = "stats.json"

bot = telebot.TeleBot(TOKEN)

# --- JSON yordamchi ---
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Fayllar ---
films = load_json(DB_FILE, {})
users = load_json(USERS_FILE, [])
stats = load_json(STATS_FILE, {"views": {}, "starts": 0, "last": [], "user_views": {}})

# --- Agar fayllar bo'lmasa yaratamiz ---
if not os.path.exists(DB_FILE):
    save_json(DB_FILE, {})
if not os.path.exists(USERS_FILE):
    save_json(USERS_FILE, [])
if not os.path.exists(STATS_FILE):
    save_json(STATS_FILE, {"views": {}, "starts": 0, "last": [], "user_views": {}})

# --- Obuna tekshirish ---
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# --- /start ---
@bot.message_handler(commands=['start'])
def start_message(message):
    uid = message.from_user.id
    uname = message.from_user.username or f"id{uid}"

    if not any(u["id"] == uid for u in users):
        users.append({
            "id": uid,
            "username": uname,
            "joined": datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")
        })
        save_json(USERS_FILE, users)

    stats["starts"] += 1
    save_json(STATS_FILE, stats)

    if is_subscribed(uid):
        bot.send_message(message.chat.id, "✅ Obuna uchun rahmat!\n🎬 Kino kodini yuboring")
    else:
        keyboard = types.InlineKeyboardMarkup()
        btn_sub = types.InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_ID[1:]}")
        btn_check = types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")
        keyboard.add(btn_sub)
        keyboard.add(btn_check)
        bot.send_message(
            message.chat.id,
            "❌ Botdan foydalanish uchun kanalga obuna bo‘ling:",
            reply_markup=keyboard
        )

# --- Inline tugma obunani tekshirish ---
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        bot.send_message(call.message.chat.id, "🎬 Kino kodini yuboring")
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali obuna bo‘lmadingiz!")

# --- Admin: video yuborilganda file_id saqlash ---
@bot.message_handler(content_types=['video'])
def save_video(message):
    uid = message.from_user.id

    if uid != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Faqat admin kino qo‘sha oladi.")
        return

    file_id = message.video.file_id

    bot.send_message(
        message.chat.id,
        f"🎬 Video qabul qilindi!\n📌 File ID: `{file_id}`\n\n❓ Ushbu video uchun kod yuboring:",
        parse_mode="Markdown"
    )

    bot.register_next_step_handler(message, lambda msg: save_code(msg, file_id))

def save_code(message, file_id):
    code = message.text.strip()
    films[code] = file_id
    save_json(DB_FILE, films)

    bot.send_message(
        message.chat.id,
        f"✅ Kino qo‘shildi!\n🔑 Kod: {code}\n🎬 File ID: `{file_id}`",
        parse_mode="Markdown"
    )

# --- Admin: statistika ---
@bot.message_handler(commands=['stats'])
def stats_handler(message):
    if message.from_user.id == ADMIN_ID:
        total_users = len(users)
        total_starts = stats.get("starts", 0)
        views = stats.get("views", {})
        user_views = stats.get("user_views", {})
        last = stats.get("last", [])

        top = Counter(views).most_common(5)
        top_text = "\n".join([f"🔑 {c}: {v} marta" for c, v in top]) if top else "📭 Hali ko‘rilmagan"

        last_text = "\n".join([f"👤 {l['user']} → {l['code']}" for l in last[-5:]]) if last else "📭 Ma’lumot yo‘q"

        last_user_info = users[-1] if users else None
        if last_user_info:
            joined_info = f"🕐 Oxirgi foydalanuvchi: {last_user_info['username']} ({last_user_info['joined']} | Toshkent)"
        else:
            joined_info = "🕐 Hali foydalanuvchilar yo‘q"

        if user_views:
            top_users = Counter(user_views).most_common(3)
            active_info = "🔥 Eng faol foydalanuvchilar:\n" + "\n".join([
                f"{i+1}. {next((u['username'] for u in users if u['id'] == int(uid)), f'id{uid}')} ({count} ta kino)"
                for i, (uid, count) in enumerate(top_users)
            ])
        else:
            active_info = "🔥 Hali faol foydalanuvchilar yo‘q"

        text = (
            f"📊 *Statistika*\n\n"
            f"👥 Foydalanuvchilar: {total_users}\n"
            f"{joined_info}\n"
            f"▶️ /start bosganlar: {total_starts}\n\n"
            f"{active_info}\n\n"
            f"🎬 Eng mashhur 5 kod:\n{top_text}\n\n"
            f"🕐 Oxirgi 5 faoliyat:\n{last_text}"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz.")

# --- Foydalanuvchi: kod orqali kino olish ---
@bot.message_handler(func=lambda message: message.content_type == "text")
def film_code_handler(message):
    uid = message.from_user.id
    uname = message.from_user.username or f"id{uid}"
    code = message.text.strip()

    if not is_subscribed(uid):
        return start_message(message)

    if code in films:
        file_id = films[code]
        stats["views"][code] = stats["views"].get(code, 0) + 1
        stats["user_views"][str(uid)] = stats["user_views"].get(str(uid), 0) + 1

        stats.setdefault("last", [])
        stats["last"].append({"user": uname, "code": code})
        if len(stats["last"]) > 50:
            stats["last"] = stats["last"][-50:]

        save_json(STATS_FILE, stats)
        bot.send_video(message.chat.id, file_id)
    else:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri kod. Qayta urinib ko‘ring.")

# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.polling(none_stop=True)