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
import json

load_dotenv()

app = FastAPI(
    title="University Schedule Miro API",
    description="API для управления онлайн-расписанием университета на платформе Miro",
    version="1.0.4",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MIRO_ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN", "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_jv_4496uBs-n-_IIAiR3z3Bit2E")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID", "uXjVGKH6bkY=")
MIRO_API_BASE_URL = "https://api.miro.com/v2"


# ========== МОДЕЛИ ДАННЫХ ==========

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
    x: float = Field(..., description="X координата")
    y: float = Field(..., description="Y координата")


class CreateTextRequest(BaseModel):
    """Запрос на создание текста"""
    content: str = Field(..., description="Текст")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    font_size: float = Field(default=14, ge=1, le=200, description="Размер шрифта (1-200)")
    color: str = Field(default="#1a1a1a", description="Цвет текста (hex)")
    text_align: str = Field(default="center", description="Выравнивание (left, center, right)")


class CreateCardRequest(BaseModel):
    """Запрос на создание карточки"""
    title: str = Field(..., min_length=1, max_length=500, description="Заголовок карточки")
    description: str = Field(default="", max_length=5000, description="Описание")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    width: float = Field(default=300, ge=256, le=2000, description="Ширина карточки (мин 256)")
    height: float = Field(default=200, ge=50, le=2000, description="Высота карточки (мин 50)")
    fill_color: str = Field(default="#ffffff", description="Цвет фона (hex)")
    frame_id: Optional[str] = Field(None, description="ID родительского фрейма")


class CreateFrameRequest(BaseModel):
    day_name: str = Field(..., description="Название дня недели")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    width: float = Field(default=800, ge=100, le=32767, description="Ширина фрейма")
    height: float = Field(default=1000, ge=100, le=32767, description="Высота фрейма")
    fill_color: str = Field(default="#E6F2FF", description="Цвет фона (hex)")


class CreateLectureRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Название предмета")
    description: str = Field(..., max_length=1000, description="Описание")
    time: str = Field(..., description="Время проведения (например: 9:00-10:30)")
    classroom: str = Field(..., description="Аудитория")
    teacher: str = Field(..., description="Преподаватель")
    subject_type: SubjectType = Field(default=SubjectType.LECTURE, description="Тип занятия")
    position: Position = Field(default=Position(x=0, y=0), description="Позиция на доске")
    frame_id: Optional[str] = Field(None, description="ID фрейма дня")


# ========== ЭНДПОИНТЫ API ==========

