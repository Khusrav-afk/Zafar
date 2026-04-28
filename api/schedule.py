"""
api/schedule.py
══════════════════════════════════════════════════
  Vercel Cron Job (срабатывает каждый день в 02:00 UTC = 07:00 Душанбе)
  Отправляет утреннее расписание в Telegram группу

  В vercel.json:
    "crons": [{ "path": "/api/schedule", "schedule": "0 2 * * *" }]
══════════════════════════════════════════════════
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import date, timedelta
from supabase import create_client

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "")
GROUP_CHAT_ID  = os.environ.get("GROUP_CHAT_ID", "")
SUPABASE_URL   = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY   = os.environ.get("SUPABASE_KEY", "")
CRON_SECRET    = os.environ.get("CRON_SECRET", "")  # Vercel автоматически передаёт этот заголовок

MONTHS_RU   = ["января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"]
WEEKDAYS_RU = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
WEEKDAYS_SH = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

def fmt_date(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month-1]}"

def send_tg(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }, timeout=10)
    return r.ok

def get_master_name(master_id, masters):
    if not master_id:
        return "Любой"
    for m in masters:
        if m["id"] == master_id:
            return m["name"]
    return "—"

def get_service_name(service_id, services):
    if not service_id:
        return "—"
    for s in services:
        if s["id"] == service_id:
            return s["name"]
    return "—"

def build_today_schedule(today: date, bookings: list, masters: list, services: list) -> str:
    day_str = f"{WEEKDAYS_RU[today.weekday()]}, {fmt_date(today)}"

    if not bookings:
        return f"🌅 *Доброе утро!*\nСегодня — {day_str}\n\n_Записей нет. День свободен!_ ☕"

    by_master: dict = {}
    any_bk = []
    for b in bookings:
        mid = b.get("master_id")
        if mid:
            by_master.setdefault(mid, []).append(b)
        else:
            any_bk.append(b)

    lines = [f"🌅 *Доброе утро, команда ZAFAR!*",
             f"Сегодня *{day_str}*\n"]

    for m in masters:
        bks = sorted(by_master.get(m["id"], []), key=lambda x: x["booking_time"])
        if not bks:
            lines.append(f"💈 *{m['name']}* — свободен")
            continue
        rev = sum(b.get("total_amount",0) or 0 for b in bks)
        lines.append(f"\n💈 *{m['name']}* — {len(bks)} записей · {rev} смн")
        for b in bks:
            t   = b["booking_time"][:5]
            svc = get_service_name(b["service_id"], services)
            lines.append(f"  ⏰ {t} — {b['client_name']} · {svc}")

    if any_bk:
        lines.append(f"\n👥 *Мастер не назначен:*")
        for b in any_bk:
            t = b["booking_time"][:5]
            lines.append(f"  ⏰ {t} — {b['client_name']}")

    total_rev = sum(b.get("total_amount",0) or 0 for b in bookings)
    lines += ["", "━━━━━━━━━━━━━━━━━━━",
              f"📊 Итого сегодня: *{len(bookings)} записей · {total_rev} смн*",
              "\n_Удачного дня! ✂️_"]
    return "\n".join(lines)

def build_week_summary(today: date, db, masters: list, services: list) -> str:
    lines = ["📆 *Записи на ближайшие 7 дней:*\n"]
    total_week_count = 0
    total_week_rev   = 0

    for i in range(1, 7):
        t   = today + timedelta(days=i)
        res = (
            db.table("bookings")
            .select("*")
            .eq("booking_date", t.strftime("%Y-%m-%d"))
            .neq("status", "cancelled")
            .execute()
        )
        bks = res.data or []
        rev = sum(b.get("total_amount",0) or 0 for b in bks)
        total_week_count += len(bks)
        total_week_rev   += rev
        day = f"{WEEKDAYS_SH[t.weekday()]} {fmt_date(t)}"

        if bks:
            lines.append(f"📅 *{day}* — {len(bks)} зап. · {rev} смн")
            for b in sorted(bks, key=lambda x: x["booking_time"])[:4]:
                mn = get_master_name(b.get("master_id"), masters)
                lines.append(f"   {b['booking_time'][:5]} {b['client_name']} → {mn}")
            if len(bks) > 4:
                lines.append(f"   _+ещё {len(bks)-4}_")
        else:
            lines.append(f"📅 *{day}* — свободно")

    lines += ["", "━━━━━━━━━━━━━━━━━━━",
              f"📊 Всего на неделю: *{total_week_count} записей · {total_week_rev} смн*"]
    return "\n".join(lines)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Vercel Cron passes Authorization: Bearer <CRON_SECRET>
        # This is automatic when using Vercel Cron Jobs
        try:
            db       = create_client(SUPABASE_URL, SUPABASE_KEY)
            masters  = db.table("masters").select("*").eq("is_active",True).execute().data or []
            services = db.table("services").select("*").execute().data or []
            today    = date.today()

            # Load today bookings
            today_bks = (
                db.table("bookings")
                .select("*")
                .eq("booking_date", today.strftime("%Y-%m-%d"))
                .neq("status", "cancelled")
                .order("booking_time")
                .execute()
                .data or []
            )

            # Send today schedule
            today_msg = build_today_schedule(today, today_bks, masters, services)
            send_tg(today_msg)

            # Send week summary
            week_msg = build_week_summary(today, db, masters, services)
            send_tg(week_msg)

            result = {"ok": True, "today_bookings": len(today_bks), "message": "Schedule sent!"}

        except Exception as e:
            print(f"schedule cron error: {e}")
            result = {"ok": False, "error": str(e)}

        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
