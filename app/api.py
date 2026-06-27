"""
FastAPI REST API для расписания.

Swagger UI (как у FastAPI by default):
  http://localhost:5000/docs      — Swagger UI
  http://localhost:5000/redoc     — ReDoc (альтернативный вид)
  http://localhost:5000/openapi.json — сырая OpenAPI 3.1 спека

Документация генерируется автоматически из:
  - Pydantic-моделей (схемы запроса/ответа)
  - аннотаций типов и Enum (валидация + dropdown'ы в Swagger UI)
  - параметра `responses=` у эндпоинтов (коды ошибок)
"""
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import schedule, storage
from .config import DAYS, TIME_SLOTS, COLORS_BY_TYPE, FORMAT_ICONS, WEEKS, WEEK_LABELS, WEEK_BOTH
from .miro_client import MiroError


# ============================================================
# Enum'ы — превращаются в dropdown'ы в Swagger UI
# ============================================================

# Динамически собираем Enum'ы из config.py, чтобы не дублировать значения.
# StrEnum (Python 3.11+) удобен, но для совместимости делаем через (str, Enum).
DayEnum = Enum("DayEnum", {d: d for d in DAYS}, type=str)
SlotEnum = Enum("SlotEnum", {s.replace(":", "_").replace("-", "_"): s for s in TIME_SLOTS}, type=str)
LessonTypeEnum = Enum(
    "LessonTypeEnum",
    {t: t for t in COLORS_BY_TYPE if t != "default"},
    type=str,
)
FormatEnum = Enum("FormatEnum", {f: f for f in FORMAT_ICONS}, type=str)
WeekEnum = Enum(
    "WeekEnum",
    {w.replace("ё", "е"): w for w in WEEKS},  # ключи enum без «ё» — значения остаются с «ё»
    type=str,
)


# ============================================================
# Pydantic-модели запроса/ответа
# ============================================================

class LessonCreate(BaseModel):
    """Данные для создания новой пары."""
    day: DayEnum = Field(..., description="День недели")
    slot: SlotEnum = Field(..., description="Временной слот пары")
    subject: str = Field(..., min_length=1, max_length=200,
                         examples=["Математический анализ"])
    lesson_type: LessonTypeEnum = Field(..., description="Тип занятия — определяет цвет карточки")
    format: FormatEnum = Field(..., description="Формат проведения")
    teacher: str = Field(..., min_length=1, max_length=200, examples=["Иванов И.И."])
    room: str = Field(
        ..., min_length=1, max_length=50, examples=["414", "А-201", "Zoom"],
        description="Номер аудитории. Обязательно. Для дистанта укажи 'Zoom' / 'BigBlueButton' и т.п.",
    )
    week: WeekEnum = Field(
        WeekEnum(WEEK_BOTH),
        description="Чётность недели: 'обе' (на всю ячейку), 'нечётная' (числитель, верх), 'чётная' (знаменатель, низ)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "day": "Понедельник",
                "slot": "09:00-10:30",
                "subject": "Математический анализ",
                "lesson_type": "лекция",
                "format": "очно",
                "teacher": "Иванов И.И.",
                "room": "414",
                "week": "нечётная",
            }
        }
    }


class LessonPatch(BaseModel):
    """Изменение пары. Все поля опциональны. day/slot менять через /move."""
    subject: Optional[str] = Field(None, min_length=1, max_length=200)
    lesson_type: Optional[LessonTypeEnum] = None
    format: Optional[FormatEnum] = None
    teacher: Optional[str] = Field(None, min_length=1, max_length=200)
    room: Optional[str] = Field(None, min_length=1, max_length=50)


class MoveRequest(BaseModel):
    """Перенос пары в другую ячейку сетки и/или смена чётности недели."""
    day: DayEnum
    slot: SlotEnum
    week: Optional[WeekEnum] = Field(
        None, description="Новая чётность недели. Если не указана — сохраняется текущая.")


class Lesson(BaseModel):
    """Пара как она хранится: данные + ID нашей записи и ID карточки в Miro."""
    id: str
    day: str
    slot: str
    week: str = WEEK_BOTH
    subject: str
    lesson_type: str
    format: str
    teacher: str
    room: str
    miro_item_id: str
    miro_item_ids: Optional[list[str]] = None
    miro_group_id: Optional[str] = None


