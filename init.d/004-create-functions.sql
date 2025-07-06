-- ===============================================
-- Создание функций и триггеров
-- ===============================================

-- Установка схемы
SET search_path TO estimates_app, public;

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_estimates_updated_at ON estimates;
CREATE TRIGGER update_estimates_updated_at
    BEFORE UPDATE ON estimates
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_estimate_items_updated_at ON estimate_items;
CREATE TRIGGER update_estimate_items_updated_at
    BEFORE UPDATE ON estimate_items
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_work_templates_updated_at ON work_templates;
CREATE TRIGGER update_work_templates_updated_at
    BEFORE UPDATE ON work_templates
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

-- Функция для подсчета итогов сметы
CREATE OR REPLACE FUNCTION calculate_estimate_totals(estimate_id_param INTEGER)
RETURNS TABLE(
    total_cost DECIMAL(15,2),
    total_duration DECIMAL(10,2),
    items_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(ei.cost * ei.quantity), 0)::DECIMAL(15,2) as total_cost,
        COALESCE(SUM(ei.duration * ei.quantity), 0)::DECIMAL(10,2) as total_duration,
        COUNT(ei.id)::INTEGER as items_count
    FROM estimate_items ei
    WHERE ei.estimate_id = estimate_id_param;
END;
$$ LANGUAGE plpgsql;

-- Функция для поиска смет пользователя
CREATE OR REPLACE FUNCTION search_user_estimates(
    user_id_param BIGINT,
    search_text TEXT DEFAULT NULL,
    status_filter VARCHAR(50) DEFAULT NULL,
    limit_param INTEGER DEFAULT 50,
    offset_param INTEGER DEFAULT 0
)
RETURNS TABLE(
    id INTEGER,
    title VARCHAR(255),
    description TEXT,
    status VARCHAR(50),
    currency VARCHAR(3),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    total_cost DECIMAL(15,2),
    total_duration DECIMAL(10,2),
    items_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.title,
        e.description,
        e.status,
        e.currency,
        e.created_at,
        e.updated_at,
        COALESCE(SUM(ei.cost * ei.quantity), 0)::DECIMAL(15,2) as total_cost,
        COALESCE(SUM(ei.duration * ei.quantity), 0)::DECIMAL(10,2) as total_duration,
        COUNT(ei.id)::INTEGER as items_count
    FROM estimates e
    LEFT JOIN estimate_items ei ON e.id = ei.estimate_id
    WHERE e.user_id = user_id_param
        AND (search_text IS NULL OR e.title ILIKE '%' || search_text || '%')
        AND (status_filter IS NULL OR e.status = status_filter)
    GROUP BY e.id, e.title, e.description, e.status, e.currency, e.created_at, e.updated_at
    ORDER BY e.updated_at DESC
    LIMIT limit_param
    OFFSET offset_param;
END;
$$ LANGUAGE plpgsql;

\echo 'Функции и триггеры созданы успешно'; 