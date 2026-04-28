# 💈 ZAFAR SALON — Деплой на GitHub + Vercel

## Структура проекта

```
zafar-salon/
├── public/
│   ├── index.html          ← Главный сайт
│   └── admin.html          ← Панель владельца
├── api/
│   ├── webhook.py          ← Telegram бот (команды)
│   ├── notify.py           ← Уведомление о новой записи
│   └── schedule.py         ← Утреннее расписание (7:00)
├── vercel.json             ← Конфигурация Vercel + Cron
├── requirements.txt        ← Python зависимости
├── supabase_setup.sql      ← SQL для базы данных
└── README.md
```

**Как всё работает:**
```
Клиент → index.html → Supabase (сохранить запись)
                           ↓
                    Supabase Webhook → /api/notify → Telegram группа 🔔
                           
Каждое утро 7:00 → Vercel Cron → /api/schedule → Telegram группа 📅

Команды в Telegram → /api/webhook → ответ в чат
```

---

## ШАГ 1 — Supabase (база данных) 🗄️

1. Зайти на **[supabase.com](https://supabase.com)** → бесплатный аккаунт
2. **New project** → название `zafar-salon` → создать
3. **SQL Editor** → вставить весь код из `supabase_setup.sql` → **Run**
4. **Project Settings → API** → скопировать:
   - `Project URL` → это `SUPABASE_URL`
   - `anon public` ключ → это `SUPABASE_KEY`

---

## ШАГ 2 — Telegram Бот 🤖

### 2.1 Создать бота
1. Написать **[@BotFather](https://t.me/BotFather)**
2. `/newbot` → имя: `ZAFAR Salon` → username: `zafarsalon_bot`
3. Скопировать **BOT_TOKEN** (вида `1234567890:ABCdef...`)

### 2.2 Группа
1. Создать группу `ZAFAR Команда`
2. Добавить бота → сделать **администратором**
3. Отправить любое сообщение в группу
4. Открыть в браузере: `https://api.telegram.org/bot<ТОКЕН>/getUpdates`
5. Найти `"chat":{"id":` — это ваш **GROUP_CHAT_ID** (отрицательное число)

---

## ШАГ 3 — GitHub 🐙

```bash
# Установить git (если не установлен)
# Windows: https://git-scm.com/download/win

# В папке проекта открыть терминал:
git init
git add .
git commit -m "Initial commit — ZAFAR Salon"

# Создать репозиторий на github.com → New repository
# Название: zafar-salon → Create
# Затем выполнить команды которые покажет GitHub:
git remote add origin https://github.com/ВАШ_ЮЗЕР/zafar-salon.git
git branch -M main
git push -u origin main
```

---

## ШАГ 4 — Vercel 🚀

### 4.1 Подключить проект
1. Зайти на **[vercel.com](https://vercel.com)** → Sign Up (через GitHub)
2. **Add New → Project**
3. Найти ваш репозиторий `zafar-salon` → **Import**
4. Настройки оставить как есть → **Deploy**

### 4.2 Добавить переменные окружения
В Vercel → **Settings → Environment Variables** добавить:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | `1234567890:ABCdef...` |
| `GROUP_CHAT_ID` | `-1001234567890` |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | `eyJhbGci...` |
| `WEBHOOK_SECRET` | `придумайте_любое_слово` |

После добавления переменных → **Redeploy** (Settings → Deployments → ...)

### 4.3 Привязать Telegram Webhook
После деплоя ваш сайт доступен по адресу типа `zafar-salon.vercel.app`.

Откройте в браузере (замените данные):
```
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://zafar-salon.vercel.app/api/webhook
```
Должны увидеть: `{"ok":true,"result":true}`

---

## ШАГ 5 — Supabase Webhook (уведомления о записях) 🔗

1. В Supabase → **Database → Webhooks**
2. **Create a new hook**:
   - Name: `notify_telegram`
   - Table: `bookings`
   - Events: ✅ `INSERT`
   - URL: `https://zafar-salon.vercel.app/api/notify`
   - HTTP Headers:
     - `x-webhook-secret` = то что вы задали в `WEBHOOK_SECRET`
3. **Confirm** → сохранить

---

## Проверка работы ✅

1. Открыть `https://zafar-salon.vercel.app`
2. Сделать тестовую запись
3. ✅ В Telegram группе должно прийти уведомление
4. Написать боту `/today` → должно прийти расписание
5. Открыть `https://zafar-salon.vercel.app/admin.html` → войти в панель

### Проверить cron вручную:
```
https://zafar-salon.vercel.app/api/schedule
```
Должны прийти 2 сообщения в группу (расписание на сегодня + неделю).

---

## Обновление сайта в будущем

Просто делайте изменения в файлах и:
```bash
git add .
git commit -m "Обновление"
git push
```
Vercel автоматически задеплоит новую версию за ~30 секунд! 🎉

---

## Структура Cron

В `vercel.json` настроен cron:
```json
"crons": [{ "path": "/api/schedule", "schedule": "0 2 * * *" }]
```
`0 2 * * *` = каждый день в 02:00 UTC = **07:00 по Душанбе** ✅

---

*ZAFAR Мужской Салон · Худжанд · 2025*
