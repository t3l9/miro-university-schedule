"""
Бизнес-логика расписания + раскладка на доске Miro.

Ключевой инсайт: текст внутри shape в Miro плохо контролируется по размеру —
inline-CSS font-size в HTML работает непредсказуемо и часто игнорируется.
Поэтому ВСЕ читаемые тексты (титул, шапки дней, время, поля карточки пары)
делаются как отдельные text-объекты, где fontSize задаётся в чистых пикселях
и работает предсказуемо (поддерживается до 288 px).

Карточка пары собирается как композиция из нескольких объектов:
  1. фоновая плашка (shape, без текста) — цветной фон + рамка
  2. цветной "корешок" слева (shape, узкий) — насыщенный акцент типа пары
  3. text: бейдж типа пары (крупные капсы)
  4. text: дисциплина (огромный жирный)
  5. text: формат + аудитория
  6. text: преподаватель

При удалении/переносе пары мы храним массив всех её ID и удаляем все.
"""
from typing import Optional

from . import miro_client, storage
from .config import (
    DAYS, TIME_SLOTS, COLORS_BY_TYPE, FORMAT_ICONS,
    DAY_ACCENTS,
    CARD_WIDTH, CARD_HEIGHT, COL_GAP, ROW_GAP,
    TITLE_HEIGHT, HEADER_HEIGHT, TIME_COL_WIDTH, FRAME_PADDING,
    COLOR_INK, COLOR_INK_MUTED, COLOR_PAPER, COLOR_SURFACE,
    COLOR_BORDER, COLOR_HEADER_BG, COLOR_HEADER_TEXT,
)


# =============================================================================
# Геометрия
# =============================================================================

# Ширина цветного корешка слева у карточки пары.
CARD_SPINE_WIDTH = 12

# Внутренние отступы карточки от её краёв (после корешка).
CARD_PAD_LEFT = CARD_SPINE_WIDTH + 22  # от левого края карточки до начала текста
CARD_PAD_RIGHT = 24
CARD_PAD_TOP = 22
CARD_PAD_BOTTOM = 22


def _grid_size() -> tuple[float, float]:
    width = TIME_COL_WIDTH + len(DAYS) * (CARD_WIDTH + COL_GAP) + COL_GAP
    height = TITLE_HEIGHT + HEADER_HEIGHT + len(TIME_SLOTS) * (CARD_HEIGHT + ROW_GAP) + ROW_GAP
    return width, height


def _frame_size() -> tuple[float, float]:
    w, h = _grid_size()
    return w + 2 * FRAME_PADDING, h + 2 * FRAME_PADDING


def _title_center() -> tuple[float, float]:
    fw, _ = _frame_size()
    x = fw / 2
    y = FRAME_PADDING + TITLE_HEIGHT / 2
    return x, y


def _title_width() -> float:
    gw, _ = _grid_size()
    return gw


def _day_header_center(day: str) -> tuple[float, float]:
    col = DAYS.index(day)
    x = FRAME_PADDING + TIME_COL_WIDTH + COL_GAP / 2 + col * (CARD_WIDTH + COL_GAP) + CARD_WIDTH / 2
    y = FRAME_PADDING + TITLE_HEIGHT + HEADER_HEIGHT / 2
    return x, y


def _day_accent_center(day: str) -> tuple[float, float]:
    col = DAYS.index(day)
    x = FRAME_PADDING + TIME_COL_WIDTH + COL_GAP / 2 + col * (CARD_WIDTH + COL_GAP) + CARD_WIDTH / 2
    # Полоска ширины 12 px по нижнему краю шапки
    y = FRAME_PADDING + TITLE_HEIGHT + HEADER_HEIGHT - 6
    return x, y


def _time_label_center(slot: str) -> tuple[float, float]:
    row = TIME_SLOTS.index(slot)
    x = FRAME_PADDING + TIME_COL_WIDTH / 2
    y = (
        FRAME_PADDING + TITLE_HEIGHT + HEADER_HEIGHT
        + ROW_GAP / 2 + row * (CARD_HEIGHT + ROW_GAP) + CARD_HEIGHT / 2
    )
    return x, y


