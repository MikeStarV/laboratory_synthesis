# Лабораторная работа №3 — веб-сервис лабораторных синтезов

## HTTP-методы

| № | Метод | URL | Назначение | Ответ |
|---|---|---|---|---|
| 1 | GET | `/api/laboratory_syntheses?laboratory_synthesis_max_duration=45` | Опубликованные синтезы с фильтром длительности и признаком своего синтеза | 200 |
| 2 | POST | `/api/laboratory_syntheses` | Создание или сохранение черновика; текстовые поля, файлы изображения и видео | 201 / 200 |
| 3 | GET | `/api/laboratory_syntheses/draft` | Черновик текущего пользователя без ID в адресе | 200 / 404 |
| 4 | PUT | `/api/laboratory_syntheses/{id}/publication` | Публикация своего черновика; пустое тело или {} | 200 |
| 5 | GET | `/api/laboratory_syntheses/feed` | Первая опубликованная карточка ленты | 200 / 404 |
| 6 | GET | `/api/laboratory_syntheses/feed/{id}?next=true` | Следующая опубликованная карточка; без next — карточка по ID | 200 / 404 |
| 7 | POST | `/api/laboratory_syntheses/{id}/likes` | laboratory_synthesis_liked: 1 — поставить лайк, 0 — снять | 200 |
| 8 | DELETE | `/api/laboratory_syntheses/{id}` | Логическое удаление своего синтеза | 204 |
| 9 | POST | `/api/laboratory_synthesis_users` | Регистрация: laboratory_synthesis_user_name и laboratory_synthesis_user_password | 201 |
| 10 | POST | `/api/laboratory_synthesis_users/login` | Заглушка аутентификации для ЛР4 | 501 |
| — | POST | `/api/laboratory_synthesis_users/logout` | Заглушка деавторизации для ЛР4 | 501 |

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
| `laboratory_synthesis_image_key` | Ключ изображения в MinIO; может быть NULL |
| `laboratory_synthesis_video_key` | Ключ видео в MinIO; может быть NULL |
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
| `laboratory_synthesis_user_password_hash` | Хеш пароля; может быть NULL |

### `laboratory_synthesis_likes`

| Поле | Назначение |
|---|---|
| `laboratory_synthesis_like_id` | Идентификатор; PK |
| `laboratory_synthesis_user_id` | Пользователь → laboratory_synthesis_users; FK |
| `laboratory_synthesis_id` | Синтез → laboratory_syntheses; FK |

У пользователя может быть только один черновик. Пара пользователь–синтез в таблице лайков уникальна. Каскадное удаление запрещено.
