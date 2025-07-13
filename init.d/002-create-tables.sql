-- ===============================================
-- Создание таблиц для бота-сметчика
-- ===============================================

-- Установка схемы
SET search_path TO estimates_app, public;

-- Таблица пользователей (для расширения функционала)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Комментарии к таблице пользователей
COMMENT ON TABLE users IS 'Информация о пользователях бота';
COMMENT ON COLUMN users.telegram_id IS 'ID пользователя в Telegram';
COMMENT ON COLUMN users.username IS 'Username в Telegram (может быть NULL)';
COMMENT ON COLUMN users.language_code IS 'Код языка пользователя';
COMMENT ON COLUMN users.is_active IS 'Активен ли пользователь';

-- Таблица смет
CREATE TABLE IF NOT EXISTS estimates (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    currency VARCHAR(3) DEFAULT 'RUB',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ограничения
    CONSTRAINT estimates_status_check CHECK (status IN ('draft', 'active', 'completed', 'archived')),
    CONSTRAINT estimates_title_length CHECK (LENGTH(title) >= 1 AND LENGTH(title) <= 255)
);

-- Комментарии к таблице смет
COMMENT ON TABLE estimates IS 'Сметы пользователей';
COMMENT ON COLUMN estimates.user_id IS 'Telegram ID пользователя-владельца сметы';
COMMENT ON COLUMN estimates.title IS 'Название сметы';
COMMENT ON COLUMN estimates.description IS 'Описание сметы';
COMMENT ON COLUMN estimates.status IS 'Статус сметы: draft, active, completed, archived';
COMMENT ON COLUMN estimates.currency IS 'Валюта сметы (ISO код)';

-- Таблица позиций в смете
CREATE TABLE IF NOT EXISTS estimate_items (
    id SERIAL PRIMARY KEY,
    estimate_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    duration DECIMAL(10,2) NOT NULL DEFAULT 0,
    cost DECIMAL(15,2) NOT NULL DEFAULT 0,
    unit VARCHAR(50) DEFAULT 'шт',
    quantity DECIMAL(10,2) DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешний ключ
    FOREIGN KEY (estimate_id) REFERENCES estimates (id) ON DELETE CASCADE,
    
    -- Ограничения
    CONSTRAINT estimate_items_name_length CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 255),
    CONSTRAINT estimate_items_duration_positive CHECK (duration >= 0),
    CONSTRAINT estimate_items_cost_positive CHECK (cost >= 0),
    CONSTRAINT estimate_items_quantity_positive CHECK (quantity > 0)
);

-- Комментарии к таблице позиций
COMMENT ON TABLE estimate_items IS 'Позиции работ/услуг в сметах';
COMMENT ON COLUMN estimate_items.estimate_id IS 'ID сметы к которой относится позиция';
COMMENT ON COLUMN estimate_items.name IS 'Наименование работы/услуги';
COMMENT ON COLUMN estimate_items.description IS 'Детальное описание позиции';
COMMENT ON COLUMN estimate_items.duration IS 'Время выполнения в часах';
COMMENT ON COLUMN estimate_items.cost IS 'Стоимость за единицу';
COMMENT ON COLUMN estimate_items.unit IS 'Единица измерения';
COMMENT ON COLUMN estimate_items.quantity IS 'Количество единиц';
COMMENT ON COLUMN estimate_items.sort_order IS 'Порядок сортировки в смете';

-- Таблица шаблонов работ (для ускорения создания смет)
CREATE TABLE IF NOT EXISTS work_templates (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    default_duration DECIMAL(10,2) DEFAULT 0,
    default_cost DECIMAL(15,2) DEFAULT 0,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ограничения
    CONSTRAINT work_templates_name_length CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 255),
    CONSTRAINT work_templates_duration_positive CHECK (default_duration >= 0),
    CONSTRAINT work_templates_cost_positive CHECK (default_cost >= 0)
);

-- Комментарии к таблице шаблонов
COMMENT ON TABLE work_templates IS 'Шаблоны работ/услуг для быстрого создания позиций';
COMMENT ON COLUMN work_templates.user_id IS 'ID пользователя-владельца шаблона';
COMMENT ON COLUMN work_templates.name IS 'Название шаблона работы';
COMMENT ON COLUMN work_templates.default_duration IS 'Время выполнения по умолчанию';
COMMENT ON COLUMN work_templates.default_cost IS 'Стоимость по умолчанию';
COMMENT ON COLUMN work_templates.category IS 'Категория работ';
COMMENT ON COLUMN work_templates.usage_count IS 'Количество использований шаблона';

-- Таблица настроек пользователей
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    default_hourly_rate DECIMAL(10,2),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'ru',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    ai_assistance_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешний ключ
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Комментарии к таблице настроек
COMMENT ON TABLE user_settings IS 'Настройки пользователей бота';
COMMENT ON COLUMN user_settings.user_id IS 'ID пользователя из таблицы users';
COMMENT ON COLUMN user_settings.default_hourly_rate IS 'Почасовая ставка по умолчанию';
COMMENT ON COLUMN user_settings.timezone IS 'Часовой пояс пользователя';
COMMENT ON COLUMN user_settings.language IS 'Язык интерфейса';
COMMENT ON COLUMN user_settings.notifications_enabled IS 'Включены ли уведомления';
COMMENT ON COLUMN user_settings.ai_assistance_enabled IS 'Включена ли помощь ИИ';

\echo 'Таблицы созданы успешно'; 