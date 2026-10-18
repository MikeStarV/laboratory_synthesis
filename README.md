# Лабораторная работа №1 — интерфейс лабораторных синтезов

## HTTP-методы

| № | Метод | URL | Назначение | Ответ |
|---|---|---|---|---|
| 1 | GET | `/laboratory_syntheses?laboratory_synthesis_max_duration=45` | Каталог с фильтром длительности | 200 |
| 2 | GET | `/laboratory_syntheses/feed` | Первая опубликованная карточка | 200 |
| 3 | GET | `/laboratory_syntheses/feed/{id}?next=true` | Следующая карточка; без next — карточка по ID | 200 |
| 4 | GET | `/laboratory_syntheses/draft` | Черновик | 200 |
