# Synthesis Yield Calculation — Backend (Lab 1)

Тема: расчёт выхода продукта от теоретически возможного.

Предметная область: лабораторные синтезы (получение эфира, йодоформа, ацетилена).
Услуга — Synthesis (лабораторный синтез), заявка — YieldRequest (расчёт практического выхода продукта в %).

Стек: FastAPI, Jinja2, MinIO, Python 3.

## Структура проекта

- main.py — точка входа FastAPI, все роуты
- models.py — Pydantic-модель Synthesis и enum SynthesisStatus
- data.py — in-memory коллекция SYNTHESIS_CATALOG
- minio_client.py — построение ссылок на медиафайлы в MinIO
- templates/ — Jinja2-шаблоны трёх страниц
- static/style.css — единый файл стилей

## Запуск

1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. docker compose up -d
5. uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Страницы

- GET /synthesis-feed/{id}?next=true — лента
- GET /synthesis-draft — черновик
- GET /synthesis-catalog?reagent_mass=X — каталог с фильтрацией