class BoardInitRequest(BaseModel):
    title: str = Field("Расписание на неделю", examples=["Расписание ИУ7, 3 курс"])


class BoardInitResponse(BaseModel):
    frame_id: str
    header_ids: dict[str, str]
    time_label_ids: dict[str, str]
    message: str


class BoardClearResponse(BaseModel):
    deleted_cards: int
    frame_deleted: bool


class MetaResponse(BaseModel):
    days: list[str]
    slots: list[str]
    lesson_types: list[str]
    formats: list[str]
    weeks: list[str]
    week_labels: dict[str, str]
    colors_by_type: dict[str, dict[str, str]]


class ScheduleCell(BaseModel):
    """Содержимое одной ячейки (день × слот) в разрезе чётности недели."""
    обе: Optional[Lesson] = None
    нечётная: Optional[Lesson] = None
    чётная: Optional[Lesson] = None


class ScheduleRow(BaseModel):
    slot: str
    cells: dict[str, ScheduleCell]


class ScheduleResponse(BaseModel):
    days: list[str]
    slots: list[str]
    weeks: list[str]
    rows: list[ScheduleRow]


class SyncResponse(BaseModel):
    preview: bool
    moved: list[dict]
    conflicts: list[dict]
    missing_on_board: list[dict]
    lessons: Optional[list[Lesson]] = None
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"


class DeleteResponse(BaseModel):
    deleted: Lesson


class ErrorResponse(BaseModel):
    error: str


# ============================================================
# Приложение
# ============================================================

app = FastAPI(
    title="Miro University Schedule API",
    description=(
        "REST API для управления расписанием университета на доске Miro.\n\n"
        "**Как пользоваться:**\n"
        "1. Вызови `POST /api/board/init` — на доске появится сетка.\n"
        "2. Добавляй пары через `POST /api/lessons`.\n"
        "3. Редактируй через `PATCH /api/lessons/{id}`, "
        "переноси через `POST /api/lessons/{id}/move`."
    ),
    version="1.0.0",
    # Хочешь поменять URL Swagger UI? docs_url="/swagger"
)


# ---- Обработчики ошибок ----
# ValueError из бизнес-логики -> 400, LookupError -> 404, MiroError -> прокидываем код Miro.
# Любое неожиданное исключение -> 500 с traceback в теле,
# чтобы причина была видна в Swagger, а не только в логах uvicorn.

import traceback


@app.exception_handler(ValueError)
async def _value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(LookupError)
async def _lookup_error_handler(_, exc: LookupError):
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(MiroError)
async def _miro_error_handler(_, exc: MiroError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": str(exc), "miro_payload": exc.payload},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_, exc: Exception):
    # Печатаем в консоль uvicorn полный traceback
    tb = traceback.format_exc()
    print(tb)
    # И возвращаем краткое сообщение клиенту (без чувствительных деталей).
    # В режиме разработки кладём type/msg, чтобы видеть прямо в Swagger.
    return JSONResponse(
        status_code=500,
        content={
            "error": f"{type(exc).__name__}: {exc}",
            "hint": "Полный traceback — в логах uvicorn",
        },
    )


# ============================================================
# Health / Meta
# ============================================================

@app.get("/api/health", response_model=HealthResponse, tags=["Health"],
         summary="Проверка живости")
async def health():
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaResponse, tags=["Health"],
         summary="Справочник: дни, слоты, типы, форматы, цвета")
async def meta():
    return {
        "days": DAYS,
        "slots": TIME_SLOTS,
        "lesson_types": [t for t in COLORS_BY_TYPE if t != "default"],
        "formats": list(FORMAT_ICONS.keys()),
        "weeks": WEEKS,
        "week_labels": WEEK_LABELS,
        "colors_by_type": COLORS_BY_TYPE,
    }


# ============================================================
# Board
# ============================================================

@app.post(
    "/api/board/init",
    response_model=BoardInitResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Board"],
    summary="Создать сетку расписания на доске Miro",
    responses={500: {"model": ErrorResponse, "description": "Ошибка Miro API"}},
)
async def board_init(body: Optional[BoardInitRequest] = None):
    title = body.title if body else "Расписание на неделю"
    return schedule.init_board(title=title)


@app.delete(
    "/api/board",
    response_model=BoardClearResponse,
    tags=["Board"],
    summary="Снести расписание",
)
async def board_clear(
    keep_frame: bool = Query(False, description="Оставить шапку с днями, удалить только пары"),
):
    return schedule.clear_all(delete_frame_too=not keep_frame)


