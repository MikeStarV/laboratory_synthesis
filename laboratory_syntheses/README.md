# Лабораторные синтезы — ЛР1

FastAPI + Jinja2, одна коллекция в памяти: четыре опубликованных синтеза,
один удалённый и один черновик. Поля услуги — длительность и температура.
Массы и расчёт практического выхода относятся к будущей заявке.

## Запуск

Команды выполняются из корня репозитория `synthesis-yield-calculation` (Python 3.10+):

```bash
python3 -m venv laboratory_syntheses/venv
source laboratory_syntheses/venv/bin/activate
python -m pip install -r laboratory_syntheses/requirements.txt
python -m uvicorn laboratory_syntheses.laboratory_syntheses_app:app --reload --host 0.0.0.0 --port 8000
```

Открыть http://localhost:8000/laboratory_syntheses.
По умолчанию изображения и короткие демонстрационные анимации берутся из
`static/media`. Это условные иллюстрации, а не видеозаписи химических опытов.

## MinIO для демонстрации лабораторной

```bash
docker compose -f laboratory_syntheses/docker-compose.yml up -d
python -m laboratory_syntheses.laboratory_syntheses_seed_minio
```

Скрипт создаёт бакет, разрешает публичное чтение и загружает SVG и MP4.
В `laboratory_syntheses/.env` добавьте:

```dotenv
LABORATORY_SYNTHESES_MEDIA_BASE_URL=http://localhost:9000/synthesis-media
```

Перезапустите приложение. Адрес должен быть доступен браузеру; при просмотре
с телефона замените `localhost` на IP компьютера.
Скрипт поддерживает `MINIO_ENDPOINT`, `MINIO_BUCKET`, `MINIO_ACCESS_KEY`,
`MINIO_SECRET_KEY`; значения по умолчанию соответствуют docker-compose.yml.
Для локального просмотра без MinIO оставьте `LABORATORY_SYNTHESES_MEDIA_BASE_URL` пустым.

## Страницы

- `/laboratory_syntheses` — каталог; параметр `laboratory_synthesis_max_duration`
  задаёт максимальную длительность в минутах (0–240). Пустое поле снимает фильтр.
- `/laboratory_syntheses/feed` — начало ленты;
  `/laboratory_syntheses/feed/2` — конкретный синтез;
  `/laboratory_syntheses/feed/2?next=true` — следующий опубликованный с переходом по кругу.
- `/laboratory_syntheses/draft` — заполнение черновика без сохранения и отправки файлов,
  согласно объёму ЛР1. JavaScript не используется.

Удалённые записи и черновик недоступны в публичной ленте. Лайки вычисляются
в обработчиках по спискам идентификаторов пользователей.

## Структура

- `laboratory_syntheses_app.py` — маршруты и подготовка контекста шаблонов.
- `laboratory_syntheses_models.py` — модель услуги и статусы.
- `laboratory_syntheses_data.py` — демонстрационная коллекция.
- `laboratory_syntheses_media.py` — пути и URL медиа.
- `laboratory_syntheses_seed_minio.py` — подготовка MinIO и загрузка файлов.
- `templates/` — базовый шаблон и три страницы.
- `static/laboratory_syntheses.css` — стили; `static/media/` — демонстрационные материалы.

## Проверка

Из корня репозитория:

```bash
python -m pip install -r laboratory_syntheses/requirements-dev.txt
python -m unittest discover -s tests -v
```

Проверяются шаблоны, ссылки и локальные медиа, фильтр и его границы,
циклическая навигация, скрытие удалённых записей и черновика.

## Источник оформления

Сайт-образец: [ТехноХимТрейд — Синтез под заказ](https://tcht.ru/service/sintez-pod-zakaz/).
Оформление соответствует тёмной форме из предоставленного HTML: фон `#030303`,
полупрозрачные поля `#FFFFFF1F`, рамки `#FFFFFF40`, светлый текст,
кнопки `#FF5E22` с наведением `#D13900` и округлением 50 px.
Карточки используют полупрозрачную поверхность `#FFFFFF17`.
Заголовки — Arial/Helvetica, как в динамических стилях страницы, основной
текст — Roboto из Google Fonts с системным запасным шрифтом.
Размещение элементов, маршруты и логика приложения сохранены.
На экранах от 600 px приложение отображается по центру как экран iPhone
390 × 844. Весь интерфейс (текст, карточки, отступы, иконки и навигация)
масштабируется одним коэффициентом до полной высоты окна, с ограничением
его шириной. На телефонах сохраняется обычный адаптивный размер интерфейса.
