# Laboratory Synthesis Backend — API для работы с лабораторными синтезами

## Модели базы данных

### Таблица `laboratory_synthesis_users` — пользователи

| Поле | Тип | Ограничения | Описание |
| :--- | :--- | :--- | :--- |
| `laboratory_synthesis_user_id` | Integer | PK, autoincrement | Идентификатор пользователя |
| `laboratory_synthesis_user_name` | String(100) | NOT NULL, UNIQUE | Имя пользователя |
| `laboratory_synthesis_user_password_hash` | String(256) | NULLABLE | Хеш пароля PBKDF2-SHA256; у старых демопользователей может отсутствовать |

### Таблица `laboratory_syntheses` — лабораторные синтезы

| Поле | Тип | Ограничения | Описание |
| :--- | :--- | :--- | :--- |
| `laboratory_synthesis_id` | Integer | PK, autoincrement | Идентификатор синтеза |
| `laboratory_synthesis_name` | String(120) | NOT NULL | Название синтеза |
| `laboratory_synthesis_description` | Text | NULLABLE | Описание синтеза |
| `laboratory_synthesis_status` | ENUM `laboratory_synthesis_status` | NOT NULL, default=draft | `draft` / `published` / `deleted` |
| `laboratory_synthesis_duration_minutes` | Integer | NULLABLE | Длительность, мин |
| `laboratory_synthesis_temperature_celsius` | Float | NULLABLE | Температура, °C |
| `laboratory_synthesis_creator_id` | Integer | FK → `laboratory_synthesis_users.laboratory_synthesis_user_id`, NOT NULL | Автор синтеза |
| `laboratory_synthesis_created_at` | TIMESTAMP(tz) | NOT NULL, default=now() | Дата создания |
| `laboratory_synthesis_formed_at` | TIMESTAMP(tz) | NULLABLE | Дата публикации |
| `laboratory_synthesis_image_url` | String(500) | NULLABLE | URL изображения |
| `laboratory_synthesis_video_url` | String(500) | NULLABLE | URL видео |
| `laboratory_synthesis_image_key` | String(255) | NULLABLE | Ключ изображения в MinIO |
| `laboratory_synthesis_video_key` | String(255) | NULLABLE | Ключ видео в MinIO |

Частичный уникальный индекс ограничивает количество черновиков: не более одного на пользователя.

### Таблица `laboratory_synthesis_likes` — лайки (м-м пользователь–синтез)

| Поле | Тип | Ограничения | Описание |
| :--- | :--- | :--- | :--- |
| `laboratory_synthesis_like_id` | Integer | PK, autoincrement | Идентификатор лайка |
| `laboratory_synthesis_user_id` | Integer | FK → `laboratory_synthesis_users.laboratory_synthesis_user_id`, NOT NULL | Кто поставил лайк |
| `laboratory_synthesis_id` | Integer | FK → `laboratory_syntheses.laboratory_synthesis_id`, NOT NULL | Какому синтезу |

Пара пользователь–синтез уникальна. Внешние ключи используют `ON DELETE RESTRICT`; каскадное удаление запрещено.

---

## API методы

Все эндпоинты имеют префикс `/api`. Тег `Лабораторные синтезы` — для работы с синтезами, `Пользователи синтезов` — для пользователей. Swagger доступен по `/api/docs`.

Каталог и лента доступны гостю. Получение черновика, создание, публикация, удаление и лайки требуют cookie `session_id`. Сессии хранятся в Redis под ключами `session:<id>`; срок действия по умолчанию — 15 минут. Для защищённых методов отсутствие действующей сессии возвращает `401`, недоступность Redis при проверке предъявленной cookie — `503`.

### Пользователи (`/api/laboratory_synthesis_users`)

#### `POST /api/laboratory_synthesis_users` — регистрация

**Тело запроса (JSON):**

```json
{
  "laboratory_synthesis_user_name": "synthesis_author",
  "laboratory_synthesis_user_password": "Synthesis-password-123"
}
```

Имя содержит от 3 до 100 символов, пароль — от 8 до 128 символов. Пароль не может состоять только из пробелов; хранится только его хеш с солью.

