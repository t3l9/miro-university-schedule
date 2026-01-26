API для управления онлайн-расписанием университета на интерактивной доске Miro. Создавайте, редактируйте и визуализируйте расписание пар с цветовым кодированием.

✨ Основные возможности

- **Структура недели** – автоматическое создание дней недели на доске
- **Управление занятиями** – добавление лекций, практик, лабораторных
- **Гибкое редактирование** – изменение и удаление элементов
- **Умный поиск** – поиск пар по названию, преподавателю, аудитории
- **Визуальное кодирование** – цветовые метки для разных типов занятий
- **Drag & Drop** – все элементы можно перемещать на доске Miro

🚀 Быстрый старт

Предварительные требования

1. **Аккаунт Miro** с доступом к [REST API](https://developers.miro.com)
2. **Токен доступа** (Access Token) – получить в [панели разработчика Miro](https://developers.miro.com/docs/rest-api-build-your-first-hello-world-app#step-3-get-your-access-token)
3. **ID доски** – из URL: `https://miro.com/app/board/**THIS_IS_BOARD_ID**/`

Установка и запуск

```bash
# 1. Клонируйте репозиторий
git clone <your-repo-url>
cd miro-university-schedule

# 2. Создайте виртуальное окружение
python -m venv venv

# 3. Активируйте окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Установите зависимости
pip install -r requirements.txt

# 5. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env файл:
# MIRO_TOKEN=ваш_токен_доступа
# MIRO_BOARD_ID=id_вашей_доски

# 6. Запустите приложение
python run.py
# Или с помощью uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

После запуска откройте в браузере: [http://localhost:8000/docs](http://localhost:8000/docs) для доступа к Swagger UI.

## 📚 Использование API

### 1. Инициализация расписания
Создает структуру дней недели на доске Miro:
```http
POST /schedule/week
```

### 2. Добавление учебной пары
```http
POST /lectures
```
```json
{
  "title": "Программирование на Python",
  "description": "Основы синтаксиса и структуры данных",
  "time": "9:00-10:30",
  "classroom": "Компьютерный класс 101",
  "teacher": "Доц. Сидоров П.П.",
  "subject_type": "practice",
  "position": {
    "x": 0,
    "y": -400
  }
}
```

**Типы занятий:** `lecture`, `practice`, `lab`, `seminar`, `exam`

### 3. Поиск по расписанию
```http
GET /schedule/search?query=программирование
```

### 4. Получение всех пар дня
```http
GET /schedule/day/{day}
```
где `day`: `monday`, `tuesday`, ..., `friday`

### 5. Удаление пары
```http
DELETE /lectures/{lecture_id}
```

🎨 Цветовое кодирование

Каждый тип занятия имеет свой цвет на доске:
- 🟦 **Лекция** – синий
- 🟩 **Практика** – зеленый
- 🟨 **Лабораторная** – желтый
- 🟪 **Семинар** – фиолетовый
- 🟥 **Экзамен** – красный

📁 Структура проекта

```
miro-university-schedule/
├── main.py              # Основное приложение FastAPI
├── run.py              # Точка входа
├── requirements.txt    # Зависимости
├── .env.example        # Пример переменных окружения

├── README.md          # Документация
