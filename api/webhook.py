"""
api/webhook.py
══════════════════════════════════════════════════
  Vercel Serverless Function
  Telegram Bot — Webhook Handler

  Telegram sends POST to: https://your-site.vercel.app/api/webhook
  Обрабатывает команды: /today /tomorrow /week /stats /start
══════════════════════════════════════════════════
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import date, timedelta
from supabase import create_client

# ─────────────────────────────────────────
#   ENV VARIABLES (задаются в Vercel Dashboard)
# ─────────────────────────────────────────
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "")
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")

# ─────────────────────────────────────────
#   HELPERS
# ─────────────────────────────────────────
MONTHS_RU    = ["января","февраля","марта","апреля","мая","июня",
                 "июля","августа","сентября","октября","ноября","декабря"]
WEEKDAYS_RU  = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

def tg(method: str, payload: dict):
    """Вызов Telegram Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    requests.post(url, json=payload, timeout=8)

def send(chat_id, text: str):
    tg("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def fmt_date(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month-1]}"

def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_master_name(master_id, masters):
    if not master_id:
        return "Любой мастер"
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

def fetch_meta(db):
    masters  = db.table("masters").select("*").eq("is_active", True).execute().data or []
    services = db.table("services").select("*").execute().data or []
    return masters, services

def fetch_bookings(db, target_date: date):
    return (
        db.table("bookings")
        .select("*")
        .eq("booking_date", target_date.strftime("%Y-%m-%d"))
        .neq("status", "cancelled")
        .order("booking_time")
        .execute()
        .data or []
    )

def build_day_msg(target: date, bookings: list, masters: list, services: list, title: str) -> str:
    day_str = f"{WEEKDAYS_RU[target.weekday()]}, {fmt_date(target)}"
    if not bookings:
        return f"📅 *{title}* — {day_str}\n\n_Записей нет. День свободен!_ 🎉"

    by_master: dict = {}
    any_bk = []
    for b in bookings:
        mid = b.get("master_id")
        if mid:
            by_master.setdefault(mid, []).append(b)
        else:
            any_bk.append(b)

    lines = [f"📅 *{title}* — {day_str}\n"]
    for m in masters:
        bks = by_master.get(m["id"], [])
        if not bks:
            continue
        total = sum(b.get("total_amount", 0) or 0 for b in bks)
        lines.append(f"\n💈 *{m['name']}* ({len(bks)} зап. · {total} смн)")
        for b in sorted(bks, key=lambda x: x["booking_time"]):
            t = b["booking_time"][:5]
            svc = get_service_name(b["service_id"], services)
            lines.append(f"  ⏰ {t} — {b['client_name']} ({b.get('client_phone','')})")
            lines.append(f"      ✂️ {svc} · {b.get('total_amount',0)} смн")
    if any_bk:
        lines.append(f"\n👥 *Не назначен* ({len(any_bk)} зап.)")
        for b in any_bk:
            lines.append(f"  ⏰ {b['booking_time'][:5]} — {b['client_name']}")

    total_all = sum(b.get("total_amount",0) or 0 for b in bookings)
    lines += ["", "━━━━━━━━━━━━━━━━━━━",
              f"📊 Итого: *{len(bookings)} записей · {total_all} смн*"]
    return "\n".join(lines)

# ─────────────────────────────────────────
#   COMMAND HANDLERS
# ─────────────────────────────────────────
def handle_command(chat_id: int, text: str):
    cmd = text.split()[0].lower().replace("@zafarsalon_bot", "")

    if cmd == "/start" or cmd == "/help":
        send(chat_id,
            "💈 *ZAFAR Salon Bot*\n\n"
            "/today — расписание сегодня\n"
            "/tomorrow — расписание завтра\n"
            "/week — неделя\n"
            "/stats — статистика сегодня"
        )
        return

    db = get_db()
    masters, services = fetch_meta(db)

    if cmd == "/today":
        bks = fetch_bookings(db, date.today())
        send(chat_id, build_day_msg(date.today(), bks, masters, services, "Сегодня"))

    elif cmd == "/tomorrow":
        tom = date.today() + timedelta(days=1)
        bks = fetch_bookings(db, tom)
        send(chat_id, build_day_msg(tom, bks, masters, services, "Завтра"))

    elif cmd == "/week":
        today = date.today()
        lines = ["📆 *Расписание на 7 дней:*\n"]
        for i in range(7):
            t = today + timedelta(days=i)
            bks = fetch_bookings(db, t)
            rev = sum(b.get("total_amount",0) or 0 for b in bks)
            day = f"{WEEKDAYS_RU[t.weekday()][:2]} {fmt_date(t)}"
            if bks:
                lines.append(f"📅 *{day}* — {len(bks)} зап. · {rev} смн")
                for b in bks[:3]:
                    mn = get_master_name(b.get("master_id"), masters)
                    lines.append(f"  {b['booking_time'][:5]} {b['client_name']} → {mn}")
                if len(bks) > 3:
                    lines.append(f"  _+ещё {len(bks)-3}_")
            else:
                lines.append(f"📅 *{day}* — свободно")
        send(chat_id, "\n".join(lines))

    elif cmd == "/stats":
        bks = fetch_bookings(db, date.today())
        rev = sum(b.get("total_amount",0) or 0 for b in bks)
        by_m: dict = {}
        for b in bks:
            name = get_master_name(b.get("master_id"), masters)
            by_m.setdefault(name, {"count":0,"rev":0})
            by_m[name]["count"] += 1
            by_m[name]["rev"]   += b.get("total_amount",0) or 0
        lines = [f"📊 *Статистика сегодня*\n",
                 f"Записей: *{len(bks)}*",
                 f"Выручка: *{rev} смн*\n"]
        if by_m:
            lines.append("*По мастерам:*")
            for name, d in sorted(by_m.items(), key=lambda x: -x[1]["rev"]):
                lines.append(f"💈 {name}: {d['count']} зап. · {d['rev']} смн")
        send(chat_id, "\n".join(lines))

# ─────────────────────────────────────────
#   VERCEL HANDLER
# ─────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            msg    = body.get("message") or body.get("channel_post")
            if msg:
                chat_id = msg["chat"]["id"]
                text    = msg.get("text", "")
                if text.startswith("/"):
                    handle_command(chat_id, text)
        except Exception as e:
            print(f"webhook error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ZAFAR Bot Webhook OK")

    def log_message(self, *args):
        pass  # suppress default logging