def _cell_center(day: str, slot: str) -> tuple[float, float]:
    if day not in DAYS:
        raise ValueError(f"Неизвестный день: {day}. Доступны: {DAYS}")
    if slot not in TIME_SLOTS:
        raise ValueError(f"Неизвестный временной слот: {slot}. Доступны: {TIME_SLOTS}")
    col = DAYS.index(day)
    row = TIME_SLOTS.index(slot)
    x = FRAME_PADDING + TIME_COL_WIDTH + COL_GAP / 2 + col * (CARD_WIDTH + COL_GAP) + CARD_WIDTH / 2
    y = (
        FRAME_PADDING + TITLE_HEIGHT + HEADER_HEIGHT
        + ROW_GAP / 2 + row * (CARD_HEIGHT + ROW_GAP) + CARD_HEIGHT / 2
    )
    return x, y


def _cell_top_left(day: str, slot: str) -> tuple[float, float]:
    """Верхний-левый угол ячейки (для расчёта позиций текстов внутри карточки)."""
    cx, cy = _cell_center(day, slot)
    return cx - CARD_WIDTH / 2, cy - CARD_HEIGHT / 2


# =============================================================================
# Валидация
# =============================================================================

VALID_FORMATS = {"очно", "дистанционно", "гибрид"}


def _normalize_lesson_type(t: str) -> str:
    return (t or "").strip().lower()


def _colors_for_type(lesson_type: str) -> dict[str, str]:
    return COLORS_BY_TYPE.get(_normalize_lesson_type(lesson_type), COLORS_BY_TYPE["default"])


def _validate_lesson_payload(data: dict, *, partial: bool = False) -> None:
    """
    partial=False — все поля обязательны (создание).
    partial=True  — проверяем только то, что прислали (PATCH).
    """
    # Все поля, включая room, обязательны при создании.
    required = ["day", "slot", "subject", "lesson_type", "format", "teacher", "room"]
    if not partial:
        for key in required:
            value = data.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Поле '{key}' обязательно")

    if "day" in data and data["day"] not in DAYS:
        raise ValueError(f"day должен быть одним из {DAYS}")
    if "slot" in data and data["slot"] not in TIME_SLOTS:
        raise ValueError(f"slot должен быть одним из {TIME_SLOTS}")
    if "format" in data and data["format"] not in VALID_FORMATS:
        raise ValueError(f"format должен быть одним из {sorted(VALID_FORMATS)}")
    if "room" in data and isinstance(data["room"], str) and not data["room"].strip():
        raise ValueError("Поле 'room' не может быть пустой строкой")


# =============================================================================
# Карточка пары — композиция из 6 элементов
# =============================================================================

