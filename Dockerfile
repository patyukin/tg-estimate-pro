FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY *.py ./

# Создаем директорию для базы данных
RUN mkdir -p /app/data

# Создаем пользователя для безопасности
RUN adduser --disabled-password --gecos '' botuser && \
    chown -R botuser:botuser /app
USER botuser

# Указываем переменные окружения по умолчанию
ENV DATABASE_URL=sqlite:///app/data/estimates.db
ENV LOG_LEVEL=INFO

# Запускаем бота
CMD ["python", "bot.py"] 