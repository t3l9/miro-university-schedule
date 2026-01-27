Miro University Schedule API

Описание проекта
[/b] FastAPI приложение для создания и управления онлайн-расписанием университета на платформе Miro. API позволяет автоматически создавать структуру расписания, добавлять учебные пары, управлять элементами доски через RESTful интерфейс. [b]

Основные возможности
- Создание текстовых элементов на доске
- Создание карточек (учебных пар) с цветовой кодировкой по типу занятия
- Создание фреймов для дней недели
- Получение информации об элементах доски
- Удаление элементов с доски
- Автоматическая организация расписания

Технологии
- Python 3.8+
- FastAPI
- HTTPX для асинхронных запросов
- Pydantic для валидации данных
- Miro REST API v2

Установка и запуск

#1. Установка зависимостей
```bash
# Установите Python 3.8 или выше
# Создайте виртуальное окружение
python -m venv venv

# Активация на Windows:
venv\Scripts\activate

# Активация на Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

#2. Настройка Miro API
1. Зарегистрируйтесь на miro.com
2. Перейдите на developers.miro.com
3. Создайте новое приложение (Create app)
4. Сгенерируйте Access Token с правами:
   - boards:read
   - boards:write
   - team:read
5. Создайте доску в Miro или используйте существующую
6. Скопируйте Board ID из URL доски

#3. Конфигурация
Создайте файл .env в корне проекта:
```
MIRO_ACCESS_TOKEN=ваш_токен_здесь
MIRO_BOARD_ID=ваш_board_id_здесь
```

#4. Запуск сервера
```bash
python main.py
# Или
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

После запуска документация API будет доступна по адресу:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

Использование API

#Создание элементов

##1. Текстовые элементы
```bash
curl -X POST http://localhost:8000/texts \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Расписание университета",
    "position": {"x": 0, "y": -600},
    "font_size": 36,
    "color": "#1976D2"
  }'
```

##2. Карточки (учебные пары)
```bash
curl -X POST http://localhost:8000/lectures \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Программирование",
    "description": "Основы Python",
    "time": "9:00-10:30",
    "classroom": "101",
    "teacher": "Иванов И.И.",
    "subject_type": "lecture",
    "position": {"x": 0, "y": 0}
  }'
```

##3. Фреймы дней недели
```bash
curl -X POST http://localhost:8000/frames \
  -H "Content-Type: application/json" \
  -d '{
    "day_name": "Понедельник",
    "position": {"x": 0, "y": 0},
    "width": 400,
    "height": 1200,
    "fill_color": "#F8F9FA"
  }'
```

#Получение информации

##1. Получить все элементы доски
```bash
curl http://localhost:8000/board/items
```

##2. Получить только фреймы
```bash
curl http://localhost:8000/board/frames
```

##3. Получить информацию об элементе по ID
```bash
curl http://localhost:8000/board/items/3458764657216552895
```

#Управление элементами

##1. Удалить элемент по ID
```bash
curl -X DELETE http://localhost:8000/board/items/3458764657216552895
```

##2. Очистить тестовые элементы
```bash
curl -X DELETE http://localhost:8000/board/cleanup/test-items
```

#Тестовые эндпоинты

##1. Тест создания карточки без фрейма
```bash
curl -X POST http://localhost:8000/test/create-card-no-frame
```

##2. Тест создания карточки внутри фрейма
```bash
curl -X POST http://localhost:8000/test/create-card-with-real-frame
```

Типы занятий и цвета

API автоматически применяет цветовую схему:
- Лекция: #E3F2FD (светло-синий)
- Практика: #E8F5E9 (светло-зеленый)
- Лабораторная: #FFF3E0 (светло-оранжевый)
- Семинар: #F3E5F5 (светло-фиолетовый)
- Экзамен: #FFEBEE (светло-красный)

Ограничения Miro API

При работе с API учтите ограничения Miro:
- Ширина карточки: минимум 256px
- Высота карточки: минимум 50px
- Длина заголовка: до 500 символов
- Длина описания: до 5000 символов
- Размер шрифта: от 1 до 200 (целое число)
- Максимальное количество элементов в запросе: 50

Пример создания полного расписания

1. Создайте фреймы для дней недели:
```bash
for day in "Понедельник" "Вторник" "Среда" "Четверг" "Пятница" "Суббота"; do
  curl -X POST http://localhost:8000/frames \
    -H "Content-Type: application/json" \
    -d "{
      \"day_name\": \"$day\",
      \"position\": {\"x\": 0, \"y\": 0},
      \"width\": 400,
      \"height\": 1200,
      \"fill_color\": \"#F8F9FA\"
    }"
done
```

2. Получите ID созданных фреймов:
```bash
curl http://localhost:8000/board/frames
```

3. Добавьте пары в соответствующие дни:
```bash
curl -X POST http://localhost:8000/lectures \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Математика",
    "description": "Лекция по алгебре",
    "time": "9:00-10:30",
    "classroom": "301",
    "teacher": "Проф. Иванов И.И.",
    "subject_type": "lecture",
    "position": {"x": 0, "y": 0},
    "frame_id": "3458764657216552883"
  }'
```

Структура проекта
```
board_miro_API/
├── main.py              # Основное приложение FastAPI
├── requirements.txt     # Зависимости Python
├── .env                # Конфигурационные переменные
├── .gitignore          # Игнорируемые файлы
└── README.md           # Документация
```

Зависимости
В файле requirements.txt:
```
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.0
pydantic==2.5.0
python-dotenv==1.0.0
```

Устранение проблем

#Ошибка 401: Unauthorized
Проверьте:
1. Правильность MIRO_ACCESS_TOKEN в .env файле
2. Срок действия токена (токены Miro действительны 1 год)
3. Наличие необходимых прав у токена

#Ошибка 400: Invalid parameters
Проверьте:
1. Ширина карточки ≥ 256px
2. Высота карточки ≥ 50px
3. font_size - целое число от 1 до 200
4. Для карточек внутри фрейма используйте относительные координаты

#Карточка создается вне фрейма
При указании frame_id используйте относительные координаты:
- x: 0, y: 0 - центр фрейма
- x: 0, y: -100 - 100px выше центра фрейма

Безопасность
- Никогда не коммитьте .env файл в Git
- Используйте переменные окружения на продакшн серверах
- Ограничьте доступ к API при развертывании в продакшн

Лицензия
MIT License