def _create_card_components(lesson: dict, frame_id: str) -> list[str]:
    """
    Создать на доске визуальную карточку пары как набор элементов.
    Возвращает СПИСОК ID всех созданных объектов — нужен, чтобы при удалении
    или обновлении карточки снести их все вместе.

    Композиция:
      [0] background — фоновая плашка с тонкой рамкой
      [1] spine — толстый цветной корешок слева
      [2] type_badge — text "ЛЕКЦИЯ" крупно цветом акцента
      [3] subject — text название дисциплины (самое крупное)
      [4] info — text "🏛 очно · ауд. 414"
      [5] teacher — text "👤 Иванов И.И."
    """
    colors = _colors_for_type(lesson["lesson_type"])
    accent = colors["accent"]
    fill = colors["fill"]

    ids: list[str] = []

    # Координаты карточки
    cx, cy = _cell_center(lesson["day"], lesson["slot"])
    left = cx - CARD_WIDTH / 2
    top = cy - CARD_HEIGHT / 2

    # --- 1. Фоновая плашка ---
    bg = miro_client.create_shape(
        content="",
        x=cx, y=cy, width=CARD_WIDTH, height=CARD_HEIGHT,
        fill_color=fill,
        border_color=accent,
        border_width=2,
        shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    ids.append(bg["id"])

    # --- 2. Цветной корешок слева ---
    spine_x = left + CARD_SPINE_WIDTH / 2 + 6  # 6 px отступ от края
    spine = miro_client.create_shape(
        content="",
        x=spine_x, y=cy,
        width=CARD_SPINE_WIDTH, height=CARD_HEIGHT - CARD_PAD_TOP - CARD_PAD_BOTTOM,
        fill_color=accent,
        border_color=accent,
        border_width=2,
        shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    ids.append(spine["id"])

    # --- 3-6. Текст. Считаем Y "сверху вниз" с учётом высоты каждого блока ---
    text_left = left + CARD_PAD_LEFT
    text_width = CARD_WIDTH - CARD_PAD_LEFT - CARD_PAD_RIGHT
    text_center_x = text_left + text_width / 2

    # Высота text-объекта в Miro расчитывается автоматически из ширины и шрифта.
    # Поэтому позиционируем тексты по их верхним краям, идя сверху вниз.
    # Используем `text` API — у него fontSize работает в честных пикселях.

    y_cursor = top + CARD_PAD_TOP

    # 3. Бейдж типа — большие капсы цветом акцента
    type_size = 22
    type_text = miro_client.create_text(
        content=f'<b>{lesson["lesson_type"].upper()}</b>',
        x=text_center_x,
        y=y_cursor + type_size / 2,  # text origin=center
        width=text_width,
        font_size=type_size,
        text_color=accent,
        text_align="left",
        parent_id=frame_id,
    )
    ids.append(type_text["id"])
    y_cursor += type_size + 12

    # 4. Название дисциплины — самое крупное, жирное
    subject_size = 32
    # Оценим высоту: ~1 строка ≈ subject_size * 1.3, разрешим 2 строки.
    subject_lines = 2
    subject_height = subject_size * 1.3 * subject_lines
    subject_text = miro_client.create_text(
        content=f'<b>{lesson["subject"]}</b>',
        x=text_center_x,
        y=y_cursor + subject_height / 2,
        width=text_width,
        font_size=subject_size,
        text_color=COLOR_INK,
        text_align="left",
        parent_id=frame_id,
    )
    ids.append(subject_text["id"])
    # Больше воздуха между дисциплиной и блоком "формат + аудитория"
    y_cursor += subject_height + 26

    # 5. Формат + аудитория одной строкой
    icon = FORMAT_ICONS.get(lesson["format"], "")
    room = lesson["room"]
    info_size = 22
    info_text = miro_client.create_text(
        content=f'{icon}&nbsp; {lesson["format"]}&nbsp; · &nbsp;<b>ауд. {room}</b>',
        x=text_center_x,
        y=y_cursor + info_size / 2,
        width=text_width,
        font_size=info_size,
        text_color=COLOR_INK,
        text_align="left",
        parent_id=frame_id,
    )
    ids.append(info_text["id"])
    # Чуть больше отступ перед именем преподавателя
    y_cursor += info_size + 16

    # 6. Преподаватель
    teacher_size = 20
    teacher_text = miro_client.create_text(
        content=f'👤&nbsp; {lesson["teacher"]}',
        x=text_center_x,
        y=y_cursor + teacher_size / 2,
        width=text_width,
        font_size=teacher_size,
        text_color=COLOR_INK_MUTED,
        text_align="left",
        parent_id=frame_id,
    )
    ids.append(teacher_text["id"])

    return ids


def _delete_card_components(item_ids: list[str]) -> None:
    """Удалить все элементы карточки. Не падаем, если что-то уже удалено вручную."""
    for item_id in item_ids:
        # Не знаем точно, shape это или text — пробуем оба эндпоинта.
        for try_delete in (miro_client.delete_shape, miro_client.delete_text):
            try:
                try_delete(item_id)
                break
            except miro_client.MiroError as e:
                if e.status == 404:
                    # Объект уже удалён или это другой тип — пробуем следующий тип
                    if try_delete is miro_client.delete_text:
                        break  # испробовали оба — сдаёмся молча
                    continue
                raise


# =============================================================================
# Шапка / время / placeholder — через composition (фон-shape + text)
# =============================================================================

def _make_title(frame_id: str, title: str) -> None:
    """Большая плашка титула: тёмный фон + крупный белый текст."""
    tx, ty = _title_center()
    width = _title_width()

    # Фоновая плашка
    miro_client.create_shape(
        content="",
        x=tx, y=ty, width=width, height=TITLE_HEIGHT,
        fill_color=COLOR_HEADER_BG, border_color=COLOR_HEADER_BG,
        border_width=0, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    # Заголовок — отдельный text, крупный
    title_size = 48
    miro_client.create_text(
        content=f'<b>{title}</b>',
        x=tx,
        y=ty - 18,  # сдвигаем чуть выше центра, чтобы под ним влез подзаголовок
        width=width - 60,
        font_size=title_size,
        text_color=COLOR_HEADER_TEXT,
        text_align="center",
        parent_id=frame_id,
    )

    # Подзаголовок — приглушённый
    miro_client.create_text(
        content=f'Понедельник — Суббота · {len(TIME_SLOTS)} пар в день',
        x=tx,
        y=ty + 30,
        width=width - 60,
        font_size=22,
        text_color="#94A3B8",
        text_align="center",
        parent_id=frame_id,
    )


def _make_day_header(frame_id: str, day: str) -> str:
    """Шапка дня: тёмный фон + крупный белый текст + цветная полоска снизу."""
    x, y = _day_header_center(day)

    # Фоновая плашка
    bg = miro_client.create_shape(
        content="",
        x=x, y=y, width=CARD_WIDTH, height=HEADER_HEIGHT,
        fill_color=COLOR_HEADER_BG, border_color=COLOR_HEADER_BG,
        border_width=0, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    # Название дня — крупный белый текст
    day_size = 32
    miro_client.create_text(
        content=f'<b>{day}</b>',
        x=x,
        y=y - 6,  # чуть выше центра, чтобы зрительно компенсировать полоску снизу
        width=CARD_WIDTH - 30,
        font_size=day_size,
        text_color=COLOR_HEADER_TEXT,
        text_align="center",
        parent_id=frame_id,
    )

    # Цветная полоска-акцент внизу
    ax, ay = _day_accent_center(day)
    miro_client.create_shape(
        content="",
        x=ax, y=ay, width=CARD_WIDTH - 40, height=12,
        fill_color=DAY_ACCENTS[day], border_color=DAY_ACCENTS[day],
        border_width=0, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    return bg["id"]


def _make_time_label(frame_id: str, slot: str) -> str:
    """Метка времени слева: светлая плашка + крупное время + подпись."""
    x, y = _time_label_center(slot)
    start, end = slot.split("-")

    # Фоновая плашка
    bg = miro_client.create_shape(
        content="",
        x=x, y=y, width=TIME_COL_WIDTH - 20, height=CARD_HEIGHT,
        fill_color=COLOR_PAPER, border_color=COLOR_BORDER,
        border_width=2, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    # Начало пары — крупное
    start_size = 32
    miro_client.create_text(
        content=f'<b>{start}</b>',
        x=x,
        y=y - 18,
        width=TIME_COL_WIDTH - 30,
        font_size=start_size,
        text_color=COLOR_INK,
        text_align="center",
        parent_id=frame_id,
    )

    # Окончание — приглушённое
    miro_client.create_text(
        content=f'до {end}',
        x=x,
        y=y + 22,
        width=TIME_COL_WIDTH - 30,
        font_size=20,
        text_color=COLOR_INK_MUTED,
        text_align="center",
        parent_id=frame_id,
    )

    return bg["id"]


def _make_placeholder(frame_id: str, day: str, slot: str) -> str:
    """Светлая placeholder-плашка в пустой ячейке. Возвращает ID плашки."""
    x, y = _cell_center(day, slot)
    bg = miro_client.create_shape(
        content="",
        x=x, y=y, width=CARD_WIDTH, height=CARD_HEIGHT,
        fill_color=COLOR_PAPER, border_color=COLOR_BORDER,
        border_width=2, shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    # Небольшой "—" по центру
    miro_client.create_text(
        content="—",
        x=x, y=y, width=80,
        font_size=28,
        text_color="#CBD5E1",
        text_align="center",
        parent_id=frame_id,
    )
    return bg["id"]


# =============================================================================
# Публичные операции
# =============================================================================

def init_board(title: str = "Расписание на неделю") -> dict:
    """
    Создать на доске Miro:
      1. Фрейм-контейнер
      2. Большую плашку с титулом
      3. Шапки дней (тёмные + цветной акцент)
      4. Колонку с временами
      5. Светлые placeholder-плашки во всех ячейках

    Идемпотентность: повторный вызов вернёт уже созданное состояние.
    Транзакционность: если на полпути упало, фрейм откатывается.
    """
    state = storage.load()
    if state.get("frame_id"):
        return {
            "frame_id": state["frame_id"],
            "header_ids": state.get("header_ids", {}),
            "time_label_ids": state.get("time_label_ids", {}),
            "message": "уже инициализирована",
        }

    width, height = _frame_size()
    frame = miro_client.create_frame(
        title=title, x=0, y=0, width=width, height=height,
        fill_color=COLOR_SURFACE,
    )
    frame_id = frame["id"]

    try:
        _make_title(frame_id, title)

        header_ids: dict[str, str] = {}
        for day in DAYS:
            header_ids[day] = _make_day_header(frame_id, day)

        time_label_ids: dict[str, str] = {}
        for slot in TIME_SLOTS:
            time_label_ids[slot] = _make_time_label(frame_id, slot)

        placeholder_ids: dict[str, str] = {}
        for day in DAYS:
            for slot in TIME_SLOTS:
                placeholder_ids[f"{day}|{slot}"] = _make_placeholder(frame_id, day, slot)
    except Exception:
        # Rollback: удаляем недоделанный фрейм
        try:
            miro_client.delete_frame(frame_id)
        except Exception:
            pass
        raise

    state["frame_id"] = frame_id
    state["header_ids"] = header_ids
    state["time_label_ids"] = time_label_ids
    state["placeholder_ids"] = placeholder_ids
    storage.save(state)

    return {
        "frame_id": frame_id,
        "header_ids": header_ids,
        "time_label_ids": time_label_ids,
        "message": "создана",
    }


def list_lessons(day: Optional[str] = None) -> list[dict]:
    lessons = list(storage.load()["lessons"].values())
    if day:
        lessons = [l for l in lessons if l["day"] == day]
    lessons.sort(key=lambda l: (DAYS.index(l["day"]), TIME_SLOTS.index(l["slot"])))
    return lessons


def _remove_placeholder(day: str, slot: str) -> None:
    state = storage.load()
    placeholders = state.get("placeholder_ids", {})
    key = f"{day}|{slot}"
    pid = placeholders.get(key)
    if pid:
        try:
            miro_client.delete_shape(pid)
        except miro_client.MiroError as e:
            if e.status != 404:
                raise
        del placeholders[key]
        state["placeholder_ids"] = placeholders
        storage.save(state)


def _restore_placeholder(day: str, slot: str) -> None:
    state = storage.load()
    if not state.get("frame_id"):
        return
    placeholders = state.get("placeholder_ids", {})
    key = f"{day}|{slot}"
    if key in placeholders:
        return
    new_id = _make_placeholder(state["frame_id"], day, slot)
    placeholders[key] = new_id
    state["placeholder_ids"] = placeholders
    storage.save(state)


def create_lesson(data: dict) -> dict:
    """Создать пару: убрать placeholder, отрисовать карточку, записать в storage."""
    _validate_lesson_payload(data, partial=False)

    if storage.find_lesson_by_slot(data["day"], data["slot"]) is not None:
        raise ValueError(
            f"На {data['day']} {data['slot']} уже есть пара. "
            "Удалите её или используйте PATCH для редактирования."
        )

    state = storage.load()
    if not state.get("frame_id"):
        init_board()
        state = storage.load()

    _remove_placeholder(data["day"], data["slot"])

    lesson_id = storage.new_lesson_id()
    lesson = {
        "id": lesson_id,
        "day": data["day"],
        "slot": data["slot"],
        "subject": data["subject"].strip(),
        "lesson_type": data["lesson_type"].strip(),
        "format": data["format"].strip(),
        "teacher": data["teacher"].strip(),
        "room": data["room"].strip(),
    }
    item_ids = _create_card_components(lesson, state["frame_id"])
    lesson["miro_item_ids"] = item_ids
    # Для обратной совместимости с прежней схемой:
    lesson["miro_item_id"] = item_ids[0] if item_ids else ""
    storage.add_lesson(lesson)
    return lesson


def update_lesson(lesson_id: str, patch: dict) -> dict:
    """
    Изменить пару. Стратегия: пересоздаём всю карточку — удаляем старые
    элементы, создаём новые. Это надёжнее, чем точечно патчить text-объекты
    (особенно если меняется длина названия дисциплины, текст переезжает).
    """
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")

    for forbidden in ("day", "slot"):
        if forbidden in patch and patch[forbidden] != lesson[forbidden]:
            raise ValueError(
                f"Нельзя изменить '{forbidden}' через PATCH. "
                f"Используйте /lessons/{lesson_id}/move."
            )

    _validate_lesson_payload(patch, partial=True)

    fields = {k: v.strip() if isinstance(v, str) else v
              for k, v in patch.items()
              if k in {"subject", "lesson_type", "format", "teacher", "room"}}
    if not fields:
        return lesson
    updated = storage.update_lesson(lesson_id, fields)

    # Снести старые элементы карточки и нарисовать заново
    old_ids = updated.get("miro_item_ids") or [updated.get("miro_item_id", "")]
    old_ids = [i for i in old_ids if i]
    _delete_card_components(old_ids)

    state = storage.load()
    new_ids = _create_card_components(updated, state["frame_id"])
    updated["miro_item_ids"] = new_ids
    updated["miro_item_id"] = new_ids[0] if new_ids else ""
    storage.update_lesson(lesson_id, updated)
    return updated


def move_lesson(lesson_id: str, new_day: str, new_slot: str) -> dict:
    """Перенос пары: удаляем старую карточку, ставим placeholder, рисуем в новой ячейке."""
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")
    if new_day not in DAYS:
        raise ValueError(f"day должен быть одним из {DAYS}")
    if new_slot not in TIME_SLOTS:
        raise ValueError(f"slot должен быть одним из {TIME_SLOTS}")

    if (new_day, new_slot) != (lesson["day"], lesson["slot"]):
        if storage.find_lesson_by_slot(new_day, new_slot) is not None:
            raise ValueError(f"На {new_day} {new_slot} уже есть другая пара")

    old_day, old_slot = lesson["day"], lesson["slot"]

    # Снести старые элементы карточки и вернуть placeholder
    old_ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
    old_ids = [i for i in old_ids if i]
    _delete_card_components(old_ids)
    _restore_placeholder(old_day, old_slot)

    # Создать карточку в новой ячейке
    _remove_placeholder(new_day, new_slot)
    lesson["day"] = new_day
    lesson["slot"] = new_slot
    state = storage.load()
    new_ids = _create_card_components(lesson, state["frame_id"])
    lesson["miro_item_ids"] = new_ids
    lesson["miro_item_id"] = new_ids[0] if new_ids else ""
    storage.update_lesson(lesson_id, lesson)
    return lesson


def delete_lesson(lesson_id: str) -> dict:
    """Удалить пару: снести все элементы карточки и вернуть placeholder."""
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")

    item_ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
    item_ids = [i for i in item_ids if i]
    _delete_card_components(item_ids)

    storage.remove_lesson(lesson_id)
    _restore_placeholder(lesson["day"], lesson["slot"])
    return lesson


def clear_all(delete_frame_too: bool = True) -> dict:
    """Снести всё расписание."""
    state = storage.load()
    deleted_cards = 0
    for lesson in list(state["lessons"].values()):
        item_ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
        item_ids = [i for i in item_ids if i]
        try:
            _delete_card_components(item_ids)
            deleted_cards += 1
        except miro_client.MiroError as e:
            if e.status != 404:
                raise

    if delete_frame_too and state.get("frame_id"):
        # Удаление фрейма унесёт все дочерние объекты (placeholder'ы, шапки, время)
        try:
            miro_client.delete_frame(state["frame_id"])
        except miro_client.MiroError as e:
            if e.status != 404:
                raise

    storage.reset()
    return {"deleted_cards": deleted_cards, "frame_deleted": delete_frame_too}