# Makefile для управления Docker развертыванием

.PHONY: help build up down logs restart clean setup

# Переменные
COMPOSE_FILE = docker-compose.yml
ENV_FILE = .env

help: ## Показать это меню
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Подготовка окружения (копирование .env)
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Создание файла .env из примера..."; \
		cp env.example $(ENV_FILE); \
		echo "Отредактируйте файл .env и укажите BOT_TOKEN"; \
	else \
		echo "Файл .env уже существует"; \
	fi

build: ## Сборка Docker образа
	docker-compose -f $(COMPOSE_FILE) build

up: ## Запуск всех сервисов
	docker-compose -f $(COMPOSE_FILE) up -d

down: ## Остановка всех сервисов
	docker-compose -f $(COMPOSE_FILE) down

restart: ## Перезапуск всех сервисов
	docker-compose -f $(COMPOSE_FILE) restart

logs: ## Просмотр логов
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-bot: ## Просмотр логов бота
	docker-compose -f $(COMPOSE_FILE) logs -f bot

logs-db: ## Просмотр логов базы данных
	docker-compose -f $(COMPOSE_FILE) logs -f postgres

ps: ## Показать статус контейнеров
	docker-compose -f $(COMPOSE_FILE) ps

shell-bot: ## Войти в контейнер бота
	docker-compose -f $(COMPOSE_FILE) exec bot /bin/bash

shell-db: ## Войти в PostgreSQL
	docker-compose -f $(COMPOSE_FILE) exec postgres psql -U bot_user -d estimates

clean: ## Очистка (остановка и удаление контейнеров, томов)
	docker-compose -f $(COMPOSE_FILE) down -v
	docker system prune -f

dev: setup build up ## Полная настройка для разработки

prod: ## Запуск в production режиме
	docker-compose -f $(COMPOSE_FILE) up -d --no-build

backup: ## Создание бэкапа базы данных
	docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U bot_user estimates > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Восстановление из бэкапа (требует файл BACKUP_FILE)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Использование: make restore BACKUP_FILE=backup_file.sql"; \
		exit 1; \
	fi
	docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U bot_user estimates < $(BACKUP_FILE) 