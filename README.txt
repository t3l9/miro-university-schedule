API для создания онлайн-расписания университета на платформе Miro. Позволяет автоматически создавать структуру расписания, добавлять учебные пары, управлять элементами доски.

Быстрый старт

Установка и запуск

1. Клонируйте репозиторий:
git clone <repository-url>
cd board_miro_API

2. Создайте виртуальное окружение и установите зависимости:
py -m venv venv

# Активация на Windows:
venv\Scripts\activate

# Активация на Linux/Mac:
source venv/bin/activate

# Установка зависимостей:
pip install -r requirements.txt

3. Настройте переменные окружения:
- Создайте файл `.env` в корне проекта
- Добавьте ваши токены Miro:

MIRO_ACCESS_TOKEN=ваш_личный_токен_miro
MIRO_BOARD_ID=id_вашей_доски_miro

4. Запустите сервер:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

5. Откройте документацию API:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Получение токенов Miro

1. Получение Access Token
1. Зарегистрируйтесь на [miro.com](https://miro.com)
2. Перейдите на [Miro Developer Platform](https://developers.miro.com)
3. Войдите в свой аккаунт
4. Нажмите "Create app"
5. Выберите "For personal use"
6. Введите название приложения (например, "University Schedule")
7. Перейдите на вкладку "Access token"
8. Нажмите "Generate new token"
9. Выберите разрешения: `boards:read`, `boards:write`, `team:read`
10. Скопируйте токен (показывается только один раз!)

2. Получение Board ID
1. Откройте доску в браузере Miro
2. Скопируйте ID из URL: `https://miro.com/app/board/{BOARD_ID}/`
3. Или создайте новую доску через Miro интерфейс

Основные возможности API

Создание элементов

1. Текстовые элементы (`POST /texts`)
```bash
curl -X POST http://localhost:8000/texts \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Расписание университета",
    "position": {"x": 0, "y": -600},
    "font_size": 36,
    "color": "#1976D2"
  }'

2. Карточки (учебные пары) (`POST /cards`)
curl -X POST http://localhost:8000/cards \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Математика",
    "description": "Лекция по алгебре",
    "position": {"x": 100, "y": 100},
    "width": 300,
    "height": 200,
    "fill_color": "#E3F2FD"
  }'

3. Учебные пары с цветовой кодировкой (`POST /lectures`)
curl -X POST http://localhost:8000/lectures \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Программирование",
    "description": "Основы Python",
    "time": "9:00-10:30",
    "classroom": "101",
    "teacher": "Иванов И.И.",
    "subject_type": "lecture",
    "position": {"x": 300, "y": 300}
  }'

4. Фреймы дней недели (`POST /frames`)
curl -X POST http://localhost:8000/frames \
  -H "Content-Type: application/json" \
  -d '{
    "day_name": "Понедельник",
    "position": {"x": 0, "y": 0},
    "width": 400,
    "height": 1200,
    "fill_color": "#F8F9FA"
  }'

Управление элементами

1. Получение всех элементов (`GET /board/items`)
curl http://localhost:8000/board/items

2. Удаление элемента (`DELETE /board/items/{item_id}`)
curl -X DELETE http://localhost:8000/board/items/uXjV1234567890

Шаблоны расписания

1. Создание структуры недели (`POST /schedule/week`)
curl -X POST http://localhost:8000/schedule/week

2. Демо-элементы для тестирования:

# Тестовая карточка
curl -X POST http://localhost:8000/demo/create-simple-card

# Тестовый текст
curl -X POST http://localhost:8000/demo/create-simple-text


Примеры использования

Пример 1: Создание расписания на понедельник
1. Создаем фрейм для понедельника
curl -X POST http://localhost:8000/frames \
  -H "Content-Type: application/json" \
  -d '{
    "day_name": "Понедельник",
    "position": {"x": 0, "y": 0},
    "width": 400,
    "height": 1200,
    "fill_color": "#F8F9FA"
  }'

Сохраняем frame_id из ответа, например: "uXjV1234567890"

2. Добавляем пары в понедельник
curl -X POST http://localhost:8000/lectures \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Математика",
    "description": "Дифференциальные уравнения",
    "time": "9:00-10:30",
    "classroom": "301",
    "teacher": "Проф. Иванов И.И.",
    "subject_type": "lecture",
    "position": {"x": 0, "y": -400},
    "frame_id": "uXjV1234567890"
  }'

curl -X POST http://localhost:8000/lectures \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Физика",
    "description": "Механика",
    "time": "11:00-12:30",
    "classroom": "415",
    "teacher": "Доц. Петрова А.С.",
    "subject_type": "practice",
    "position": {"x": 0, "y": -200},
    "frame_id": "uXjV1234567890"
  }'
```

Пример 2: Создание полного расписания на неделю
1. Создаем структуру недели
curl -X POST http://localhost:8000/schedule/week
2. Получаем frame_id из ответа для каждого дня
3. Добавляем пары в каждый день аналогично Примеру 1

Типы занятий и цвета

API автоматически применяет цветовую схему по типу занятия:

- `lecture` - Лекция (#E3F2FD, светло-синий)
- `practice` - Практика (#E8F5E9, светло-зеленый)
- `laboratory` - Лабораторная (#FFF3E0, светло-оранжевый)
- `seminar` - Семинар (#F3E5F5, светло-фиолетовый)
- `exam` - Экзамен (#FFEBEE, светло-красный)

Ограничения Miro API

- Минимальная ширина карточки: 256px
- Минимальная высота карточки: 50px
- Максимальная длина заголовка: 500 символов
- Максимальная длина описания: 5000 символов
- Размер шрифта: от 1 до 200

Устранение неполадок

Ошибка 401: Unauthorized
- Проверьте правильность MIRO_ACCESS_TOKEN в .env файле
- Убедитесь, что токен не истек
- Проверьте, есть ли у токена права на запись

Ошибка 400: Invalid parameters
- Проверьте, что ширина карточки ≥ 256px
- Убедитесь, что длина заголовка ≤ 500 символов
- Для карточек не используйте textAlign в стиле

Проверка подключения
curl http://localhost:8000/test/connection

Структура проекта

board_miro_API/
├── main.py              # Основной файл FastAPI приложения
├── requirements.txt     # Зависимости Python
├── .env                # Переменные окружения (не добавлять в git)
├── .gitignore          # Игнорируемые файлы
└── README.md           # Документация

Зависимости

- FastAPI - веб-фреймворк
- Uvicorn - ASGI сервер
- HTTPX - HTTP клиент
- Pydantic - валидация данных
