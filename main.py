# main.py (исправленная версия для parent.id)
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
import re

load_dotenv()

app = FastAPI(
    title="University Schedule Miro API",
    description="API для управления онлайн-расписанием университета на платформе Miro",
    version="1.0.6",
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
    font_size: int = Field(default=14, ge=1, le=200, description="Размер шрифта (целое число 1-200)")
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
    frame_id: Optional[str] = Field(None, description="ID родительского фрейма (числовой ID)")


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
    frame_id: Optional[str] = Field(None, description="ID фрейма дня (числовой ID)")


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def extract_numeric_id(item_id: str) -> Optional[str]:
    """
    Извлекает числовой ID из строкового ID Miro
    Miro ID могут быть в формате: '34567890123456789012' или 'uXjV1234567890='
    """
    if not item_id:
        return None

    # Убираем возможные префиксы и суффиксы
    item_id = str(item_id).strip()

    # Если это уже число, возвращаем как есть
    if item_id.isdigit():
        return item_id

    # Пытаемся извлечь числовую часть
    match = re.search(r'\d+', item_id)
    if match:
        return match.group(0)

    return None


# ========== ЭНДПОИНТЫ API ==========

@app.post("/texts", tags=["Text"], status_code=status.HTTP_201_CREATED)
async def create_text_element(request: CreateTextRequest):
    """
    Создание текстового элемента на доске Miro

    Ограничения Miro API:
    - font_size: целое число от 1 до 200
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
        color = "#1a1a1a"

    # Проверяем и корректируем выравнивание
    text_align = request.text_align.lower()
    if text_align not in ["left", "center", "right"]:
        text_align = "center"

    payload = {
        "data": {
            "content": request.content[:5000]
        },
        "position": {
            "origin": "center",
            "x": request.position.x,
            "y": request.position.y
        },
        "style": {
            "color": color,
            "fontSize": max(1, min(request.font_size, 200)),
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
    - frame_id: должен быть числовым ID
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
        fill_color = "#ffffff"

    # Проверяем размеры
    width = max(request.width, 256)
    height = max(request.height, 50)

    payload = {
        "data": {
            "title": request.title[:500],
            "description": request.description[:5000]
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
            "width": width,
            "height": height
        }
    }

    # Обрабатываем frame_id - преобразуем в числовой ID если нужно
    if request.frame_id and request.frame_id.strip():
        frame_id = request.frame_id.strip()

        # Если это не стандартное значение Swagger "string"
        if frame_id != "string" and len(frame_id) > 1:
            numeric_id = extract_numeric_id(frame_id)
            if numeric_id and numeric_id.isdigit():
                payload["parent"] = {"id": numeric_id}
            else:
                # Если не можем извлечь числовой ID, используем как есть
                # Miro API может принимать разные форматы
                payload["parent"] = {"id": frame_id}

    print(f"\n🔍 Создаем карточку в Miro API...")
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

    subject_colors = {
        SubjectType.LECTURE: "#E3F2FD",
        SubjectType.PRACTICE: "#E8F5E9",
        SubjectType.LABORATORY: "#FFF3E0",
        SubjectType.SEMINAR: "#F3E5F5",
        SubjectType.EXAM: "#FFEBEE"
    }

    full_description = (
                           f"⏰ Время: {request.time}\n"
                           f"🏫 Аудитория: {request.classroom}\n"
                           f"👨‍🏫 Преподаватель: {request.teacher}\n"
                           f"📚 Тип: {request.subject_type.value}\n\n"
                           f"{request.description}"
                       )[:5000]

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
            "width": 300,  # Исправлено с 250 на 300 (или 256+)
            "height": 200
        }
    }

    # Обрабатываем frame_id
    if request.frame_id and request.frame_id.strip():
        frame_id = request.frame_id.strip()
        if frame_id != "string" and len(frame_id) > 1:
            numeric_id = extract_numeric_id(frame_id)
            if numeric_id and numeric_id.isdigit():
                payload["parent"] = {"id": numeric_id}
            else:
                payload["parent"] = {"id": frame_id}

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


# ========== ПОЛЕЗНЫЕ ЭНДПОИНТЫ ==========

@app.get("/board/items/{item_id}", tags=["Board"])
async def get_item_by_id(item_id: str):
    """Получение информации о конкретном элементе по ID"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    print(f"\n🔍 Получаем информацию об элементе: {item_id}")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items/{item_id}",
            headers=headers
        )

    if response.status_code == 200:
        item_data = response.json()

        # Добавляем полезную информацию
        item_info = {
            "id": item_data.get("id"),
            "type": item_data.get("type"),
            "title": item_data.get("data", {}).get("title"),
            "description": item_data.get("data", {}).get("description"),
            "created_at": item_data.get("createdAt"),
            "position": item_data.get("position"),
            "parent_id": item_data.get("parent", {}).get("id") if item_data.get("parent") else None
        }

        return {
            "item_info": item_info,
            "full_data": item_data
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.delete("/board/items/{item_id}", tags=["Board"], status_code=status.HTTP_200_OK)
async def delete_item(item_id: str):
    """Удаление элемента с доски по ID

    Возвращает:
    - 200: Успешное удаление
    - 404: Элемент не найден
    - 400: Ошибка удаления
    """
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    print(f"\n🗑️  Удаляем элемент: {item_id}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items/{item_id}",
            headers=headers
        )

    print(f"Status: {response.status_code}")

    if response.status_code == 204:
        return {
            "success": True,
            "message": f"Элемент {item_id} успешно удален",
            "item_id": item_id
        }
    elif response.status_code == 404:
        return {
            "success": False,
            "message": f"Элемент {item_id} не найден",
            "item_id": item_id
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.delete("/board/cleanup/test-items", tags=["Board"])
async def cleanup_test_items():
    """Удаление всех тестовых элементов с доски"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    print(f"\n🧹 Очистка тестовых элементов...")

    # Получаем все элементы
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items?limit=50",
            headers=headers
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )

    items = response.json().get("data", [])
    deleted_items = []
    failed_items = []

    # Фильтруем тестовые элементы
    test_keywords = ["тест", "Test", "TEST", "демо", "Демо", "DEMO", "карточка", "Карточка"]

    for item in items:
        item_id = item.get("id")
        item_title = item.get("data", {}).get("title", "").lower()
        item_desc = item.get("data", {}).get("description", "").lower()

        # Проверяем, является ли элемент тестовым
        is_test = any(keyword.lower() in item_title for keyword in test_keywords) or \
                  any(keyword.lower() in item_desc for keyword in test_keywords)

        if is_test:
            try:
                # Удаляем элемент
                delete_response = await client.delete(
                    f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items/{item_id}",
                    headers=headers
                )

                if delete_response.status_code == 204:
                    deleted_items.append({
                        "id": item_id,
                        "title": item.get("data", {}).get("title"),
                        "type": item.get("type")
                    })
                else:
                    failed_items.append({
                        "id": item_id,
                        "error": delete_response.text
                    })
            except Exception as e:
                failed_items.append({
                    "id": item_id,
                    "error": str(e)
                })

    return {
        "message": "Очистка тестовых элементов завершена",
        "deleted_count": len(deleted_items),
        "failed_count": len(failed_items),
        "deleted_items": deleted_items,
        "failed_items": failed_items
    }

@app.get("/board/items", tags=["Board"])
async def get_board_items(limit: int = 50):
    """Получение всех элементов с доски"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    # Ограничиваем limit значением 50 (максимум для Miro API)
    limit = min(limit, 50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items?limit={limit}",
            headers=headers
        )

    if response.status_code == 200:
        items = response.json()

        # Извлекаем фреймы для удобства
        frames = []
        for item in items.get("data", []):
            if item.get("type") == "frame":
                frames.append({
                    "id": item.get("id"),
                    "title": item.get("data", {}).get("title"),
                    "position": item.get("position")
                })

        return {
            "total_items": len(items.get("data", [])),
            "frames": frames,
            "items": items
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.get("/board/frames", tags=["Board"])
async def get_board_frames():
    """Получение только фреймов с доски"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/items?limit=50",
            headers=headers
        )

    if response.status_code == 200:
        items = response.json()
        frames = []

        for item in items.get("data", []):
            if item.get("type") == "frame":
                item_id = item.get("id")
                numeric_id = extract_numeric_id(item_id)

                frames.append({
                    "id": item_id,
                    "numeric_id": numeric_id,
                    "title": item.get("data", {}).get("title", "Без названия"),
                    "position": item.get("position"),
                    "geometry": item.get("geometry"),
                    "created_at": item.get("createdAt")
                })

        return {
            "frames_count": len(frames),
            "frames": frames
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


# ========== ТЕСТОВЫЕ ЭНДПОИНТЫ ==========

@app.post("/test/create-card-no-frame", tags=["Test"])
async def test_create_card_no_frame():
    """Тест: создание карточки БЕЗ фрейма"""
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "title": "Карточка без фрейма",
            "description": "Тестовая карточка созданная без родительского фрейма"
        },
        "position": {
            "origin": "center",
            "x": -500,
            "y": 500
        },
        "style": {
            "cardTheme": "#E3F2FD"
        },
        "geometry": {
            "width": 300,
            "height": 200
        }
    }

    print(f"\n🔍 Тест: карточка без фрейма")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✅ Успех!")
        return response.json()
    else:
        print(f"❌ Ошибка: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/test/create-card-with-real-frame", tags=["Test"])
async def test_create_card_with_real_frame():
    """Тест: создание карточки с реальным фреймом"""

    # Сначала получим существующие фреймы
    frames_response = await get_board_frames()

    if frames_response["frames_count"] == 0:
        # Создаем тестовый фрейм
        frame_response = await create_frame_element(CreateFrameRequest(
            day_name="Тестовый день",
            position=Position(x=0, y=0),
            width=800,
            height=1200,
            fill_color="#F8F9FA"
        ))

        frame_id = frame_response["id"]
        frame_title = "Тестовый день"
    else:
        # Используем первый существующий фрейм
        frame = frames_response["frames"][0]
        frame_id = frame["id"]
        frame_title = frame["title"]

    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Используем минимальную ширину 256 и центр фрейма
    payload = {
        "data": {
            "title": f"Карточка в {frame_title}",
            "description": f"Тестовая карточка внутри фрейма '{frame_title}'"
        },
        "position": {
            "origin": "center",
            "x": 0,
            "y": 0
        },
        "style": {
            "cardTheme": "#E8F5E9"
        },
        "geometry": {
            "width": 256,  # Минимальная ширина!
            "height": 180
        },
        "parent": {
            "id": extract_numeric_id(frame_id) or frame_id
        }
    }

    print(f"\n🔍 Тест: карточка с фреймом")
    print(f"Frame: {frame_title} (ID: {frame_id})")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✅ Успех!")
        return {
            "message": "Карточка успешно создана внутри фрейма",
            "frame": {
                "id": frame_id,
                "title": frame_title
            },
            "card": response.json()
        }
    else:
        print(f"❌ Ошибка: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


@app.post("/test/create-card-inside-frame-safe", tags=["Test"])
async def test_create_card_inside_frame_safe():
    """Безопасный тест: создание карточки внутри фрейма"""

    # Сначала создадим фрейм специально для теста
    frame_response = await create_frame_element(CreateFrameRequest(
        day_name="Тестовый фрейм для API",
        position=Position(x=1000, y=0),  # Правая часть доски
        width=600,
        height=800,
        fill_color="#F0F8FF"
    ))

    frame_id = frame_response["id"]

    # Теперь создаем маленькую карточку прямо в центре этого фрейма
    headers = {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "title": "Тестовая карточка",
            "description": "Создана внутри фрейма через API"
        },
        "position": {
            "origin": "center",
            "x": 0,
            "y": 0
        },
        "style": {
            "cardTheme": "#E3F2FD"
        },
        "geometry": {
            "width": 256,  # Минимальная ширина
            "height": 150
        },
        "parent": {
            "id": extract_numeric_id(frame_id) or frame_id
        }
    }

    print(f"\n🔍 Безопасный тест: карточка внутри фрейма")
    print(f"Frame ID: {frame_id}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MIRO_API_BASE_URL}/boards/{MIRO_BOARD_ID}/cards",
            headers=headers,
            json=payload
        )

    if response.status_code == 201:
        return {
            "success": True,
            "message": "Карточка успешно создана внутри фрейма",
            "frame_id": frame_id,
            "card": response.json()
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Miro API error: {response.text}"
        )


# ========== КОРНЕВОЙ ЭНДПОИНТ ==========

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "University Schedule Miro API v1.0.6",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.6",
        "important": "frame_id должен быть числовым ID",
        "useful_endpoints": [
            "/board/frames - получить список фреймов",
            "/board/items/{id} - получить информацию об элементе",
            "/board/items/{id} (DELETE) - удалить элемент",
            "/board/cleanup/test-items - удалить все тестовые элементы",
            "/test/create-card-no-frame - создать карточку без фрейма",
            "/test/create-card-with-real-frame - создать карточку с фреймом"
        ]
    }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="University Schedule Miro API v1.0.6",
        version="1.0.6",
        description="""
        🎯 API для Miro

        📋 Важная информация:

        1. **frame_id должен быть числовым ID** (например: "34567890123456789012")
        2. Если не знаете ID фрейма, используйте `/board/frames` чтобы получить список
        3. Можно создавать карточки без фрейма (просто не указывайте frame_id)

        🚀 Полезные эндпоинты:

        ```bash
        # Получить список всех фреймов на доске
        curl http://localhost:8000/board/frames

        # Создать карточку БЕЗ фрейма (для теста)
        curl -X POST http://localhost:8000/test/create-card-no-frame

        # Создать карточку с реальным фреймом
        curl -X POST http://localhost:8000/test/create-card-with-real-frame
        ```

        📝 Примеры запросов:

        Карточка БЕЗ фрейма:
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

        Карточка С фреймом:
        ```bash
        curl -X POST http://localhost:8000/cards \\
          -H "Content-Type: application/json" \\
          -d '{
            "title": "Математика",
            "description": "Лекция по алгебре",
            "position": {"x": 0, "y": 0},
            "width": 300,
            "height": 200,
            "fill_color": "#E3F2FD",
            "frame_id": "34567890123456789012"
          }'
        ```
        
        🗑️ Управление элементами:

        Получить информацию об элементе:
        ```bash
        curl http://localhost:8000/board/items/3458764657216552895
        ```

        Удалить элемент:
        ```bash
        curl -X DELETE http://localhost:8000/board/items/3458764657216552895
        ```

        Удалить несколько элементов:
        ```bash
        curl -X DELETE http://localhost:8000/board/items/batch?item_ids=id1&item_ids=id2&item_ids=id3
        ```

        ⚠️ Для Swagger тестирования:
        В поле `frame_id` не указывайте "string" - это вызовет ошибку.
        Либо оставьте поле пустым, либо получите реальный frame_id через `/board/frames`.
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
