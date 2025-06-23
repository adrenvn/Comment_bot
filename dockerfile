FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    git \
    python3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создаем пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser -s /bin/bash botuser

# Создаем директории и устанавливаем права
RUN mkdir -p /app/data /app/logs /app/sessions \
    && chown -R botuser:botuser /app

# Устанавливаем pip, wheel и setuptools
RUN pip install --upgrade pip setuptools wheel

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создаем структуру директорий для модулей
RUN mkdir -p /app/database /app/handlers /app/services /app/ui /app/utils

# Создаем __init__.py файлы для Python пакетов
RUN touch /app/database/__init__.py \
    && touch /app/handlers/__init__.py \
    && touch /app/services/__init__.py \
    && touch /app/ui/__init__.py \
    && touch /app/utils/__init__.py

# Устанавливаем права на все файлы
RUN chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Health check для проверки работоспособности
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/data/bot_database.db') else 1)" || exit 1

# Экспонируем порт (если понадобится веб-интерфейс)
EXPOSE 8080

# Создаем точку входа
ENTRYPOINT ["python", "bot.py"]

# Метаданные образа
LABEL maintainer="Instagram Automation Bot"
LABEL version="2.0"
LABEL description="Instagram Automation Bot with Proxy Support"