@app.post("/texts", tags=["Text"], status_code=status.HTTP_201_CREATED)
async def create_text_element(request: CreateTextRequest):
    """
    Создание текстового элемента на доске Miro

    Ограничения Miro API:
    - font_size: от 1 до 200
    - content: до 5000 символов
    """
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Проверяем и корректируем цвет
    color = request.color.strip()
    if not color.startswith('#'):
        color = f"#{color}"
    if len(color) != 7:  # #RRGGBB
        color = "#1a1a1a"  # fallback

    # Проверяем и корректируем выравнивание
    text_align = request.text_align.lower()
    if text_align not in ["left", "center", "right"]:
        text_align = "center"

    payload = {
        "data": {
            "content": request.content[:5000]  # Ограничение Miro
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "style": {
            "color": color,
            "fontSize": min(max(request.font_size, 1), 200),  # Ограничение 1-200
            "textAlign": text_align
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/texts",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/cards", tags=["Cards"], status_code=status.HTTP_201_CREATED)
async def create_card_element(request: CreateCardRequest):
    """
    Создание карточки на доске Miro

    Важные ограничения Miro API:
    - width: минимум 256 пикселей
    - height: минимум 50 пикселей
    - title: до 500 символов
    - description: до 5000 символов
    """
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Проверяем и корректируем цвет
    fill_color = request.fill_color.strip()
    if not fill_color.startswith('#'):
        fill_color = f"#{fill_color}"
    if len(fill_color) != 7:  # #RRGGBB
        fill_color = "#ffffff"  # fallback

    # Проверяем размеры (Miro требует width >= 256)
    width = max(request.width, 256)
    height = max(request.height, 50)

    payload = {
        "data": {
            "title": request.title[:500],  # Ограничение Miro
            "description": request.description[:5000]  # Ограничение Miro
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "style": {
            "cardTheme": fill_color
            # textAlign не поддерживается для карточек в Miro API!
        },
        "geometry": {
            "width": width,
            "height": height
        }
    }

    # Добавляем родителя если указан
    if request.frame_id and request.frame_id.strip():
        payload["parent"] = {"id": request.frame_id.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/frames", tags=["Frames"], status_code=status.HTTP_201_CREATED)
async def create_frame_element(request: CreateFrameRequest):
    """
    Создание фрейма на доске Miro

    Ограничения:
    - width/height: от 100 до 32767
    - title: до 500 символов
    """
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Проверяем и корректируем цвет
    fill_color = request.fill_color.strip()
    if not fill_color.startswith('#'):
        fill_color = f"#{fill_color}"
    if len(fill_color) != 7:
        fill_color = "#E6F2FF"

    payload = {
        "data": {
            "title": request.day_name[:500]
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "style": {
            "fillColor": fill_color
        },
        "geometry": {
            "width": max(min(request.width, 32767), 100),
            "height": max(min(request.height, 32767), 100)
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/frames",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/lectures", tags=["Lectures"], status_code=status.HTTP_201_CREATED)
async def create_lecture(request: CreateLectureRequest):
    """
    Создание карточки с учебной парой

    Автоматически применяет цветовую схему по типу занятия
    """
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Цветовая схема по типам занятий
    subject_colors = {
        SubjectType.LECTURE: "#E3F2FD",  # светло-синий
        SubjectType.PRACTICE: "#E8F5E9",  # светло-зеленый
        SubjectType.LABORATORY: "#FFF3E0",  # светло-оранжевый
        SubjectType.SEMINAR: "#F3E5F5",  # светло-фиолетовый
        SubjectType.EXAM: "#FFEBEE"  # светло-красный
    }

    # Форматируем описание
    full_description = (
                           f"⏰ Время: {request.time}\n"
                           f"🏫 Аудитория: {request.classroom}\n"
                           f"👨‍🏫 Преподаватель: {request.teacher}\n"
                           f"📚 Тип: {request.subject_type.value}\n\n"
                           f"{request.description}"
                       )[:5000]  # Ограничение Miro

    fill_color = subject_colors.get(request.subject_type, "#ffffff")

    payload = {
        "data": {
            "title": request.title[:500],
            "description": full_description
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "style": {
            "cardTheme": fill_color
        },
        "geometry": {
            "width": 300,  # Оптимальный размер для карточки пары
            "height": 200
        }
    }

    # Добавляем родителя если указан
    if request.frame_id and request.frame_id.strip():
        payload["parent"] = {"id": request.frame_id.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


# ========== ДЕМО ЭНДПОИНТЫ ==========

@app.post("/demo/create-simple-card", tags=["Demo"])
async def demo_create_simple_card():
    """Демо: создание простой карточки с правильными параметрами"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "title": "Простая карточка",
            "description": "Создана в демо-режиме через API"
        },
        "position": {
            "origin": "center",
            "x": 500,
            "y": 500
        },
        "style": {
            "cardTheme": "#E3F2FD"
            # textAlign удален - не поддерживается для карточек
        },
        "geometry": {
            "width": 300,  # МИНИМУМ 256!
            "height": 200
        }
    }

    print(f"\n🔍 Отправляем запрос в Miro API...")
    print(f"Board ID: {MIRO_BOARD_ID}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/demo/create-simple-text", tags=["Demo"])
async def demo_create_simple_text():
    """Демо: создание простого текста"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "content": "Привет от Miro API! 🎯"
        },
        "position": {
            "origin": "center",
            "x": -500,
            "y": 500
        },
        "style": {
            "color": "#1a1a1a",
            "fontSize": 24,
            "textAlign": "center"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/texts",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


# ========== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ==========

@app.get("/board/items", tags=["Board"])
async def get_board_items(limit: int = 50):
    """Получение всех элементов с доски"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items?limit={limit}",
            headers=headers
        )

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.delete("/board/items/{item_id}", tags=["Board"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    """Удаление элемента с доски"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items/{item_id}",
            headers=headers
        )

    if response.status_code == 204:
        return {"message": "Item deleted successfully"}
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.get("/test/connection", tags=["Test"])
async def test_connection():
    """Проверка подключения к Miro API"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}",
            headers=headers
        )

    if response.status_code == 200:
        board_info = response.json()
        return {
            "status": "connected",
            "board": {
                "name": board_info.get("name"),
                "id": board_info.get("id"),
                "viewLink": board_info.get("viewLink"),
                "createdAt": board_info.get("createdAt")
            }
        }
    else:
        return {
            "status": "error",
            "code": response.status_code,
            "detail": response.text
        }


# ========== ТЕСТОВЫЙ ЭНДПОИНТ ДЛЯ ОТЛАДКИ ==========

@app.post("/test/create-card-minimal", tags=["Test"])
async def test_create_card_minimal():
    """Тест: создание минимальной карточки"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Минимальный payload без style вообще
    payload = {
        "data": {
            "title": "Минимальная карточка"
        },
        "position": {
            "origin": "center",
            "x": 700,
            "y": 700
        },
        "geometry": {
            "width": 256,  # Абсолютный минимум
            "height": 100
        }
    }

    print(f"\n🔍 Тест: создание минимальной карточки")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/test/create-card-with-color", tags=["Test"])
async def test_create_card_with_color():
    """Тест: создание карточки с цветом"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "title": "Карточка с цветом",
            "description": "Тестовая карточка"
        },
        "position": {
            "origin": "center",
            "x": 900,
            "y": 700
        },
        "style": {
            "cardTheme": "#E3F2FD"
        },
        "geometry": {
            "width": 300,
            "height": 200
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


# ========== ШАБЛОНЫ РАСПИСАНИЯ ==========

@app.post("/schedule/week", tags=["Schedule"], status_code=status.HTTP_201_CREATED)
async def create_week_schedule():
    """
    Создание полной структуры расписания на неделю
    """
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    results = []

    for i, day in enumerate(days):
        # Создаем фрейм для дня
        frame_response = await create_frame_element(CreateFrameRequest(
            day_name=day,
            position=Position(x=i * 450, y=0),
            width=400,
            height=1200,
            fill_color="#F8F9FA"
        ))

        # Создаем заголовок дня
        await create_text_element(CreateTextRequest(
            content=f"📅 {day.upper()}",
            position=Position(x=i * 450, y=-550),
            font_size=28,
            color="#1976D2",
            text_align="center"
        ))

        # Добавляем временные метки
        times = ["9:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00"]
        for j, time in enumerate(times):
            await create_text_element(CreateTextRequest(
                content=f"🕐 {time}",
                position=Position(x=i * 450 - 150, y=-400 + (j * 170)),
                font_size=14,
                color="#666666",
                text_align="left"
            ))

        results.append({
            "day": day,
            "frame_id": frame_response["id"],
            "position": i * 450
        })

    return {
        "message": "Week schedule structure created successfully",
        "frames": results
    }


# ========== КОРНЕВОЙ ЭНДПОИНТ ==========

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "University Schedule Miro API v1.0.4",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.4",
        "test_endpoints": [
            "/test/connection",
            "/test/create-card-minimal",
            "/test/create-card-with-color",
            "/demo/create-simple-card",
            "/demo/create-simple-text"
        ],
        "limitations": {
            "card_min_width": 256,
            "card_min_height": 50,
            "max_title_length": 500,
            "max_description_length": 5000
        }
    }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="University Schedule Miro API v1.0.4",
        version="1.0.4",
        description="""
        ## 🎯 Рабочий API для Miro с исправленными ограничениями

        ### ✅ ИСПРАВЛЕНО: Убран textAlign для карточек

        ### 📏 Важные ограничения Miro API:

        | Элемент | Поддерживаемые параметры style |
        |---------|--------------------------------|
        | Карточка | только `cardTheme` |
        | Текст | `color`, `fontSize`, `textAlign` |
        | Фрейм | `fillColor` |

        ### 🚀 Тестовые эндпоинты:

        1. **Минимальная карточка:**
        ```bash
        curl -X POST http://localhost:8000/test/create-card-minimal
        ```

        2. **Карточка с цветом:**
        ```bash
        curl -X POST http://localhost:8000/test/create-card-with-color
        ```

        3. **Демо карточка:**
        ```bash
        curl -X POST http://localhost:8000/demo/create-simple-card
        ```

        ### 📝 Пример создания карточки:
        ```bash
        curl -X POST http://localhost:8000/cards \\
          -H "Content-Type: application/json" \\
          -d '{
            "title": "Математика",
            "description": "Лекция по алгебре",
            "position": {"x": 100, "y": 100},
            "width": 300,
            "height": 200,
            "fill_color": "#E3F2FD"
          }'
        ```

        ### ⚠️ Важно:
        - Для карточек НЕ используйте `textAlign` в style
        - Минимальная ширина карточки: 256px
        - Для текста можно использовать `textAlign`
        """,
        routes=app.routes,
    )

    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Локальный сервер"}
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
