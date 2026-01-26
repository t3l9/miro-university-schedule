from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import httpx
import os
from dotenv import load_dotenv
from enum import Enum

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(
    title="University Schedule Miro API",
    description="API для управления онлайн-расписанием университета на платформе Miro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация
MIRO_ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN", "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_jv_4496uBs-n-_IIAiR3z3Bit2E")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID", "uXjVGKH6bkY")
MIRO_API_BASE_URL = "https://api.miro.com/v2"

# Модели данных
class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class SubjectType(str, Enum):
    LECTURE = "lecture"
    PRACTICE = "practice"
    LABORATORY = "laboratory"
    SEMINAR = "seminar"
    EXAM = "exam"

class Position(BaseModel):
    """Модель для позиции на доске"""
    x: float = Field(..., description="X координата")
    y: float = Field(..., description="Y координата")

class CreateFrameRequest(BaseModel):
    """Запрос на создание фрейма дня"""
    day_name: str = Field(..., description="Название дня недели")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    width: float = Field(default=800, description="Ширина фрейма")
    height: float = Field(default=1000, description="Высота фрейма")
    color: str = Field(default="#E6F2FF", description="Цвет фона")

class CreateLectureRequest(BaseModel):
    """Запрос на создание карточки с парой"""
    title: str = Field(..., description="Название предмета")
    description: str = Field(..., description="Описание")
    time: str = Field(..., description="Время проведения (например, 9:00-10:30)")
    classroom: str = Field(..., description="Аудитория")
    teacher: str = Field(..., description="Преподаватель")
    subject_type: SubjectType = Field(default=SubjectType.LECTURE, description="Тип занятия")
    frame_id: Optional[str] = Field(None, description="ID фрейма дня (если есть)")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    width: float = Field(default=200, description="Ширина карточки")
    height: float = Field(default=150, description="Высота карточки")

class CreateTextRequest(BaseModel):
    """Запрос на создание текстового элемента"""
    content: str = Field(..., description="Текст")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доски")
    font_size: str = Field(default="14px", description="Размер шрифта")
    color: str = Field(default="#000000", description="Цвет текста")

class UpdateLectureRequest(BaseModel):
    """Запрос на обновление карточки"""
    title: Optional[str] = None
    description: Optional[str] = None
    time: Optional[str] = None
    classroom: Optional[str] = None
    teacher: Optional[str] = None
    subject_type: Optional[SubjectType] = None
    color: Optional[str] = None

class DaySchedule(BaseModel):
    """Модель расписания на день"""
    day: DayOfWeek
    frame_id: Optional[str] = None
    lectures: List[Dict[str, Any]] = []

class WeekSchedule(BaseModel):
    """Модель расписания на неделю"""
    board_id: str
    days: List[DaySchedule] = []

class MiroItemResponse(BaseModel):
    """Базовая модель ответа Miro"""
    id: str
    type: str
    data: Dict[str, Any]
    position: Dict[str, float]
    geometry: Optional[Dict[str, float]] = None
    created_at: Optional[str] = None
    created_by: Optional[Dict[str, Any]] = None
    modified_at: Optional[str] = None
    modified_by: Optional[Dict[str, Any]] = None

# Клиент для работы с Miro API
class MiroClient:
    def __init__(self):
        self.base_url = MIRO_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """Универсальный метод для выполнения запросов"""
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Miro API error: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Request error: {str(e)}"
                )
    
    async def create_frame(self, board_id: str, frame_data: Dict) -> Dict:
        """Создание фрейма"""
        return await self._make_request("POST", f"boards/{board_id}/frames", json=frame_data)
    
    async def create_card(self, board_id: str, card_data: Dict) -> Dict:
        """Создание карточки"""
        return await self._make_request("POST", f"boards/{board_id}/cards", json=card_data)
    
    async def create_text(self, board_id: str, text_data: Dict) -> Dict:
        """Создание текстового элемента"""
        return await self._make_request("POST", f"boards/{board_id}/texts", json=text_data)
    
    async def create_shape(self, board_id: str, shape_data: Dict) -> Dict:
        """Создание фигуры"""
        return await self._make_request("POST", f"boards/{board_id}/shapes", json=shape_data)
    
    async def get_board_items(self, board_id: str, limit: int = 50) -> Dict:
        """Получение всех элементов доски"""
        return await self._make_request("GET", f"boards/{board_id}/items?limit={limit}")
    
    async def get_item(self, board_id: str, item_id: str) -> Dict:
        """Получение конкретного элемента"""
        return await self._make_request("GET", f"boards/{board_id}/items/{item_id}")
    
    async def update_card(self, board_id: str, item_id: str, update_data: Dict) -> Dict:
        """Обновление карточки"""
        return await self._make_request("PATCH", f"boards/{board_id}/cards/{item_id}", json=update_data)
    
    async def delete_item(self, board_id: str, item_id: str) -> None:
        """Удаление элемента"""
        await self._make_request("DELETE", f"boards/{board_id}/items/{item_id}")
    
    async def search_items(self, board_id: str, query: str) -> Dict:
        """Поиск элементов на доске"""
        return await self._make_request("GET", f"boards/{board_id}/items?query={query}")

