# EstimatePro - Telegram Bot для создания смет

Профессиональный Telegram бот для создания смет проектов с поддержкой ИИ-помощника.

## ✨ Возможности

- 📝 **Создание смет** - удобное создание и управление сметами проектов
- 🔧 **Шаблоны работ** - библиотека типовых работ для быстрого составления смет
- 🤖 **ИИ-помощник** - автоматическая генерация смет на основе описания проекта
- 📊 **Статистика** - аналитика по проектам и эффективности
- 📄 **Отчеты** - экспорт смет в различных форматах
- 💾 **База данных** - надежное хранение всех данных

## 🏗️ Архитектура

Проект использует модульную архитектуру для легкой поддержки:

```
bot/
├── __init__.py          # Инициализация пакета
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── handlers/            # Обработчики
│   ├── __init__.py
│   ├── commands.py      # Команды (/start, /help)
│   ├── messages.py      # Обработка сообщений
│   ├── callbacks.py     # Callback кнопки
│   └── inline.py        # Inline режим
├── database/            # База данных
│   ├── __init__.py
│   ├── models.py        # Модели данных
│   └── database.py      # Работа с БД
├── keyboards/           # Клавиатуры
│   ├── __init__.py
│   ├── inline.py        # Inline клавиатуры
│   └── reply.py         # Reply клавиатуры
├── utils/              # Утилиты
│   ├── __init__.py
│   ├── decorators.py    # Декораторы
│   ├── helpers.py       # Вспомогательные функции
│   ├── validators.py    # Валидация данных
│   └── states.py        # FSM состояния
└── middlewares/        # Промежуточное ПО
    ├── __init__.py
    ├── auth.py          # Аутентификация
    └── logging.py       # Логирование
```

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd estimate-pro
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

Скопируйте файл с примером настроек:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```env
# Обязательные настройки
BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@localhost:5432/database

# Опциональные настройки
LOG_LEVEL=INFO
AI_ENABLED=true
GIGACHAT_CREDENTIALS=your_credentials
```

### 4. Настройка базы данных

Убедитесь, что PostgreSQL запущен и создайте базу данных:

```sql
CREATE DATABASE estimates_db;
CREATE USER bot_user WITH PASSWORD 'bot_password';
GRANT ALL PRIVILEGES ON DATABASE estimates_db TO bot_user;
```

### 5. Запуск бота

Несколько способов запуска:

```bash
# Через основной файл
python bot.py

# Через модуль
python -m bot.main

# С Docker
docker-compose up -d
```

## 📦 Зависимости

Основные зависимости проекта:

- `aiogram` - Telegram Bot API
- `asyncpg` - PostgreSQL драйвер
- `python-dotenv` - Загрузка переменных окружения
- `reportlab` - Генерация PDF отчетов

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | **Обязательно** |
| `DATABASE_URL` | URL подключения к PostgreSQL | **Обязательно** |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `AI_ENABLED` | Включить ИИ-помощника | `true` |
| `GIGACHAT_CREDENTIALS` | Учетные данные GigaChat | - |

### Создание бота

1. Отправьте `/newbot` боту @BotFather в Telegram
2. Следуйте инструкциям для создания бота
3. Получите токен и добавьте его в `.env`

## 🤖 ИИ-помощник

Бот поддерживает интеграцию с GigaChat для автоматической генерации смет:

1. Получите API ключ GigaChat
2. Добавьте `GIGACHAT_CREDENTIALS` в `.env`
3. Установите `AI_ENABLED=true`

## 📊 Использование

### Основные команды

- `/start` - Запуск бота и главное меню
- `/help` - Справка по использованию

### Основной функционал

1. **Создание сметы**
   - Нажмите "📝 Новая смета"
   - Введите название и описание
   - Добавляйте позиции работ

2. **Шаблоны работ**
   - Создавайте шаблоны для часто используемых работ
   - Группируйте по категориям
   - Используйте для быстрого создания смет

3. **ИИ-помощник**
   - Опишите проект на естественном языке
   - Выберите тип проекта
   - Получите готовую смету

## 🛠️ Разработка

### Добавление новых функций

1. **Новый обработчик**: добавьте в соответствующий файл в `handlers/`
2. **Новая клавиатура**: добавьте в `keyboards/inline.py` или `keyboards/reply.py`
3. **Новая утилита**: добавьте в соответствующий файл в `utils/`
4. **Новая модель**: добавьте в `database/models.py`

### Структура обработчика

```python
@router.callback_query(F.data == "example")
@error_handler
async def callback_example(callback: CallbackQuery, user_id: int, db, **kwargs):
    """Описание обработчика"""
    # Ваш код здесь
    await callback.message.edit_text("Пример")
```

### Добавление middleware

```python
# В bot/main.py
from bot.middlewares.custom import CustomMiddleware

dp.message.middleware(CustomMiddleware())
dp.callback_query.middleware(CustomMiddleware())
```

## 🐳 Docker

Запуск с Docker:

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down
```

## 📝 Changelog

### v1.0.0 (Текущая версия)

- Модульная архитектура
- Поддержка PostgreSQL
- ИИ-помощник
- Система шаблонов
- Middleware для аутентификации и логирования

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Сделайте коммит изменений (`git commit -m 'Add some amazing feature'`)
4. Отправьте изменения в ветку (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 🆘 Поддержка

Если у вас возникли вопросы или проблемы:

1. Проверьте документацию
2. Посмотрите существующие Issues
3. Создайте новый Issue с подробным описанием проблемы

## 📊 Статистика

- 🏗️ Модульная архитектура для легкого расширения
- 🚀 Высокая производительность с async/await
- 🔐 Безопасность с middleware аутентификации
- 📱 Удобный интерфейс с inline клавиатурами
- 🤖 Интеграция с современными ИИ-сервисами 