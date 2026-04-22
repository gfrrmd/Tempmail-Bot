import os
import time
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BASE_URL = "https://api.mail.tm"

def get_domain():
    res = requests.get(f"{BASE_URL}/domains").json()
    return res['hydra:member'][0]['domain']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📧 **Temp Mail Pro**\nKlik tombol di bawah untuk membuat email baru."
    btns = [[InlineKeyboardButton("🆕 Generate Email Baru", callback_data="gen")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # FUNGSI GENERATE EMAIL
    if query.data == "gen":
        domain = get_domain()
        user = f"mail{int(time.time())}"[-10:]
        email = f"{user}@{domain}"
        password = "password123"

        # Daftar & Ambil Token
        requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
        token_res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()
        
        context.user_data['email'] = email
        context.user_data['token'] = token_res['token']

        msg = f"✅ **Email Aktif:**\n`{email}`\n\nMenunggu email masuk..."
        btns = [[InlineKeyboardButton("🔄 Refresh Inbox", callback_data="refresh")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

    # FUNGSI REFRESH & LIST SUBJECT DI TOMBOL
    elif query.data == "refresh":
        token = context.user_data.get('token')
        email = context.user_data.get('email')
        if not token: return

        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages", headers=headers).json()
        messages = res.get('hydra:member', [])

        btns = []
        if not messages:
            msg = f"📧 **Alamat:** `{email}`\n\n📭 Inbox masih kosong. Belum ada email masuk."
        else:
            msg = f"📧 **Alamat:** `{email}`\n\n🔎 **Pilih email di bawah untuk membaca:**"
            # Ambil maksimal 3 email terbaru untuk jadi tombol
            for m in messages[:3]:
                subject = m['subject'] or "(No Subject)"
                # Tombol berisi subjek email
                btns.append([InlineKeyboardButton(f"📩 {subject}", callback_data=f"read_{m['id']}")])
        
        # Tambahkan tombol kontrol di bawah list subjek
        btns.append([InlineKeyboardButton("🔄 Refresh Lagi", callback_data="refresh")])
        btns.append([InlineKeyboardButton("🆕 Ganti Email", callback_data="gen")])
        
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

    # FUNGSI BACA ISI EMAIL
    elif query.data.startswith("read_"):
        msg_id = query.data.replace("read_", "")
        token = context.user_data.get('token')
        headers = {"Authorization": f"Bearer {token}"}
        
        # Ambil detail
        detail = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers).json()
        isi = detail.get('text') or "Isi pesan kosong atau hanya format HTML."
        
        full_text = (
            f"📧 **Detail Email**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 **Dari:** {detail['from']['address']}\n"
            f"📝 **Subjek:** {detail['subject']}\n\n"
            f"📄 **Isi:**\n{isi[:3800]}"
        )
        
        # Tombol kembali ke list
        btns = [[InlineKeyboardButton("⬅️ Kembali ke List", callback_data="refresh")]]
        await query.edit_message_text(full_text, reply_markup=InlineKeyboardMarkup(btns))

if __name__ == '__main__':
    token_bot = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token_bot).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