**Ответ `201`:**

```json
{
  "laboratory_synthesis_user_id": 1,
  "laboratory_synthesis_user_name": "synthesis_author"
}
```

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `201` | Пользователь создан |
| `409` | Имя пользователя уже занято |
| `422` | Ошибка валидации |

#### `POST /api/laboratory_synthesis_users/login` — вход

Принимает JSON с теми же полями имени и пароля, что и регистрация. Проверяет пароль, создаёт сессию Redis и устанавливает cookie `session_id` с параметрами `HttpOnly`, `SameSite=Lax`, `Path=/`. Повторный вход заменяет текущую сессию браузера.

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `200` | ID и имя пользователя; cookie устанавливается заголовком Set-Cookie |
| `401` | Неверное имя пользователя или пароль |
| `422` | Ошибка валидации |
| `503` | Redis недоступен |

Swagger на том же хосте автоматически использует установленную браузером cookie для следующих запросов.

#### `POST /api/laboratory_synthesis_users/logout` — выход

Удаляет текущую сессию из Redis и cookie из браузера. Тело запроса не требуется. Повторный запрос без cookie также возвращает `204`.

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `204` | Выход выполнен |
| `503` | Не удалось удалить сессию из Redis |

---

### Лабораторные синтезы (`/api/laboratory_syntheses`)

#### `GET /api/laboratory_syntheses` — каталог синтезов

Возвращает список опубликованных синтезов с данными автора, количеством лайков, признаками собственного синтеза и собственного лайка.

**Query-параметры:**

| Параметр | Тип | Обяз. | Описание |
| :--- | :--- | :--- | :--- |
| `laboratory_synthesis_max_duration` | int | Нет | Максимальная длительность от 0 до 90 минут; возвращаются синтезы с длительностью не больше указанной |

**Ответ `200`:**

```json
[
  {
    "laboratory_synthesis_id": 1,
    "laboratory_synthesis_name": "Учебный синтез",
    "laboratory_synthesis_description": "Описание лабораторного синтеза",
    "laboratory_synthesis_duration_minutes": 20,
    "laboratory_synthesis_temperature_celsius": 25.0,
    "laboratory_synthesis_status": "published",
    "laboratory_synthesis_image_key": "laboratory_syntheses/example.png",
    "laboratory_synthesis_video_key": "laboratory_syntheses/example.mp4",
    "laboratory_synthesis_image_url": "http://localhost:9000/synthesis-media/laboratory_syntheses/example.png",
    "laboratory_synthesis_video_url": "http://localhost:9000/synthesis-media/laboratory_syntheses/example.mp4",
    "laboratory_synthesis_created_at": "2026-11-03T10:00:00Z",
    "laboratory_synthesis_formed_at": "2026-11-03T10:05:00Z",
    "laboratory_synthesis_creator": {
      "laboratory_synthesis_user_id": 1,
      "laboratory_synthesis_user_name": "synthesis_author"
    },
    "laboratory_synthesis_is_creator": 1,
    "laboratory_synthesis_liked": 0,
    "laboratory_synthesis_likes_count": 3
  }
]
```

Для гостя `laboratory_synthesis_is_creator` и `laboratory_synthesis_liked` равны `0`. Некорректный фильтр возвращает `422`.

#### `DELETE /api/laboratory_syntheses/{laboratory_synthesis_id}` — логическое удаление

Меняет статус синтеза на `deleted`. Удалить запись может только её создатель.

**Path-параметры:**

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `laboratory_synthesis_id` | int | Положительный ID синтеза |

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `204` | Синтез логически удалён |
| `401` | Требуется вход |
| `403` | Синтез принадлежит другому пользователю |
| `404` | Синтез не найден или уже удалён |
| `422` | Ошибка валидации |

#### `GET /api/laboratory_syntheses/feed` — лента

Возвращает одну опубликованную карточку. Для обращения по ID используется `GET /api/laboratory_syntheses/feed/{laboratory_synthesis_id}`.

**Параметры:**

