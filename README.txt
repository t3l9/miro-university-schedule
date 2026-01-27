```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        
        .container {
            background-color: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            border-bottom: 3px solid #4a6ee0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        h2 {
            color: #3498db;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }
        
        h3 {
            color: #2c3e50;
            margin-top: 25px;
        }
        
        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        .badge-fastapi { background-color: #009688; color: white; }
        .badge-python { background-color: #3776ab; color: white; }
        .badge-miro { background-color: #ffd02f; color: #333; }
        .badge-api { background-color: #6f42c1; color: white; }
        
        .code-block {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
            font-family: 'Consolas', monospace;
            overflow-x: auto;
        }
        
        .code-inline {
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
        }
        
        .endpoint {
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
        }
        
        .method {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
            font-size: 0.8em;
            margin-right: 10px;
        }
        
        .method-get { background-color: #61affe; color: white; }
        .method-post { background-color: #49cc90; color: white; }
        .method-delete { background-color: #f93e3e; color: white; }
        
        .url {
            font-family: 'Consolas', monospace;
            color: #2c3e50;
        }
        
        .color-box {
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 10px;
            vertical-align: middle;
            border: 1px solid #ddd;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .card {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .card h4 {
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #4a6ee0;
            padding-bottom: 10px;
        }
        
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffecb5;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }
        
        .success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }
        
        .info {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        
        tr:hover {
            background-color: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 University Schedule Miro API</h1>
            <p>FastAPI приложение для создания и управления онлайн-расписанием университета на платформе Miro</p>
            <div>
                <span class="badge badge-fastapi">FastAPI</span>
                <span class="badge badge-python">Python 3.8+</span>
                <span class="badge badge-miro">Miro API v2</span>
                <span class="badge badge-api">REST API</span>
            </div>
        </div>
        
        <h2>📋 Оглавление</h2>
        <ul>
            <li><a href="#overview">Обзор проекта</a></li>
            <li><a href="#features">Основные возможности</a></li>
            <li><a href="#setup">Установка и настройка</a></li>
            <li><a href="#api-endpoints">Эндпоинты API</a></li>
            <li><a href="#examples">Примеры использования</a></li>
            <li><a href="#colors">Цветовая схема</a></li>
            <li><a href="#limitations">Ограничения</a></li>
            <li><a href="#troubleshooting">Устранение проблем</a></li>
        </ul>
        
        <h2 id="overview">🚀 Обзор проекта</h2>
        <p>API для автоматического создания и управления онлайн-расписанием университета на интерактивных досках Miro. Позволяет программно создавать структуру недели, добавлять учебные пары с цветовой кодировкой и управлять элементами через RESTful интерфейс.</p>
        
        <div class="info">
            <strong>📊 Основные преимущества:</strong>
            <ul>
                <li>Автоматическое создание структуры расписания</li>
                <li>Цветовая кодировка по типам занятий</li>
                <li>Поддержка фреймов для дней недели</li>
                <li>Полный CRUD для элементов доски</li>
                <li>Автоматическая документация Swagger</li>
            </ul>
        </div>
        
        <h2 id="features">✨ Основные возможности</h2>
        <div class="grid">
            <div class="card">
                <h4>📝 Создание элементов</h4>
                <ul>
                    <li>Текстовые элементы</li>
                    <li>Карточки учебных пар</li>
                    <li>Фреймы дней недели</li>
                    <li>Автоматическое позиционирование</li>
                </ul>
            </div>
            
            <div class="card">
                <h4>🎨 Умные функции</h4>
                <ul>
                    <li>Цветовая кодировка по типам занятий</li>
                    <li>Относительное позиционирование</li>
                    <li>Автоматическое форматирование</li>
                    <li>Валидация параметров</li>
                </ul>
            </div>
            
            <div class="card">
                <h4>🛠️ Управление</h4>
                <ul>
                    <li>Получение информации об элементах</li>
                    <li>Удаление элементов</li>
                    <li>Очистка тестовых данных</li>
                    <li>Поиск фреймов</li>
                </ul>
            </div>
        </div>
        
        <h2 id="setup">⚙️ Установка и настройка</h2>
        
        <h3>1. Предварительные требования</h3>
        <div class="code-block">
# Проверьте версию Python
python --version
# Должно быть Python 3.8 или выше
        </div>
        
        <h3>2. Установка зависимостей</h3>
        <div class="code-block">
# Клонируйте репозиторий
git clone https://github.com/ваш-репозиторий/board_miro_API.git
cd board_miro_API

# Создайте виртуальное окружение
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
        </div>
        
        <h3>3. Настройка Miro API</h3>
        <div class="warning">
            <strong>Важно:</strong> Для работы API необходим токен доступа Miro
        </div>
        
        <ol>
            <li>Зарегистрируйтесь на <a href="https://miro.com">miro.com</a></li>
            <li>Перейдите на <a href="https://developers.miro.com">developers.miro.com</a></li>
            <li>Создайте новое приложение (Create app)</li>
            <li>Сгенерируйте Access Token с правами:
                <ul>
                    <li><code>boards:read</code></li>
                    <li><code>boards:write</code></li>
                    <li><code>team:read</code></li>
                </ul>
            </li>
            <li>Скопируйте Board ID из URL вашей доски</li>
        </ol>
        
        <h3>4. Конфигурация</h3>
        <p>Создайте файл <span class="code-inline">.env</span> в корне проекта:</p>
        <div class="code-block">
MIRO_ACCESS_TOKEN=ваш_токен_здесь
MIRO_BOARD_ID=ваш_board_id_здесь
        </div>
        
        <h3>5. Запуск сервера</h3>
        <div class="code-block">
# Запуск через Python
python main.py

# Или через Uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
        </div>
        
        <div class="success">
            <strong>✅ Сервер запущен!</strong>
            <p>Документация API доступна по адресам:</p>
            <ul>
                <li><a href="http://localhost:8000/docs">http://localhost:8000/docs</a> (Swagger UI)</li>
                <li><a href="http://localhost:8000/redoc">http://localhost:8000/redoc</a> (ReDoc)</li>
            </ul>
        </div>
        
        <h2 id="api-endpoints">🔌 Эндпоинты API</h2>
        
        <h3>Создание элементов</h3>
        
        <div class="endpoint">
            <span class="method method-post">POST</span>
            <span class="url">/texts</span>
            <p><strong>Создание текстового элемента</strong></p>
            <p>Параметры: content, position, font_size, color, text_align</p>
        </div>
        
        <div class="endpoint">
            <span class="method method-post">POST</span>
            <span class="url">/cards</span>
            <p><strong>Создание карточки</strong></p>
            <p>Параметры: title, description, position, width, height, fill_color, frame_id</p>
        </div>
        
        <div class="endpoint">
            <span class="method method-post">POST</span>
            <span class="url">/lectures</span>
            <p><strong>Создание учебной пары</strong></p>
            <p>Автоматическое применение цветовой схемы по типу занятия</p>
        </div>
        
        <div class="endpoint">
            <span class="method method-post">POST</span>
            <span class="url">/frames</span>
            <p><strong>Создание фрейма дня недели</strong></p>
            <p>Параметры: day_name, position, width, height, fill_color</p>
        </div>
        
        <h3>Чтение данных</h3>
        
        <div class="endpoint">
            <span class="method method-get">GET</span>
            <span class="url">/board/items</span>
            <p><strong>Получение всех элементов доски</strong></p>
            <p>Опциональный параметр: limit (макс. 50)</p>
        </div>
        
        <div class="endpoint">
            <span class="method method-get">GET</span>
            <span class="url">/board/frames</span>
            <p><strong>Получение только фреймов</strong></p>
            <p>Полезно для получения ID фреймов</p>
        </div>
        
        <div class="endpoint">
            <span class="method method-get">GET</span>
            <span class="url">/board/items/{item_id}</span>
            <p><strong>Информация о конкретном элементе</strong></p>
        </div>
        
        <h3>Управление элементами</h3>
        
        <div class="endpoint">
            <span class="method method-delete">DELETE</span>
            <span class="url">/board/items/{item_id}</span>
            <p><strong>Удаление элемента по ID</strong></p>
        </div>
        
        <div class="endpoint">
            <span class="method method-delete">DELETE</span>
            <span class="url">/board/cleanup/test-items</span>
            <p><strong>Очистка тестовых элементов</strong></p>
            <p>Автоматически удаляет элементы с ключевыми словами "тест", "demo"</p>
        </div>
        
        <h2 id="examples">💡 Примеры использования</h2>
        
        <h3>Пример 1: Создание учебной пары</h3>
        <div class="code-block">
curl -X POST "http://localhost:8000/lectures" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Программирование на Python",
    "description": "Основы языка Python: переменные, типы данных, функции",
    "time": "9:00-10:30",
    "classroom": "Компьютерный класс 101",
    "teacher": "Профессор Иванов И.И.",
    "subject_type": "lecture",
    "position": {
      "x": 0,
      "y": 0
    }
  }'
        </div>
        
        <h3>Пример 2: Создание структуры недели</h3>
        <div class="code-block">
# 1. Создаем фреймы для дней недели
curl -X POST "http://localhost:8000/frames" \
  -H "Content-Type: application/json" \
  -d '{
    "day_name": "Понедельник",
    "position": {"x": 0, "y": 0},
    "width": 400,
    "height": 1200,
    "fill_color": "#F8F9FA"
  }'

# 2. Получаем ID созданного фрейма
curl "http://localhost:8000/board/frames"

# 3. Добавляем пары во фрейм
curl -X POST "http://localhost:8000/lectures" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Математика",
    "description": "Дифференциальные уравнения",
    "time": "9:00-10:30",
    "classroom": "Аудитория 301",
    "teacher": "Доцент Петрова А.С.",
    "subject_type": "lecture",
    "position": {"x": 0, "y": 0},
    "frame_id": "3458764657216552883"
  }'
        </div>
        
        <h2 id="colors">🎨 Цветовая схема</h2>
        <table>
            <thead>
                <tr>
                    <th>Тип занятия</th>
                    <th>Цвет</th>
                    <th>HEX код</th>
                    <th>Пример</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Лекция</strong></td>
                    <td>Светло-синий</td>
                    <td><code>#E3F2FD</code></td>
                    <td><div class="color-box" style="background-color: #E3F2FD;"></div> Основные курсы</td>
                </tr>
                <tr>
                    <td><strong>Практика</strong></td>
                    <td>Светло-зеленый</td>
                    <td><code>#E8F5E9</code></td>
                    <td><div class="color-box" style="background-color: #E8F5E9;"></div> Семинары, упражнения</td>
                </tr>
                <tr>
                    <td><strong>Лабораторная</strong></td>
                    <td>Светло-оранжевый</td>
                    <td><code>#FFF3E0</code></td>
                    <td><div class="color-box" style="background-color: #FFF3E0;"></div> Практические работы</td>
                </tr>
                <tr>
                    <td><strong>Семинар</strong></td>
                    <td>Светло-фиолетовый</td>
                    <td><code>#F3E5F5</code></td>
                    <td><div class="color-box" style="background-color: #F3E5F5;"></div> Обсуждения, доклады</td>
                </tr>
                <tr>
                    <td><strong>Экзамен</strong></td>
                    <td>Светло-красный</td>
                    <td><code>#FFEBEE</code></td>
                    <td><div class="color-box" style="background-color: #FFEBEE;"></div> Зачеты, экзамены</td>
                </tr>
            </tbody>
        </table>
        
        <h2 id="limitations">⚠️ Ограничения Miro API</h2>
        <table>
            <thead>
                <tr>
                    <th>Параметр</th>
                    <th>Минимум</th>
                    <th>Максимум</th>
                    <th>Примечание</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Ширина карточки</strong></td>
                    <td>256px</td>
                    <td>2000px</td>
                    <td>Обязательное ограничение</td>
                </tr>
                <tr>
                    <td><strong>Высота карточки</strong></td>
                    <td>50px</td>
                    <td>2000px</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td><strong>Заголовок</strong></td>
                    <td>1 символ</td>
                    <td>500 символов</td>
                    <td>Автоматически обрезается</td>
                </tr>
                <tr>
                    <td><strong>Описание</strong></td>
                    <td>0 символов</td>
                    <td>5000 символов</td>
                    <td>Автоматически обрезается</td>
                </tr>
                <tr>
                    <td><strong>Размер шрифта</strong></td>
                    <td>1</td>
                    <td>200</td>
                    <td>Только целые числа</td>
                </tr>
                <tr>
                    <td><strong>Элементов в запросе</strong></td>
                    <td>-</td>
                    <td>50</td>
                    <td>Пагинация не поддерживается</td>
                </tr>
            </tbody>
        </table>
        
        <h2 id="troubleshooting">🔧 Устранение проблем</h2>
        
        <div class="warning">
            <strong>Ошибка 401: Unauthorized</strong>
            <p>Проверьте:</p>
            <ol>
                <li>Правильность MIRO_ACCESS_TOKEN в .env файле</li>
                <li>Срок действия токена (действителен 1 год)</li>
                <li>Наличие прав boards:read, boards:write, team:read</li>
            </ol>
        </div>
        
        <div class="warning">
            <strong>Ошибка 400: Invalid parameters</strong>
            <p>Возможные причины:</p>
            <ul>
                <li>Ширина карточки меньше 256px</li>
                <li>Высота карточки меньше 50px</li>
                <li>font_size не целое число</li>
                <li>frame_id содержит "string" вместо числового ID</li>
            </ul>
        </div>
        
        <div class="info">
            <strong>Карточка создается вне фрейма</strong>
            <p>Решение:</p>
            <ul>
                <li>При указании frame_id используйте относительные координаты</li>
                <li><code>x: 0, y: 0</code> - центр фрейма</li>
                <li><code>x: 0, y: -100</code> - 100px выше центра</li>
                <li>Абсолютные координаты игнорируются при наличии родителя</li>
            </ul>
        </div>
        
        <div class="info">
            <strong>Тестовые эндпоинты</strong>
            <p>Для отладки используйте:</p>
            <ul>
                <li><code>GET /test/connection</code> - проверка подключения</li>
                <li><code>POST /test/create-card-no-frame</code> - тест карточки без фрейма</li>
                <li><code>POST /test/create-card-inside-frame-safe</code> - тест карточки во фрейме</li>
            </ul>
        </div>
        
        <h2>📞 Поддержка</h2>
        <p>При возникновении проблем:</p>
        <ol>
            <li>Проверьте логи сервера в консоли</li>
            <li>Используйте тестовые эндпоинты для диагностики</li>
            <li>Убедитесь, что доска существует и доступна</li>
            <li>Проверьте актуальность токена доступа</li>
        </ol>
        
        <div class="success">
            <strong>🎉 Готово к использованию!</strong>
            <p>API полностью настроен и готов к интеграции с системами университета. Используйте Swagger документацию для тестирования всех эндпоинтов.</p>
        </div>
    </div>
</body>
</html>
```