# Dependency для клиента Miro
async def get_miro_client():
    return MiroClient()

# Цветовая схема для предметов
SUBJECT_COLORS = {
    SubjectType.LECTURE: "#E3F2FD",      # светло-синий
    SubjectType.PRACTICE: "#E8F5E9",     # светло-зеленый
    SubjectType.LABORATORY: "#FFF3E0",   # светло-оранжевый
    SubjectType.SEMINAR: "#F3E5F5",      # светло-фиолетовый
    SubjectType.EXAM: "#FFEBEE"          # светло-красный
}

DAY_NAMES_RU = {
    DayOfWeek.MONDAY: "Понедельник",
    DayOfWeek.TUESDAY: "Вторник",
    DayOfWeek.WEDNESDAY: "Среда",
    DayOfWeek.THURSDAY: "Четверг",
    DayOfWeek.FRIDAY: "Пятница",
    DayOfWeek.SATURDAY: "Суббота",
    DayOfWeek.SUNDAY: "Воскресенье"
}

# ========== API ЭНДПОИНТЫ ==========

@app.get("/", tags=["Root"])
async def root():
    """
    Корневой эндпоинт API
    """
    return {
        "message": "University Schedule Miro API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "active"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Проверка здоровья API
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/frames", response_model=MiroItemResponse, tags=["Frames"], status_code=status.HTTP_201_CREATED)
async def create_frame(
    request: CreateFrameRequest,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Создание фрейма для дня недели на доске Miro
    
    - **day_name**: Название дня недели
    - **position**: Позиция на доске (x, y)
    - **width**: Ширина фрейма
    - **height**: Высота фрейма
    - **color**: Цвет фона фрейма
    """
    frame_data = {
        "data": {
            "title": request.day_name,
            "style": {
                "fillColor": request.color
            }
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "geometry": {
            "width": request.width,
            "height": request.height
        }
    }
    
    response = await miro.create_frame(MIRO_BOARD_ID, frame_data)
    return response

@app.post("/lectures", response_model=MiroItemResponse, tags=["Lectures"], status_code=status.HTTP_201_CREATED)
async def create_lecture(
    request: CreateLectureRequest,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Создание карточки с учебной парой
    
    - **title**: Название предмета
    - **description**: Описание занятия
    - **time**: Время проведения
    - **classroom**: Аудитория
    - **teacher**: Преподаватель
    - **subject_type**: Тип занятия (лекция, практика и т.д.)
    - **frame_id**: ID фрейма дня (опционально)
    - **position**: Позиция на доске
    - **width**: Ширина карточки
    - **height**: Высота карточки
    """
    # Формируем полное описание
    full_description = f"""
    Время: {request.time}
    Аудитория: {request.classroom}
    Преподаватель: {request.teacher}
    Тип: {request.subject_type.value}
    
    {request.description}
    """.strip()
    
    card_data = {
        "data": {
            "title": request.title,
            "description": full_description,
            "style": {
                "fillColor": SUBJECT_COLORS.get(request.subject_type, "#FFFFFF"),
                "textAlign": "left",
                "borderColor": "#000000",
                "borderWidth": "1px",
                "borderStyle": "solid"
            }
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "geometry": {
            "width": request.width,
            "height": request.height
        }
    }
    
    # Если указан frame_id, добавляем родительский элемент
    if request.frame_id:
        card_data["parent"] = {"id": request.frame_id}
    
    response = await miro.create_card(MIRO_BOARD_ID, card_data)
    return response

@app.post("/texts", response_model=MiroItemResponse, tags=["Text"], status_code=status.HTTP_201_CREATED)
async def create_text_element(
    request: CreateTextRequest,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Создание текстового элемента на доске
    
    - **content**: Текст для отображения
    - **position**: Позиция на доске
    - **font_size**: Размер шрифта
    - **color**: Цвет текста
    """
    text_data = {
        "data": {
            "content": request.content,
            "style": {
                "color": request.color,
                "fontSize": request.font_size,
                "textAlign": "center"
            }
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        }
    }
    
    response = await miro.create_text(MIRO_BOARD_ID, text_data)
    return response

@app.get("/board/items", response_model=Dict[str, Any], tags=["Board"])
async def get_board_items(
    limit: int = 50,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Получение всех элементов с доски
    
    - **limit**: Максимальное количество элементов (по умолчанию 50)
    """
    response = await miro.get_board_items(MIRO_BOARD_ID, limit)
    return response

@app.get("/board/items/{item_id}", response_model=MiroItemResponse, tags=["Board"])
async def get_item_by_id(
    item_id: str,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Получение конкретного элемента по ID
    
    - **item_id**: ID элемента на доске Miro
    """
    response = await miro.get_item(MIRO_BOARD_ID, item_id)
    return response

@app.patch("/lectures/{item_id}", response_model=MiroItemResponse, tags=["Lectures"])
async def update_lecture(
    item_id: str,
    request: UpdateLectureRequest,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Обновление информации о паре (лекции)
    
    - **item_id**: ID карточки на доске
    - Можно обновлять: title, description, time, classroom, teacher, subject_type, color
    """
    update_data = {}
    
    if request.title or request.description or request.time or request.classroom or request.teacher:
        # Если обновляются основные поля, нужно пересоздать описание
        # Сначала получим текущую карточку
        current_item = await miro.get_item(MIRO_BOARD_ID, item_id)
        current_data = current_item.get("data", {})
        
        title = request.title or current_data.get("title", "")
        description = request.description or current_data.get("description", "")
        time = request.time or ""
        classroom = request.classroom or ""
        teacher = request.teacher or ""
        subject_type = request.subject_type or SubjectType.LECTURE
        
        full_description = f"""
        Время: {time}
        Аудитория: {classroom}
        Преподаватель: {teacher}
        Тип: {subject_type.value}
        
        {description}
        """.strip()
        
        update_data["data"] = {
            "title": title,
            "description": full_description
        }
    
    if request.subject_type or request.color:
        style_data = update_data.get("data", {}).get("style", {})
        if request.subject_type:
            style_data["fillColor"] = SUBJECT_COLORS.get(request.subject_type, "#FFFFFF")
        if request.color:
            style_data["fillColor"] = request.color
        
        if "data" not in update_data:
            update_data["data"] = {}
        update_data["data"]["style"] = style_data
    
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )
    
    response = await miro.update_card(MIRO_BOARD_ID, item_id, update_data)
    return response

@app.delete("/board/items/{item_id}", tags=["Board"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Удаление элемента с доски
    
    - **item_id**: ID элемента для удаления
    """
    await miro.delete_item(MIRO_BOARD_ID, item_id)
    return {"message": "Item deleted successfully"}

@app.post("/schedule/week", response_model=WeekSchedule, tags=["Schedule"], status_code=status.HTTP_201_CREATED)
async def create_week_schedule(
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Создание полной структуры расписания на неделю
    
    Создает 6 фреймов (пн-сб) с разметкой для расписания
    """
    days_of_week = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
        DayOfWeek.SATURDAY
    ]
    
    week_schedule = WeekSchedule(board_id=MIRO_BOARD_ID, days=[])
    x_position = 0
    
    for day in days_of_week:
        # Создаем фрейм для дня
        frame_request = CreateFrameRequest(
            day_name=DAY_NAMES_RU[day],
            position=Position(x=x_position, y=0),
            width=350,
            height=1200,
            color="#F5F5F5"
        )
        
        frame_response = await create_frame(frame_request, miro)
        
        # Добавляем заголовок дня внутри фрейма
        text_request = CreateTextRequest(
            content=f"📅 {DAY_NAMES_RU[day].upper()}",
            position=Position(x=x_position, y=-550),
            font_size="24px",
            color="#1976D2"
        )
        await create_text_element(text_request, miro)
        
        # Создаем временные метки
        times = ["9:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00"]
        for i, time in enumerate(times):
            time_text_request = CreateTextRequest(
                content=f"🕐 {time}",
                position=Position(x=x_position - 150, y=-450 + (i * 180)),
                font_size="12px",
                color="#666666"
            )
            await create_text_element(time_text_request, miro)
        
        day_schedule = DaySchedule(
            day=day,
            frame_id=frame_response["id"],
            lectures=[]
        )
        week_schedule.days.append(day_schedule)
        
        x_position += 400  # Сдвигаем следующий день
    
    return week_schedule

@app.post("/schedule/day/{day}", response_model=Dict[str, Any], tags=["Schedule"])
async def add_lectures_to_day(
    day: DayOfWeek,
    lectures: List[CreateLectureRequest],
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Добавление нескольких пар в конкретный день
    
    - **day**: День недели
    - **lectures**: Список пар для добавления
    """
    # Сначала найдем фрейм дня
    board_items = await miro.get_board_items(MIRO_BOARD_ID, limit=100)
    day_frame = None
    
    for item in board_items.get("data", []):
        if item.get("type") == "frame" and DAY_NAMES_RU[day] in item.get("data", {}).get("title", ""):
            day_frame = item
            break
    
    if not day_frame:
        raise HTTPException(
            status_code=404,
            detail=f"Frame for {DAY_NAMES_RU[day]} not found"
        )
    
    created_lectures = []
    base_y = day_frame.get("position", {}).get("y", 0) - 400
    
    for i, lecture in enumerate(lectures):
        # Позиционируем пары вертикально
        lecture.position = Position(
            x=day_frame.get("position", {}).get("x", 0),
            y=base_y + (i * 200)
        )
        lecture.frame_id = day_frame["id"]
        
        response = await create_lecture(lecture, miro)
        created_lectures.append({
            "id": response["id"],
            "title": lecture.title,
            "time": lecture.time
        })
    
    return {
        "day": DAY_NAMES_RU[day],
        "frame_id": day_frame["id"],
        "created_lectures": created_lectures,
        "count": len(created_lectures)
    }

@app.get("/schedule/search", tags=["Schedule"])
async def search_schedule(
    query: str,
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Поиск пар по названию предмета, преподавателю или аудитории
    
    - **query**: Поисковый запрос
    """
    response = await miro.search_items(MIRO_BOARD_ID, query)
    
    # Фильтруем только карточки (пары)
    lectures = []
    for item in response.get("data", []):
        if item.get("type") == "card":
            lectures.append({
                "id": item.get("id"),
                "title": item.get("data", {}).get("title"),
                "description": item.get("data", {}).get("description"),
                "position": item.get("position")
            })
    
    return {
        "query": query,
        "found": len(lectures),
        "lectures": lectures
    }

@app.post("/schedule/template/math-week", tags=["Templates"])
async def create_math_week_template(
    miro: MiroClient = Depends(get_miro_client)
):
    """
    Создание шаблонного расписания для математического факультета
    """
    # Создаем структуру недели
    await create_week_schedule(miro)
    
    # Пример расписания для понедельника
    monday_lectures = [
        CreateLectureRequest(
            title="Высшая математика",
            description="Дифференциальные уравнения",
            time="9:00-10:30",
            classroom="301",
            teacher="Проф. Иванов И.И.",
            subject_type=SubjectType.LECTURE,
            position=Position(x=0, y=-400)
        ),
        CreateLectureRequest(
            title="Алгебра",
            description="Линейная алгебра",
            time="11:00-12:30",
            classroom="415",
            teacher="Доц. Петрова А.С.",
            subject_type=SubjectType.PRACTICE,
            position=Position(x=0, y=-200)
        )
    ]
    
    await add_lectures_to_day(DayOfWeek.MONDAY, monday_lectures, miro)
    
    return {
        "message": "Math week template created successfully",
        "schedule": {
            "monday": ["Высшая математика", "Алгебра"],
            "tuesday": [],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "saturday": []
        }
    }

# Кастомная конфигурация Swagger
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="University Schedule Miro API",
        version="1.0.0",
        description="""
        API для управления онлайн-расписанием университета на платформе Miro
        
        Основные возможности:
        
        - 🎯 Создание структуры расписания (дни недели)
        - 📚 Добавление учебных пар (лекций, практик и т.д.)
        - ✏️ Редактирование и удаление элементов
        - 🔍 Поиск по расписанию
        - 🎨 Цветовое кодирование по типу занятий
        
        Требования:
        
        1. Токен доступа Miro (в .env файле)
        2. ID доски Miro
        3. Права на редактирование доски
        
        Примеры цветов для типов занятий:
        
        |   Тип    |   Цвет   |
        |----------|----------|
        | Лекция   | #E3F2FD |
        | Практика | #E8F5E9 |
        | Лаб.     | #FFF3E0 |
        | Семинар  | #F3E5F5 |
        | Экзамен  | #FFEBEE |
        """,
        routes=app.routes,
    )
    
    # Добавляем информацию о серверах
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Локальный сервер разработки"
        },
        {
            "url": "https://your-domain.com/api",
            "description": "Продакшн сервер"
        }
    ]
    
    # Добавляем теги для лучшей организации
    openapi_schema["tags"] = [
        {"name": "Root", "description": "Базовые эндпоинты"},
        {"name": "Health", "description": "Проверка здоровья API"},
        {"name": "Frames", "description": "Управление фреймами дней недели"},
        {"name": "Lectures", "description": "Управление учебными парами"},
        {"name": "Text", "description": "Работа с текстовыми элементами"},
        {"name": "Board", "description": "Общие операции с доской"},
        {"name": "Schedule", "description": "Управление расписанием"},
        {"name": "Templates", "description": "Шаблоны расписаний"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )