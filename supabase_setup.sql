-- ============================================
--   ZAFAR SALON — Supabase Database Setup
--   Запустите этот SQL в Supabase SQL Editor
-- ============================================

-- Таблица мастеров
CREATE TABLE masters (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  specialty TEXT,
  photo_url TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица услуг
CREATE TABLE services (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 30,
  is_active BOOLEAN DEFAULT true
);

-- Таблица записей (заказов)
CREATE TABLE bookings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  master_id UUID REFERENCES masters(id),
  service_id UUID REFERENCES services(id),
  client_name TEXT NOT NULL,
  client_phone TEXT NOT NULL,
  booking_date DATE NOT NULL,
  booking_time TIME NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')),
  total_amount DECIMAL(10,2),
  telegram_notified BOOLEAN DEFAULT false,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================
--  Row Level Security
-- =====================
ALTER TABLE masters ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- Публичный доступ на чтение мастеров
CREATE POLICY "Public read masters" ON masters FOR SELECT USING (true);

-- Публичный доступ на чтение услуг
CREATE POLICY "Public read services" ON services FOR SELECT USING (true);

-- Публичный доступ на чтение заказов (только занятые слоты)
CREATE POLICY "Public read bookings" ON bookings FOR SELECT USING (true);

-- Публичный доступ на создание заказа
CREATE POLICY "Public create bookings" ON bookings FOR INSERT WITH CHECK (true);

-- Обновление заказа (для бота — пометить как уведомлено)
CREATE POLICY "Service update bookings" ON bookings FOR UPDATE USING (true);

-- =====================
--   Тестовые данные
-- =====================
INSERT INTO masters (name, specialty) VALUES
  ('Зафар', 'Основатель · Топ-мастер'),
  ('Алишер', 'Барбер · Бороды'),
  ('Бобур', 'Мастер стрижек'),
  ('Санжар', 'Стилист · Укладки');

INSERT INTO services (name, description, price, duration_minutes) VALUES
  ('Классическая стрижка', 'Элегантная стрижка под ваш тип лица', 50, 30),
  ('Стрижка + борода', 'Стрижка волос и профессиональное оформление бороды', 80, 60),
  ('Стрижка машинкой', 'Чёткая стрижка машинкой на выбранную длину', 40, 20),
  ('Модельная стрижка', 'Индивидуальная авторская стрижка от мастера', 70, 45);

-- =====================
--   Realtime для бота
-- =====================
ALTER PUBLICATION supabase_realtime ADD TABLE bookings;