| Параметр | Расположение | Тип | Обяз. | Описание |
| :--- | :--- | :--- | :--- | :--- |
| `laboratory_synthesis_id` | Path | int | Для маршрута с ID | Положительный ID карточки |
| `next` | Query | bool | Нет | При `true` возвращается следующая после указанного ID карточка |

**Логика выбора:**

- `/feed` — первая опубликованная карточка.
- `/feed/1` — опубликованная карточка с ID 1.
- `/feed/1?next=true` — следующая опубликованная карточка после ID 1, с возвратом к первой в конце ленты.

**Ответ `200`:** один объект синтеза в том же формате, что элемент каталога. Поле `laboratory_synthesis_liked` показывает, поставил ли текущий пользователь лайк. При отсутствии подходящей опубликованной записи — `404`, при неверных параметрах — `422`.

#### `GET /api/laboratory_syntheses/draft` — получить черновик

Возвращает единственный черновик текущего пользователя. ID передавать не требуется.

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `200` | Объект синтеза в статусе draft |
| `401` | Требуется вход |
| `404` | У пользователя нет черновика |

#### `POST /api/laboratory_syntheses` — создать черновик

Создаёт новый черновик и загружает изображение и видео в MinIO. Если у пользователя уже есть черновик, возвращается `409`.

**Тело запроса (`multipart/form-data`):**

| Поле | Тип | Обяз. | Ограничения |
| :--- | :--- | :--- | :--- |
| `laboratory_synthesis_name` | string | Да | От 1 до 120 символов |
| `laboratory_synthesis_image` | file | Да | JPEG, PNG или WebP; по умолчанию до 10 МиБ |
| `laboratory_synthesis_video` | file | Да | MP4 или WebM; по умолчанию до 64 МиБ |

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `201` | Созданный черновик |
| `401` | Требуется вход |
| `409` | Черновик уже существует или возник конфликт сохранения |
| `413` | Превышен допустимый размер файла |
| `415` | Недопустимый формат файла |
| `422` | Ошибка валидации |
| `503` | Не удалось сохранить данные в БД или MinIO |

**Что происходит:**

1. Определяется пользователь по сессии и проверяется отсутствие его черновика.
2. Проверяются поля, тип, содержимое и размер файлов.
3. Формируется запись со статусом `draft` и текущим пользователем в качестве автора.
4. Файлы сохраняются в MinIO под сгенерированными ключами.
5. Ключи и ссылки записываются в БД. При ошибке сохранения выполняется откат и очистка загруженных файлов.

#### `PUT /api/laboratory_syntheses/draft/publication` — публикация

Публикует собственный черновик пользователя. ID не передаётся. Описание, длительность и температура заполняются при публикации.

**Тело запроса (JSON):**

```json
{
  "laboratory_synthesis_description": "Описание лабораторного синтеза",
  "laboratory_synthesis_duration_minutes": 20,
  "laboratory_synthesis_temperature_celsius": 25
}
```

**Ограничения:** описание — от 1 до 5000 символов, длительность — от 1 до 90 минут, температура — конечное число не ниже −273,15 °C. Фото и видео должны быть загружены при создании черновика.

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `200` | Объект синтеза со статусом published и датой публикации |
| `401` | Требуется вход |
| `409` | Черновик отсутствует либо в нём нет необходимых медиа |
| `422` | Ошибка валидации |

Повторная публикация без нового черновика возвращает `409`. ID, автор, статус, даты и ключи медиа назначаются сервером и не принимаются для изменения из JSON.

#### `POST /api/laboratory_syntheses/{laboratory_synthesis_id}/likes` — поставить или снять лайк

**Path-параметры:**

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `laboratory_synthesis_id` | int | Положительный ID опубликованного синтеза |

**Тело запроса (JSON):**

```json
{
  "laboratory_synthesis_liked": 1
}
```

Значение `1` ставит лайк, `0` снимает. Повторная установка или снятие не создаёт дубликатов и не возвращает ошибку.

**Ответы:**

| Код | Описание |
| :--- | :--- |
| `200` | Карточка с обновлёнными признаками и количеством лайков |
| `401` | Требуется вход |
| `404` | Опубликованный синтез не найден |
| `422` | Ошибка валидации |
