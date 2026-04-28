"""
api/notify.py
══════════════════════════════════════════════════
  Vercel Serverless Function
  Supabase Webhook → Telegram уведомление

  Supabase вызывает POST https://your-site.vercel.app/api/notify
  каждый раз когда в таблицу bookings добавляется новая запись.
══════════════════════════════════════════════════
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import datetime
from supabase import create_client

BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "")
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")
# Секретный ключ для защиты endpoint (задайте в Vercel и Supabase)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "zafar_secret_2025")

MONTHS_RU   = ["января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"]
WEEKDAYS_RU = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

def send_tg(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }, timeout=8)

def get_name(table_id, table, id_field="id", name_field="name"):
    if not table_id:
        return "—"
    for row in table:
        if row[id_field] == table_id:
            return row[name_field]
    return "—"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Verify secret header
        secret = self.headers.get("x-webhook-secret", "")
        if secret != WEBHOOK_SECRET:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error":"unauthorized"}')
            return

        try:
            length  = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))

            # Supabase sends: {"type": "INSERT", "record": {...}}
            record_type = payload.get("type", "")
            record      = payload.get("record", {})

            if record_type == "INSERT" and record:
                db = create_client(SUPABASE_URL, SUPABASE_KEY)
                masters  = db.table("masters").select("*").execute().data or []
                services = db.table("services").select("*").execute().data or []

                master_name  = get_name(record.get("master_id"),  masters)
                service_name = get_name(record.get("service_id"), services)
                amount       = record.get("total_amount", 0) or 0
                client_name  = record.get("client_name", "")
                client_phone = record.get("client_phone", "")
                notes        = record.get("notes", "")
                booking_date = record.get("booking_date", "")
                booking_time = (record.get("booking_time") or "")[:5]

                # Format date
                try:
                    d = datetime.strptime(booking_date, "%Y-%m-%d")
                    date_display = f"{WEEKDAYS_RU[d.weekday()]}, {d.day} {MONTHS_RU[d.month-1]}"
                except:
                    date_display = booking_date

                msg = (
                    "🔔 *Новая запись!*\n\n"
                    f"👤 *Клиент:* {client_name}\n"
                    f"📞 *Телефон:* {client_phone}\n"
                    f"✂️ *Услуга:* {service_name}\n"
                    f"💈 *Мастер:* {master_name}\n"
                    f"📅 *Дата:* {date_display}\n"
                    f"⏰ *Время:* {booking_time}\n"
                    f"💰 *Сумма:* {amount} смн"
                )
                if notes:
                    msg += f"\n💬 *Заметка:* {notes}"

                send_tg(msg)

                # Mark notified
                db.table("bookings").update({"telegram_notified": True}) \
                    .eq("id", record["id"]).execute()

        except Exception as e:
            print(f"notify error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"notify endpoint OK")

    def log_message(self, *args):
        pass
