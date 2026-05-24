"""
Локальное хранилище в JSON-файле.

Зачем оно нужно: Miro API оперирует своими ID объектов (карточек, фреймов, текстов).
Чтобы потом редактировать/удалять пару, нам нужно помнить, какая
пара (день + слот) соответствует какому miro_item_id.

Структура файла storage.json:
{
  "board_id": "uXjVxxxxxxx=",
  "frame_id": "3458764512345678",
  "header_ids": {"Понедельник": "...", ...},      # ID текстов-заголовков дней
  "time_label_ids": {"09:00-10:30": "...", ...},   # ID текстов с временем
  "lessons": {
      "<lesson_id>": {
          "id": "<lesson_id>",
          "day": "Понедельник",
          "slot": "09:00-10:30",
          "subject": "Матанализ",
          "lesson_type": "лекция",
          "format": "очно",
          "teacher": "Иванов И.И.",
          "miro_item_id": "3458764512..."
      }
  }
}
"""
import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from .config import STORAGE_FILE


# Один глобальный лок — записи в JSON-файл не пересекаются между запросами.
_lock = threading.Lock()


def _empty_state() -> dict:
    return {
        "board_id": None,
        "frame_id": None,
        "header_ids": {},
        "time_label_ids": {},
        "lessons": {},
    }


def load() -> dict:
    """Прочитать состояние из файла. Если файла нет — вернуть пустое."""
    path = Path(STORAGE_FILE)
    if not path.exists():
        return _empty_state()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # На случай, если файл был создан более старой версией — дозальём недостающие ключи
        for k, v in _empty_state().items():
            data.setdefault(k, v)
        return data
    except (json.JSONDecodeError, OSError):
        # Файл повреждён — начинаем заново, чтобы не валить весь сервис
        return _empty_state()


def save(state: dict) -> None:
    """Записать состояние в файл атомарно (через временный файл)."""
    path = Path(STORAGE_FILE)
    tmp = path.with_suffix(".json.tmp")
    with _lock:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp.replace(path)


# --- Удобные обёртки для частых операций ---

def new_lesson_id() -> str:
    """Сгенерировать короткий человекочитаемый ID для пары."""
    return uuid.uuid4().hex[:12]


def get_lesson(lesson_id: str) -> Optional[dict]:
    return load().get("lessons", {}).get(lesson_id)


def add_lesson(lesson: dict) -> None:
    state = load()
    state["lessons"][lesson["id"]] = lesson
    save(state)


def update_lesson(lesson_id: str, patch: dict) -> Optional[dict]:
    state = load()
    if lesson_id not in state["lessons"]:
        return None
    state["lessons"][lesson_id].update(patch)
    save(state)
    return state["lessons"][lesson_id]


def remove_lesson(lesson_id: str) -> Optional[dict]:
    state = load()
    lesson = state["lessons"].pop(lesson_id, None)
    if lesson is not None:
        save(state)
    return lesson


def find_lesson_by_slot(day: str, slot: str) -> Optional[dict]:
    """Найти пару по (день, слот). Возвращает первую найденную либо None."""
    for lesson in load()["lessons"].values():
        if lesson["day"] == day and lesson["slot"] == slot:
            return lesson
    return None


def reset() -> None:
    """Полностью очистить локальное хранилище (использовать с осторожностью)."""
    save(_empty_state())
