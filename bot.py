import os
import time
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Setup Logging agar kita bisa lihat error di Railway Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BASE_URL = "https://api.mail.tm"

# --- FUNGSI HELPER MAIL.TM ---
def get_domains():
    try:
        res = requests.get(f"{BASE_URL}/domains").json()
        return res['hydra:member'][0]['domain']
    except Exception as e:
        logging.error(f"Error get domain: {e}")
        return None

# --- HANDLER BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ **Bot Temporary Email** ✨\n\n"
        "Gunakan bot ini untuk menerima email tanpa ribet.\n"
        "Klik tombol di bawah untuk membuat email baru."
    )
    keyboard = [[InlineKeyboardButton("📧 Generate Email", callback_data="gen_email")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "gen_email":
        domain = get_domains()
        if not domain:
            await query.edit_message_text("❌ Gagal mengambil domain. Coba lagi.")
            return

        user_id = query.from_user.id
        # Buat username unik
        username = f"user{user_id}{int(time.time())}"[-15:]
        email = f"{username}@{domain}"
        password = "password123"

        # Daftar Akun
        reg = requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
        
        if reg.status_code == 201:
            # Ambil Token
            token_res = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()
            token = token_res['token']
            
            # Simpan data sementara di user_data
            context.user_data['email'] = email
            context.user_data['token'] = token

            msg = (
                f"✅ **Email Berhasil Dibuat!**\n\n"
                f"📧 ` {email} `\n"
                f"🔑 Password: `{password}`\n\n"
                "Menunggu email masuk... Klik refresh jika sudah mengirim email."
            )
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_inbox")],
                [InlineKeyboardButton("🆕 Buat Email Baru", callback_data="gen_email")]
            ]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Gagal mendaftar. Coba lagi.")

    elif query.data == "check_inbox":
        token = context.user_data.get('token')
        if not token:
            await query.message.reply_text("Silakan buat email dulu!")
            return

        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/messages", headers=headers).json()
        messages = res.get('hydra:member', [])

        if not messages:
            await query.message.reply_text("📭 Belum ada email masuk.")
        else:
            for m in messages[:3]: # Tampilkan 3 email terakhir
                m_id = m['id']
                detail = requests.get(f"{BASE_URL}/messages/{m_id}", headers=headers).json()
                
                info = (
                    f"📩 **Pesan Masuk**\n"
                    f"Dari: {m['from']['address']}\n"
                    f"Subjek: {m['subject']}\n"
                    f"---\n{detail['text']}"
                )
                await query.message.reply_text(info)

# --- EKSEKUSI UTAMA ---
def main():
    # Ambil token dari Environment Variable di Railway
    token_bot = os.getenv("BOT_TOKEN")

    if not token_bot:
        print("ERROR: BOT_TOKEN tidak ditemukan di Variable Railway!")
        return

    # Inisialisasi Aplikasi (v20+)
    app = Application.builder().token(token_bot).build()

    # Tambahkan Handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("Bot sedang berjalan...")
    app.run_polling()

if __name__ == '__main__':
    main()