@app.get(
    "/api/schedule",
    response_model=ScheduleResponse,
    tags=["Board"],
    summary="Расписание сеткой (дни × слоты × чётность) из локального хранилища",
)
async def schedule_grid():
    """
    Готовая к отображению сетка: строки — слоты, столбцы — дни, в каждой
    ячейке три ячейки чётности (обе / нечётная / чётная).
    Берётся из storage и НЕ ходит в Miro.
    """
    return schedule.get_schedule_grid()


@app.post(
    "/api/board/sync",
    response_model=SyncResponse,
    tags=["Board"],
    summary="Считать актуальное состояние расписания с доски Miro",
    responses={404: {"model": ErrorResponse, "description": "Доска не инициализирована"}},
)
async def board_sync(
    preview: bool = Query(
        False,
        description="Только показать, что считалось, не записывая изменения в storage"),
    detect_week: bool = Query(
        False,
        description="Пытаться определить чётность недели по верх/низ половине ячейки"),
):
    """
    Считывает фактические позиции карточек на доске и сопоставляет каждую
    ближайшей ячейке (день × слот), затем обновляет локальное хранилище.
    Используется, когда расписание правили вручную прямо в Miro.

    - `preview=true` — сухой прогон: вернёт, что увидели, ничего не меняя.
    - `detect_week=true` — заодно пробует определить числитель/знаменатель.

    Карточки на доске не двигаются (остаются на своих местах);
    пересобираются только плейсхолдеры пустых ячеек.
    """
    return schedule.sync_from_board(preview=preview, detect_week=detect_week)


# ============================================================
# Lessons
# ============================================================

@app.get(
    "/api/lessons",
    response_model=list[Lesson],
    tags=["Lessons"],
    summary="Список всех пар (с фильтром по дню)",
)
async def lessons_list(
    day: Optional[DayEnum] = Query(None, description="Фильтр по дню"),
    week: Optional[WeekEnum] = Query(None, description="Фильтр по чётности недели"),
):
    return schedule.list_lessons(
        day=day.value if day else None,
        week=week.value if week else None,
    )


@app.post(
    "/api/lessons",
    response_model=Lesson,
    status_code=status.HTTP_201_CREATED,
    tags=["Lessons"],
    summary="Создать пару",
    responses={
        400: {"model": ErrorResponse, "description": "Ячейка занята / не пройдена валидация"},
    },
)
async def lessons_create(body: LessonCreate):
    return schedule.create_lesson(body.model_dump(mode="json"))


@app.get(
    "/api/lessons/{lesson_id}",
    response_model=Lesson,
    tags=["Lessons"],
    summary="Получить пару по ID",
    responses={404: {"model": ErrorResponse, "description": "Пара не найдена"}},
)
async def lessons_get(lesson_id: str = Path(..., description="ID пары")):
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Пара {lesson_id} не найдена")
    return lesson


@app.patch(
    "/api/lessons/{lesson_id}",
    response_model=Lesson,
    tags=["Lessons"],
    summary="Изменить пару (кроме day/slot)",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def lessons_patch(lesson_id: str, body: LessonPatch):
    # exclude_unset=True — отправляем в логику только реально переданные поля,
    # это превращает PATCH в честный частичный апдейт.
    patch = body.model_dump(mode="json", exclude_unset=True)
    return schedule.update_lesson(lesson_id, patch)


@app.post(
    "/api/lessons/{lesson_id}/move",
    response_model=Lesson,
    tags=["Lessons"],
    summary="Перенести пару в другую ячейку",
    responses={
        400: {"model": ErrorResponse, "description": "Целевая ячейка занята"},
        404: {"model": ErrorResponse, "description": "Пара не найдена"},
    },
)
async def lessons_move(lesson_id: str, body: MoveRequest):
    return schedule.move_lesson(
        lesson_id, body.day.value, body.slot.value,
        new_week=body.week.value if body.week else None,
    )


@app.delete(
    "/api/lessons/{lesson_id}",
    response_model=DeleteResponse,
    tags=["Lessons"],
    summary="Удалить пару",
    responses={404: {"model": ErrorResponse, "description": "Пара не найдена"}},
)
async def lessons_delete(lesson_id: str):
    return {"deleted": schedule.delete_lesson(lesson_id)}