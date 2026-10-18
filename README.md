# Лабораторная работа №2 — лабораторные синтезы с PostgreSQL

## HTTP-методы

| № | Метод | URL | Назначение | Ответ |
|---|---|---|---|---|
| 1 | GET | `/laboratory_syntheses?laboratory_synthesis_max_duration=45` | Каталог с фильтром длительности | 200 |
| 2 | GET | `/laboratory_syntheses/feed` | Первая опубликованная карточка | 200 |
| 3 | GET | `/laboratory_syntheses/feed/{id}?next=true` | Следующая карточка; без next — карточка по ID | 200 |
| 4 | GET | `/laboratory_syntheses/draft` | Черновик | 200 |
| 5 | POST | `/laboratory_syntheses/draft` | Создание черновика по «Далее» | 303 |
| 6 | POST | `/laboratory_syntheses/draft/publish` | Публикация черновика | 303 |
| 7 | POST | `/laboratory_syntheses/{id}/delete` | Логическое удаление через SQL UPDATE | 303 |

## Таблицы БД

### `laboratory_syntheses`

| Поле | Назначение |
|---|---|
| `laboratory_synthesis_id` | Идентификатор; PK |
| `laboratory_synthesis_name` | Название |
| `laboratory_synthesis_description` | Описание; может быть NULL |
| `laboratory_synthesis_status` | draft, published, deleted |
| `laboratory_synthesis_image_url` | URL изображения; может быть NULL |
| `laboratory_synthesis_video_url` | URL видео; может быть NULL |
| `laboratory_synthesis_duration_minutes` | Длительность, мин; может быть NULL |
| `laboratory_synthesis_temperature_celsius` | Температура, °C; может быть NULL |
| `laboratory_synthesis_created_at` | Дата создания |
| `laboratory_synthesis_formed_at` | Дата публикации; может быть NULL |
| `laboratory_synthesis_creator_id` | Создатель → laboratory_synthesis_users; FK |

### `laboratory_synthesis_users`

| Поле | Назначение |
|---|---|
| `laboratory_synthesis_user_id` | Идентификатор; PK |
| `laboratory_synthesis_user_name` | Имя пользователя; уникальное |

### `laboratory_synthesis_likes`

| Поле | Назначение |
|---|---|
| `laboratory_synthesis_like_id` | Идентификатор; PK |
| `laboratory_synthesis_user_id` | Пользователь → laboratory_synthesis_users; FK |
| `laboratory_synthesis_id` | Синтез → laboratory_syntheses; FK |

У пользователя может быть только один черновик. Пара пользователь–синтез в таблице лайков уникальна. Каскадное удаление запрещено.
