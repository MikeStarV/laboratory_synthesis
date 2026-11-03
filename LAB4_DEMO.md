# ЛР4 — авторизация и завершение бэкенда

Рабочая ветка: `lab4`, исходная точка: `lab3` / `e4ad16c8fee7402fdb530ffbb82976f65230c2e3`.
Ветки `lab1`, `lab2`, `lab3` не изменены. Ничего не отправляется в GitHub автоматически.

Источники:
- [Задание курса ИУ5](https://github.com/iu5git/Web#лабораторная-4).
- [Ориентир FRAX-backend, ветка auth](https://github.com/IvanDrf/FRAX-backend/tree/b5000aef693be08fe2b7b5a9fc979491f205b533).

Использована та же архитектура: FastAPI, Redis, cookie session_id, обязательная и необязательная аутентификация. Код предметной области и PBKDF2 из вашего проекта сохранены. Выход удаляет именно `session:<id>`; в образце префикс при выходе пропущен. Регистрация не выдаёт сессию: после неё нужен вход.

## Запуск (PowerShell, из корня репозитория)

Требуются Python 3.12 и работающий Docker Desktop.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r laboratory_syntheses/requirements-test.txt
# Только при отсутствии .env; существующий файл не перезаписывать.
if (-not (Test-Path laboratory_syntheses/.env)) {
    Copy-Item laboratory_syntheses/.env.example laboratory_syntheses/.env
}
docker compose -f laboratory_syntheses/docker-compose.yml up -d
Push-Location laboratory_syntheses
..\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
.\.venv\Scripts\python.exe -m laboratory_syntheses.laboratory_syntheses_seed_minio
.\.venv\Scripts\python.exe -m laboratory_syntheses.laboratory_syntheses_seed_database
.\.venv\Scripts\python.exe -m uvicorn laboratory_syntheses.laboratory_syntheses_app:app --host 127.0.0.1 --port 8000
```

Swagger: http://127.0.0.1:8000/api/docs. Каталог: http://127.0.0.1:8000/laboratory_syntheses.
Не смешивайте `localhost` и `127.0.0.1`: cookie относится к конкретному хосту.
Redis работает на локальном порту 6380; TTL сессии — 900 секунд. На HTTPS включить `SESSION_COOKIE_SECURE=true`.
Новая миграция не требуется: хеш пароля уже добавлен в ЛР3. Старые демопользователи без хеша не могут войти; зарегистрируйте нового. Существующие данные не удалять, `docker compose down -v` не выполнять.

## Демонстрация и скриншоты

1. Откройте Swagger в инкогнито. Через POST `/api/laboratory_synthesis_users` зарегистрируйте уникального пользователя:

```json
{"laboratory_synthesis_user_name":"lab4_author","laboratory_synthesis_user_password":"Lab4-password-123"}
```

2. **Скриншот 1:** POST `/api/laboratory_synthesis_users/login` с теми же данными: 200, публичные ID и имя. Браузер сам принимает HttpOnly cookie. Вводить её в кнопку Authorize не нужно: браузер запрещает вручную устанавливать Cookie-заголовок из JavaScript.
3. **Скриншот 2:** GET `/api/laboratory_syntheses` в Swagger — 200.
4. **Скриншот 3:** DevTools → Application → Cookies → `session_id` (HttpOnly, SameSite=Lax, срок действия). Для отчёта замажьте значение; в Postman перенесите его в cookie jar или заголовок `Cookie: session_id=<значение>`. На демонстрации используйте учебную учётную запись.
5. Импортируйте `laboratory_syntheses/laboratory_syntheses_lab4.postman_collection.json`; задайте `base_url` и `session_id`. **Скриншоты 4–5:** GET каталога с cookie и без неё. Для проверки гостя отключите cookie jar (или удалите cookie для хоста), одного удаления ручного заголовка недостаточно.
6. Под автором выполните POST `/api/laboratory_syntheses`: multipart-поля `laboratory_synthesis_name`, `laboratory_synthesis_image` (файл PNG/JPEG/WebP), `laboratory_synthesis_video` (файл MP4/WebM). Можно выбрать файлы из `laboratory_syntheses/static/media`. Получите 201 и ID. GET `/api/laboratory_syntheses/draft` — 200. Повторное создание — 409.
7. **Скриншот 6:** без cookie PUT `/api/laboratory_syntheses/draft/publication` с JSON ниже — 401.

```json
{"laboratory_synthesis_description":"Учебный синтез для демонстрации ЛР4","laboratory_synthesis_duration_minutes":20,"laboratory_synthesis_temperature_celsius":25}
```

8. **Скриншот 7:** тот же PUT с cookie автора — 200, статус `published`, дата публикации и введённые поля. Затем повторный PUT — 409. Поля `creator_id`, `status`, даты и ID не принимаются от клиента.
9. **Скриншот 8:** показать ключ Redis, ID пользователя и оставшийся срок:

```powershell
docker compose -f laboratory_syntheses/docker-compose.yml exec redis redis-cli --scan --pattern 'session:*'
docker compose -f laboratory_syntheses/docker-compose.yml exec redis redis-cli GET 'session:<значение cookie>'
docker compose -f laboratory_syntheses/docker-compose.yml exec redis redis-cli TTL 'session:<значение cookie>'
```

10. GET `/feed`, GET `/feed/<id>?next=true`, POST `/<id>/likes` с `{"laboratory_synthesis_liked":1}`, затем с 0. Зарегистрировать второго пользователя, войти и попытаться удалить синтез первого — 403; чужой черновик не виден.
11. POST `/api/laboratory_synthesis_users/logout` — 204. Redis GET старого ключа возвращает nil. Повторить защищённый запрос со старой cookie вручную — 401. Каталог по-прежнему доступен. Через 15 минут без повторного входа сессия также перестаёт действовать.
12. **Скриншот 9:** диаграмма последовательности в StarUML: у сообщений поле `signature` ссылается на методы доменов диаграммы классов. Порядок и параметры приведены в `LAB4_DOCUMENTATION.md`; новую диаграмму нужно связать с вашим существующим файлом классов.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Тесты используют реальные HTTP-маршруты и SQLAlchemy, но временную SQLite, fakeredis и подмену загрузки файлов. Они не доказывают доступность Docker, настоящего PostgreSQL/Redis/MinIO, работу миграций в PostgreSQL или внешний вид браузера. Полный сценарий выше требуется повторить с запущенными сервисами.

Старые POST-формы ЛР2 удалены из приложения ветки lab4, чтобы не обходить авторизацию и проверку файлов. Шаблоны каталога, ленты и создания сохранены, изменения выполняет JavaScript через защищённый API. Для открытия черновика сначала войдите в Swagger на том же хосте.
