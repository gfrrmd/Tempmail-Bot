import os
import time
import requests
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging untuk melihat error di Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BASE_URL = "https://api.mail.tm"

def get_domains():
    try:
        res = requests.get(f"{BASE_URL}/domains", timeout=10).json()
        return res['hydra:member'][0]['domain']
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👋 **Temp Mail Bot**\nKlik tombol untuk buat email."
    keyboard = [[InlineKeyboardButton("📧 Generate Email", callback_data="gen_email")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "gen_email":
        domain = get_domains()
        if not domain:
            await query.edit_message_text("❌ Domain tidak tersedia.")
            return

        user_id = query.from_user.id
        username = f"u{user_id}{int(time.time())}"[-15:]
        email = f"{username}@{domain}"
        password = "pass_user_123"

        reg = requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
        
        if reg.status_code == 201:
            token_res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()
            context.user_data['email'] = email
            context.user_data['token'] = token_res['token']

            msg = f"✅ **Email Dibuat!**\n\n`{email}`\n\nKlik Refresh untuk cek pesan."
            btns = [[InlineKeyboardButton("🔄 Refresh", callback_data="check_inbox")]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Gagal daftar akun.")

    elif query.data == "check_inbox":
        token = context.user_data.get('token')
        if not token:
            await query.message.reply_text("Buat email dulu!")
            return

        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages", headers=headers).json()
        messages = res.get('hydra:member', [])

        if not messages:
            await query.message.reply_text("📭 Inbox kosong.")
        else:
            for m in messages[:2]:
                m_id = m['id']
                detail = requests.get(f"{BASE_URL}/messages/{m_id}", headers=headers).json()
                await query.message.reply_text(f"📩 **Dari:** {m['from']['address']}\n**Subjek:** {m['subject']}\n\n{detail['text']}")

if __name__ == '__main__':
    token_bot = os.getenv("BOT_TOKEN")
    if not token_bot:
        print("Variable BOT_TOKEN kosong!")
    else:
        # Inisialisasi v21.x
        app = Application.builder().token(token_bot).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_buttons))
        print("Bot Aktif...")
        app.run_polling(drop_pending_updates=True)
