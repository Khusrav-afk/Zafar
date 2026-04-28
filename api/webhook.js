// api/webhook.js
// Vercel Serverless Function — Telegram Bot (Node.js)

const BOT_TOKEN    = process.env.BOT_TOKEN;
const GROUP_CHAT_ID = process.env.GROUP_CHAT_ID;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

const MONTHS_RU   = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
const WEEKDAYS_RU = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];
const WEEKDAYS_SH = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];

// ─── Telegram ───────────────────────────────────────
async function sendMessage(chatId, text) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' })
  });
}

// ─── Supabase ────────────────────────────────────────
async function supabase(table, params = '') {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}${params}`, {
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`
    }
  });
  return res.json();
}

// ─── Helpers ─────────────────────────────────────────
function fmtDate(d) {
  return `${d.getDate()} ${MONTHS_RU[d.getMonth()]}`;
}

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

function dateStr(d) {
  return d.toISOString().split('T')[0];
}

function getMasterName(masterId, masters) {
  if (!masterId) return 'Любой мастер';
  const m = masters.find(x => x.id === masterId);
  return m ? m.name : '—';
}

function getServiceName(serviceId, services) {
  if (!serviceId) return '—';
  const s = services.find(x => x.id === serviceId);
  return s ? s.name : '—';
}

// ─── Build schedule message ───────────────────────────
function buildDayMsg(date, bookings, masters, services, title) {
  const day = `${WEEKDAYS_RU[date.getDay()]}, ${fmtDate(date)}`;
  if (!bookings.length) {
    return `📅 *${title}* — ${day}\n\n_Записей нет. День свободен!_ 🎉`;
  }

  const byMaster = {};
  const anyBk = [];
  for (const b of bookings) {
    if (b.master_id) {
      byMaster[b.master_id] = byMaster[b.master_id] || [];
      byMaster[b.master_id].push(b);
    } else {
      anyBk.push(b);
    }
  }

  const lines = [`📅 *${title}* — ${day}\n`];
  for (const m of masters) {
    const bks = byMaster[m.id] || [];
    if (!bks.length) continue;
    const total = bks.reduce((s, b) => s + (b.total_amount || 0), 0);
    lines.push(`\n💈 *${m.name}* (${bks.length} зап. · ${total} смн)`);
    for (const b of bks) {
      const t = b.booking_time.slice(0, 5);
      const svc = getServiceName(b.service_id, services);
      lines.push(`  ⏰ ${t} — ${b.client_name} (${b.client_phone})`);
      lines.push(`      ✂️ ${svc} · ${b.total_amount || 0} смн`);
    }
  }
  if (anyBk.length) {
    lines.push(`\n👥 *Мастер не назначен:*`);
    for (const b of anyBk) {
      lines.push(`  ⏰ ${b.booking_time.slice(0,5)} — ${b.client_name}`);
    }
  }

  const totalAll = bookings.reduce((s, b) => s + (b.total_amount || 0), 0);
  lines.push(`\n━━━━━━━━━━━━━━━━━━━`);
  lines.push(`📊 Итого: *${bookings.length} записей · ${totalAll} смн*`);
  return lines.join('\n');
}

// ─── Commands ─────────────────────────────────────────
async function handleCommand(chatId, cmd) {
  const masters  = await supabase('masters',  '?is_active=eq.true');
  const services = await supabase('services', '');

  if (cmd === '/start' || cmd === '/help') {
    await sendMessage(chatId,
      '💈 *ZAFAR Salon Bot*\n\n' +
      '/today — расписание сегодня\n' +
      '/tomorrow — расписание завтра\n' +
      '/week — записи на 7 дней\n' +
      '/stats — статистика сегодня'
    );
    return;
  }

  if (cmd === '/today') {
    const today = new Date();
    const bookings = await supabase('bookings',
      `?booking_date=eq.${todayStr()}&status=neq.cancelled&order=booking_time`
    );
    await sendMessage(chatId, buildDayMsg(today, bookings, masters, services, 'Сегодня'));
    return;
  }

  if (cmd === '/tomorrow') {
    const tom = new Date();
    tom.setDate(tom.getDate() + 1);
    const bookings = await supabase('bookings',
      `?booking_date=eq.${dateStr(tom)}&status=neq.cancelled&order=booking_time`
    );
    await sendMessage(chatId, buildDayMsg(tom, bookings, masters, services, 'Завтра'));
    return;
  }

  if (cmd === '/week') {
    const today = new Date();
    const lines = ['📆 *Расписание на 7 дней:*\n'];
    let totalWeek = 0;

    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(today.getDate() + i);
      const ds = dateStr(d);
      const bks = await supabase('bookings',
        `?booking_date=eq.${ds}&status=neq.cancelled&order=booking_time`
      );
      const rev = bks.reduce((s, b) => s + (b.total_amount || 0), 0);
      totalWeek += bks.length;
      const day = `${WEEKDAYS_SH[d.getDay()]} ${fmtDate(d)}`;

      if (bks.length) {
        lines.push(`📅 *${day}* — ${bks.length} зап. · ${rev} смн`);
        for (const b of bks.slice(0, 3)) {
          const mn = getMasterName(b.master_id, masters);
          lines.push(`   ${b.booking_time.slice(0,5)} ${b.client_name} → ${mn}`);
        }
        if (bks.length > 3) lines.push(`   _+ещё ${bks.length - 3}_`);
      } else {
        lines.push(`📅 *${day}* — свободно`);
      }
    }

    lines.push(`\n━━━━━━━━━━━━━━━━━━━`);
    lines.push(`📊 Всего на неделю: *${totalWeek} записей*`);
    await sendMessage(chatId, lines.join('\n'));
    return;
  }

  if (cmd === '/stats') {
    const bookings = await supabase('bookings',
      `?booking_date=eq.${todayStr()}&status=neq.cancelled`
    );
    const rev = bookings.reduce((s, b) => s + (b.total_amount || 0), 0);

    const byMaster = {};
    for (const b of bookings) {
      const name = getMasterName(b.master_id, masters);
      byMaster[name] = byMaster[name] || { count: 0, rev: 0 };
      byMaster[name].count++;
      byMaster[name].rev += b.total_amount || 0;
    }

    const lines = [
      `📊 *Статистика сегодня*\n`,
      `Записей: *${bookings.length}*`,
      `Выручка: *${rev} смн*\n`
    ];
    if (Object.keys(byMaster).length) {
      lines.push('*По мастерам:*');
      for (const [name, d] of Object.entries(byMaster).sort((a,b) => b[1].rev - a[1].rev)) {
        lines.push(`💈 ${name}: ${d.count} зап. · ${d.rev} смн`);
      }
    }
    await sendMessage(chatId, lines.join('\n'));
    return;
  }
}

// ─── Main Handler ─────────────────────────────────────
export default async function handler(req, res) {
  if (req.method === 'POST') {
    try {
      const body = req.body;
      const msg  = body.message || body.channel_post;
      if (msg) {
        const chatId = msg.chat.id;
        const text   = msg.text || '';
        if (text.startsWith('/')) {
          const cmd = text.split(' ')[0].split('@')[0].toLowerCase();
          await handleCommand(chatId, cmd);
        }
      }
    } catch (e) {
      console.error('webhook error:', e);
    }
  }
  res.status(200).json({ ok: true });
}
