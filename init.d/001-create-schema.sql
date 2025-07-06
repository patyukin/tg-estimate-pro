-- ===============================================
-- Создание схемы базы данных для бота-сметчика
-- ===============================================

-- Создание схемы приложения
CREATE SCHEMA IF NOT EXISTS estimates_app;

-- Установка схемы по умолчанию для текущей сессии
SET search_path TO estimates_app, public;

-- Создание расширений если нужны
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Комментарий к схеме
COMMENT ON SCHEMA estimates_app IS 'Схема данных для телеграм бота-сметчика';

\echo 'Схема estimates_app создана успешно'; 