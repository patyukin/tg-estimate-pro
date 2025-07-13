FROM python:3.13-slim

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

# Запускаем бота
CMD ["python", "bot.py"] 