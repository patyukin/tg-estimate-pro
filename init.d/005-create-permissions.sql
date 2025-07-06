-- ===============================================
-- Настройка прав доступа и безопасности
-- ===============================================

-- Предоставление прав пользователю bot_user на схему
GRANT USAGE ON SCHEMA estimates_app TO bot_user;
GRANT CREATE ON SCHEMA estimates_app TO bot_user;

-- Права на таблицы
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA estimates_app TO bot_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA estimates_app TO bot_user;

-- Права на функции
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA estimates_app TO bot_user;

-- Права на будущие объекты
ALTER DEFAULT PRIVILEGES IN SCHEMA estimates_app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA estimates_app GRANT USAGE, SELECT ON SEQUENCES TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA estimates_app GRANT EXECUTE ON FUNCTIONS TO bot_user;

-- Настройка поиска схем для пользователя
ALTER USER bot_user SET search_path TO estimates_app, public;

\echo 'Права доступа настроены успешно'; 