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
(+ для половинных карточек — маленький уголок-бейдж недели «I»/«II»).

Все элементы карточки склеиваются в Miro-группу (best-effort), чтобы
карточка перемещалась целиком, а не по отдельным объектам.

ЧЁТНОСТЬ НЕДЕЛИ (числитель/знаменатель):
  Ячейку (день × слот) можно занять либо одной парой «на каждую неделю»
  (week="обе", занимает всю ячейку), либо двумя половинами:
    нечётная (числитель, «I») — верхняя половина,
    чётная   (знаменатель, «II») — нижняя половина.
  Между половинами рисуется тонкий пунктир-разделитель.

При удалении/переносе пары мы храним массив всех её ID и удаляем все.
"""
from math import ceil
from typing import Optional

from . import miro_client, storage
from .config import (
    DAYS, TIME_SLOTS, COLORS_BY_TYPE, FORMAT_ICONS,
    DAY_ACCENTS,
    WEEKS, WEEK_BOTH, WEEK_ODD, WEEK_EVEN, WEEK_LABELS, WEEK_BADGE, WEEK_BADGE_BG,
    CARD_WIDTH, CARD_HEIGHT, COL_GAP, ROW_GAP,
    TITLE_HEIGHT, HEADER_HEIGHT, TIME_COL_WIDTH, FRAME_PADDING,
    SUBCELL_GAP, SUBCELL_DIVIDER_H, COLOR_SUBCELL_DIVIDER,
    COLOR_INK, COLOR_INK_MUTED, COLOR_PAPER, COLOR_SURFACE,
    COLOR_BORDER, COLOR_HEADER_BG, COLOR_HEADER_TEXT,
)


# =============================================================================
# Геометрия
# =============================================================================

# Ширина цветного корешка слева у карточки пары.
CARD_SPINE_WIDTH = 10

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


def _subcell_rect(day: str, slot: str, week: str) -> tuple[float, float, float, float]:
    """
    Прямоугольник (cx, cy, width, height) для пары с учётом чётности.

      week="обе"      → вся ячейка целиком;
      week="нечётная" → верхняя половина (числитель, «I»);
      week="чётная"   → нижняя половина (знаменатель, «II»).
    """
    cx, cy = _cell_center(day, slot)
    if week == WEEK_BOTH:
        return cx, cy, float(CARD_WIDTH), float(CARD_HEIGHT)

    half_h = (CARD_HEIGHT - SUBCELL_GAP) / 2
    offset = SUBCELL_GAP / 2 + half_h / 2
    if week == WEEK_ODD:
        return cx, cy - offset, float(CARD_WIDTH), float(half_h)
    if week == WEEK_EVEN:
        return cx, cy + offset, float(CARD_WIDTH), float(half_h)
    raise ValueError(f"Неизвестная чётность недели: {week}. Доступны: {WEEKS}")


def _divider_center(day: str, slot: str) -> tuple[float, float]:
    """Центр горизонтальной линии-разделителя числителя и знаменателя."""
    cx, cy = _cell_center(day, slot)
    return cx, cy


# =============================================================================
# Валидация
# =============================================================================

VALID_FORMATS = {"очно", "дистанционно", "гибрид"}


def _normalize_lesson_type(t: str) -> str:
    return (t or "").strip().lower()


def _normalize_week(w) -> str:
    w = (w or "").strip().lower() if isinstance(w, str) else WEEK_BOTH
    return w if w in WEEKS else WEEK_BOTH


def _colors_for_type(lesson_type: str) -> dict[str, str]:
    return COLORS_BY_TYPE.get(_normalize_lesson_type(lesson_type), COLORS_BY_TYPE["default"])


def _validate_lesson_payload(data: dict, *, partial: bool = False) -> None:
    """
    partial=False — все поля обязательны (создание).
    partial=True  — проверяем только то, что прислали (PATCH).
    """
    # Все поля, включая room, обязательны при создании. week — опционально (default "обе").
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
    if "week" in data and data["week"] not in WEEKS:
        raise ValueError(f"week должен быть одним из {WEEKS}")
    if "room" in data and isinstance(data["room"], str) and not data["room"].strip():
        raise ValueError("Поле 'room' не может быть пустой строкой")


# =============================================================================
# Карточка пары — композиция элементов
# =============================================================================

def _create_card_components(lesson: dict, frame_id: str) -> list[str]:
    """
    Создать на доске визуальную карточку пары как набор элементов.
    Возвращает СПИСОК ID всех созданных объектов — нужен, чтобы при удалении
    или обновлении карточки снести их все вместе.

    Содержимое центрируется по вертикали внутри (полу)ячейки, шрифты подобраны
    крупными — расписание должно читаться, даже когда доску «вписали в экран».

    Раскладка зависит от чётности недели:
      week="обе"  → полноразмерная карточка (на всю ячейку),
      week=полов. → компактная карточка в половине ячейки + уголок «I»/«II».
    """
    week = _normalize_week(lesson.get("week", WEEK_BOTH))
    compact = week != WEEK_BOTH

    colors = _colors_for_type(lesson["lesson_type"])
    accent = colors["accent"]
    fill = colors["fill"]

    ids: list[str] = []

    cx, cy, w, h = _subcell_rect(lesson["day"], lesson["slot"], week)
    left = cx - w / 2
    top = cy - h / 2

    if compact:
        pad_left = CARD_SPINE_WIDTH + 18
        pad_right = 18
        # В половинке мало места: тип уносим в инфо-строку.
        type_size, info_size, teacher_size = 0, 17, 0
        subj_base, subj_min, subj_max_lines = 22, 14, 2
        gap = 6
        show_type = False
    else:
        pad_left = CARD_PAD_LEFT
        pad_right = CARD_PAD_RIGHT
        type_size, info_size, teacher_size = 24, 24, 22
        subj_base, subj_min, subj_max_lines = 36, 18, 3
        gap = 10
        show_type = True

    # --- 1. Фоновая плашка ---
    bg = miro_client.create_shape(
        content="",
        x=cx, y=cy, width=w, height=h,
        fill_color=fill,
        border_color=accent,
        border_width=2,
        shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    ids.append(bg["id"])

    # --- 2. Цветной корешок слева (не доходит до скруглённых углов) ---
    spine_inset = 18
    spine_x = left + CARD_SPINE_WIDTH / 2 + 7
    spine = miro_client.create_shape(
        content="",
        x=spine_x, y=cy,
        width=CARD_SPINE_WIDTH, height=h - 2 * spine_inset,
        fill_color=accent,
        border_color=accent,
        border_width=2,
        shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    ids.append(spine["id"])

    # --- Текстовая колонка ---
    text_left = left + pad_left
    text_width = w - pad_left - pad_right
    text_center_x = text_left + text_width / 2

    def _est(font: int, lines: int = 1) -> float:
        """Грубая оценка высоты однострочного text-объекта Miro."""
        return font * 1.34 * lines

    def _subj_h(font: int, lines: int) -> float:
        """Высота названия — с запасом по межстрочному интервалу, чтобы не налезало."""
        return font * 1.42 * lines

    # Для длинных названий освобождаем строку преподавателя (уносим её в инфо),
    # чтобы у дисциплины было больше места по высоте.
    merge_teacher = (not compact) and len(lesson["subject"]) > 28
    if merge_teacher:
        subj_base, subj_max_lines = 30, 3
    teacher_in_info = compact or merge_teacher
    has_teacher_row = (not compact) and not merge_teacher

    # --- Адаптивный размер названия ---
    # Чем длиннее дисциплина, тем мельче шрифт и/или больше строк, пока всё не
    # уляжется в отведённую высоту в пределах subj_max_lines. Так длинные названия
    # не вылезают за карточку и не наезжают на строку с аудиторией.
    subject = lesson["subject"]
    pad_v = 16 if compact else 24
    fixed = _est(info_size) + gap
    if show_type:
        fixed += _est(type_size) + gap
    if has_teacher_row:
        fixed += _est(teacher_size) + gap
    avail_subject = (h - pad_v) - fixed

    def _chars_per_line(fs: int) -> int:
        # 0.64 — ширина символа относительно кегля (с запасом под open_sans)
        return max(1, int(text_width / (fs * 0.64)))

    def _wrap_lines(text: str, fs: int) -> int:
        """Сколько строк займёт текст при переносе ПО СЛОВАМ (как в Miro)."""
        cpl = _chars_per_line(fs)
        lines, cur = 1, 0
        for wd in text.split():
            wl = len(wd)
            if cur == 0:
                cur = wl            # первое слово строки кладём всегда
            elif cur + 1 + wl <= cpl:
                cur += 1 + wl
            else:
                lines += 1
                cur = wl
        return lines

    # Потолок шрифта, при котором самое длинное СЛОВО ещё влезает в строку целиком
    # (Miro переносит только по пробелам — неразрывное слово иначе вылезет вбок).
    max_word = max((len(w) for w in subject.split()), default=1)
    fs_cap = int(text_width / (max_word * 0.64))
    fs_hi = max(subj_min, min(subj_base, fs_cap))

    subject_size, subject_lines = subj_min, subj_max_lines
    for fs in range(fs_hi, subj_min - 1, -1):
        lines = _wrap_lines(subject, fs)
        if lines <= subj_max_lines and _subj_h(fs, lines) <= avail_subject:
            subject_size, subject_lines = fs, lines
            break
    else:
        subject_size = subj_min
        subject_lines = min(subj_max_lines, _wrap_lines(subject, subj_min))
    subject_h = _subj_h(subject_size, subject_lines)

    # Оценим суммарную высоту блока, чтобы отцентрировать его по вертикали.
    block_h = subject_h + gap + _est(info_size)
    if show_type:
        block_h += _est(type_size) + gap
    if has_teacher_row:
        block_h += gap + _est(teacher_size)

    pad_top_min = 8 if compact else 12
    y_cursor = top + max(pad_top_min, (h - block_h) / 2)

    # 3. Бейдж типа — капсы цветом акцента (в половинках не рисуем — нет места)
    if show_type:
        type_text = miro_client.create_text(
            content=f'<b>{lesson["lesson_type"].upper()}</b>',
            x=text_center_x,
            y=y_cursor + _est(type_size) / 2,
            width=text_width,
            font_size=type_size,
            text_color=accent,
            text_align="left",
            parent_id=frame_id,
        )
        ids.append(type_text["id"])
        y_cursor += _est(type_size) + gap

    # 4. Дисциплина — самое крупное, жирное (размер подобран адаптивно выше)
    subject_text = miro_client.create_text(
        content=f'<b>{lesson["subject"]}</b>',
        x=text_center_x,
        y=y_cursor + subject_h / 2,
        width=text_width,
        font_size=subject_size,
        text_color=COLOR_INK,
        text_align="left",
        parent_id=frame_id,
    )
    ids.append(subject_text["id"])
    y_cursor += subject_h + gap

    icon = FORMAT_ICONS.get(lesson["format"], "")
    room = lesson["room"]

    if teacher_in_info:
        # Инфо-строка с преподавателем (половинки и длинные названия)
        info_text = miro_client.create_text(
            content=(f'<b>{lesson["lesson_type"]}</b>&nbsp; · &nbsp;'
                     f'ауд. {room}&nbsp; · &nbsp;{lesson["teacher"]}'),
            x=text_center_x,
            y=y_cursor + _est(info_size) / 2,
            width=text_width,
            font_size=info_size,
            text_color=COLOR_INK_MUTED,
            text_align="left",
            parent_id=frame_id,
        )
        ids.append(info_text["id"])
    else:
        # Формат + аудитория, отдельной строкой
        info_text = miro_client.create_text(
            content=f'{icon}&nbsp; {lesson["format"]}&nbsp; · &nbsp;<b>ауд. {room}</b>',
            x=text_center_x,
            y=y_cursor + _est(info_size) / 2,
            width=text_width,
            font_size=info_size,
            text_color=COLOR_INK,
            text_align="left",
            parent_id=frame_id,
        )
        ids.append(info_text["id"])

    if has_teacher_row:
        y_cursor += _est(info_size) + gap
        teacher_text = miro_client.create_text(
            content=f'👤&nbsp; {lesson["teacher"]}',
            x=text_center_x,
            y=y_cursor + _est(teacher_size) / 2,
            width=text_width,
            font_size=teacher_size,
            text_color=COLOR_INK_MUTED,
            text_align="left",
            parent_id=frame_id,
        )
        ids.append(teacher_text["id"])

    # --- Уголок-бейдж недели (только для половинок) ---
    if compact:
        badge_w, badge_h = 46, 30
        badge_cx = left + w - pad_right - badge_w / 2 + 8
        badge_cy = top + 8 + badge_h / 2
        badge_bg = miro_client.create_shape(
            content="",
            x=badge_cx, y=badge_cy, width=badge_w, height=badge_h,
            fill_color=WEEK_BADGE_BG[week], border_color=WEEK_BADGE_BG[week],
            border_width=2, shape_kind="round_rectangle",
            parent_id=frame_id,
        )
        ids.append(badge_bg["id"])
        badge_text = miro_client.create_text(
            content=f'<b>{WEEK_BADGE[week]}</b>',
            x=badge_cx, y=badge_cy, width=badge_w,
            font_size=18, text_color="#FFFFFF",
            text_align="center", parent_id=frame_id,
        )
        ids.append(badge_text["id"])

    return ids


def _group_card(item_ids: list[str], lesson: dict) -> Optional[str]:
    """Best-effort: склеить элементы карточки в группу. Вернуть group_id или None."""
    group = miro_client.create_group(item_ids)
    return group.get("id") if group else None


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
                    if try_delete is miro_client.delete_text:
                        break  # испробовали оба — сдаёмся молча
                    continue
                raise


def _card_anchor_id(lesson: dict) -> Optional[str]:
    """ID опорного элемента карточки (фоновая плашка) — по нему читаем позицию с доски."""
    ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
    ids = [i for i in ids if i]
    return ids[0] if ids else None


# =============================================================================
# Шапка / время — через composition (фон-shape + text)
# =============================================================================

def _make_title(frame_id: str, title: str) -> None:
    """Большая плашка титула: тёмный фон + крупный белый текст + легенда недель."""
    tx, ty = _title_center()
    width = _title_width()

    miro_client.create_shape(
        content="",
        x=tx, y=ty, width=width, height=TITLE_HEIGHT,
        fill_color=COLOR_HEADER_BG, border_color=COLOR_HEADER_BG,
        border_width=0, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    title_size = 48
    miro_client.create_text(
        content=f'<b>{title}</b>',
        x=tx,
        y=ty - 44,
        width=width - 60,
        font_size=title_size,
        text_color=COLOR_HEADER_TEXT,
        text_align="center",
        parent_id=frame_id,
    )

    miro_client.create_text(
        content=f'Понедельник — Суббота · {len(TIME_SLOTS)} пар в день',
        x=tx,
        y=ty + 2,
        width=width - 60,
        font_size=26,
        text_color="#CBD5E1",
        text_align="center",
        parent_id=frame_id,
    )

    # Легенда чётности недели — чтобы деление ячеек читалось интуитивно.
    miro_client.create_text(
        content=(
            'Ячейка делится: верх — <b>I, числитель (нечётная)</b>, '
            'низ — <b>II, знаменатель (чётная)</b>. '
            'Пара на всю ячейку идёт каждую неделю.'
        ),
        x=tx,
        y=ty + 48,
        width=width - 60,
        font_size=20,
        text_color="#94A3B8",
        text_align="center",
        parent_id=frame_id,
    )


def _make_day_header(frame_id: str, day: str) -> str:
    """Шапка дня: тёмный фон + крупный белый текст + цветная полоска снизу."""
    x, y = _day_header_center(day)

    bg = miro_client.create_shape(
        content="",
        x=x, y=y, width=CARD_WIDTH, height=HEADER_HEIGHT,
        fill_color=COLOR_HEADER_BG, border_color=COLOR_HEADER_BG,
        border_width=0, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

    day_size = 32
    miro_client.create_text(
        content=f'<b>{day}</b>',
        x=x,
        y=y - 6,
        width=CARD_WIDTH - 30,
        font_size=day_size,
        text_color=COLOR_HEADER_TEXT,
        text_align="center",
        parent_id=frame_id,
    )

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

    bg = miro_client.create_shape(
        content="",
        x=x, y=y, width=TIME_COL_WIDTH - 20, height=CARD_HEIGHT,
        fill_color=COLOR_PAPER, border_color=COLOR_BORDER,
        border_width=2, shape_kind="round_rectangle",
        parent_id=frame_id,
    )

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


# =============================================================================
# Плейсхолдеры и разделитель — модель «желаемого состояния» ячейки
# =============================================================================
# В placeholder_ids под ключами вида "<day>|<slot>|<что>" храним СПИСКИ id всех
# вспомогательных элементов ячейки (плашка + её «—», линия-разделитель), чтобы
# при пересборке снести ровно их и не плодить «осиротевшие» тексты.

def _ph_prefix(day: str, slot: str) -> str:
    return f"{day}|{slot}|"


def _make_placeholder(frame_id: str, day: str, slot: str, week: str) -> list[str]:
    """Светлая placeholder-плашка в (полу)ячейке. Возвращает список созданных id."""
    cx, cy, w, h = _subcell_rect(day, slot, week)
    ids: list[str] = []
    bg = miro_client.create_shape(
        content="",
        x=cx, y=cy, width=w, height=h,
        fill_color=COLOR_PAPER, border_color=COLOR_BORDER,
        border_width=2, shape_kind="round_rectangle",
        parent_id=frame_id,
    )
    ids.append(bg["id"])
    dash = miro_client.create_text(
        content="—",
        x=cx, y=cy, width=80,
        font_size=24 if week != WEEK_BOTH else 28,
        text_color="#CBD5E1",
        text_align="center",
        parent_id=frame_id,
    )
    ids.append(dash["id"])
    return ids


def _make_divider(frame_id: str, day: str, slot: str) -> list[str]:
    """Тонкая линия-разделитель числителя и знаменателя по центру ячейки."""
    cx, cy = _divider_center(day, slot)
    line = miro_client.create_shape(
        content="",
        x=cx, y=cy, width=CARD_WIDTH - 60, height=SUBCELL_DIVIDER_H,
        fill_color=COLOR_SUBCELL_DIVIDER, border_color=COLOR_SUBCELL_DIVIDER,
        border_width=0, shape_kind="rectangle",
        parent_id=frame_id,
    )
    return [line["id"]]


def _delete_managed(ids) -> None:
    """Удалить вспомогательные элементы (плашки/тексты/линии). Тихо игнорим 404."""
    if isinstance(ids, str):
        ids = [ids]
    for item_id in ids or []:
        for try_delete in (miro_client.delete_shape, miro_client.delete_text):
            try:
                try_delete(item_id)
                break
            except miro_client.MiroError as e:
                if e.status == 404:
                    if try_delete is miro_client.delete_text:
                        break
                    continue
                raise


def _reconcile_placeholders(day: str, slot: str) -> None:
    """
    Привести вспомогательные элементы ячейки к «желаемому состоянию» исходя из
    того, какие пары сейчас в ней лежат (по storage):

      пусто                         → одна полноразмерная плашка-плейсхолдер;
      пара "обе"                    → ничего (карточка занимает всю ячейку);
      только числитель/знаменатель  → разделитель + плашка в пустой половине;
      обе половины заняты           → только разделитель.

    Работает идемпотентно: сносит все текущие вспомогательные элементы ячейки
    и создаёт нужные заново.
    """
    state = storage.load()
    frame_id = state.get("frame_id")
    if not frame_id:
        return

    placeholders: dict = state.get("placeholder_ids", {})

    # 1. Снести всё, что сейчас относится к этой ячейке.
    prefix = _ph_prefix(day, slot)
    for key in [k for k in placeholders if k.startswith(prefix)]:
        _delete_managed(placeholders.pop(key))

    # 2. Понять занятость ячейки.
    cell = storage.find_lessons_in_cell(day, slot)
    weeks_here = {_normalize_week(l.get("week", WEEK_BOTH)) for l in cell}
    has_both = WEEK_BOTH in weeks_here
    has_odd = WEEK_ODD in weeks_here
    has_even = WEEK_EVEN in weeks_here

    # 3. Построить желаемые элементы.
    if has_both:
        pass  # вся ячейка занята — ни плашек, ни разделителя
    elif not has_odd and not has_even:
        placeholders[prefix + WEEK_BOTH] = _make_placeholder(frame_id, day, slot, WEEK_BOTH)
    else:
        placeholders[prefix + "__div__"] = _make_divider(frame_id, day, slot)
        if not has_odd:
            placeholders[prefix + WEEK_ODD] = _make_placeholder(frame_id, day, slot, WEEK_ODD)
        if not has_even:
            placeholders[prefix + WEEK_EVEN] = _make_placeholder(frame_id, day, slot, WEEK_EVEN)

    state["placeholder_ids"] = placeholders
    storage.save(state)


# =============================================================================
# Публичные операции
# =============================================================================

def init_board(title: str = "Расписание на неделю") -> dict:
    """
    Создать на доске Miro:
      1. Фрейм-контейнер
      2. Большую плашку с титулом + легенду чётности недели
      3. Шапки дней (тёмные + цветной акцент)
      4. Колонку с временами
      5. Полноразмерные placeholder-плашки во всех (пустых) ячейках

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

        placeholder_ids: dict[str, list[str]] = {}
        for day in DAYS:
            for slot in TIME_SLOTS:
                # Пустая ячейка → одна полноразмерная плашка.
                placeholder_ids[_ph_prefix(day, slot) + WEEK_BOTH] = \
                    _make_placeholder(frame_id, day, slot, WEEK_BOTH)
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


def list_lessons(day: Optional[str] = None, week: Optional[str] = None) -> list[dict]:
    lessons = list(storage.load()["lessons"].values())
    if day:
        lessons = [l for l in lessons if l["day"] == day]
    if week:
        lessons = [l for l in lessons if _normalize_week(l.get("week", WEEK_BOTH)) == week]
    lessons.sort(key=lambda l: (
        DAYS.index(l["day"]),
        TIME_SLOTS.index(l["slot"]),
        WEEKS.index(_normalize_week(l.get("week", WEEK_BOTH))),
    ))
    return lessons


def get_schedule_grid() -> dict:
    """
    Вернуть расписание как удобную для клиента сетку:
    строки — слоты, столбцы — дни, в каждой ячейке три ячейки чётности.
    """
    lessons = list(storage.load()["lessons"].values())

    def cell(day: str, slot: str) -> dict:
        out = {WEEK_BOTH: None, WEEK_ODD: None, WEEK_EVEN: None}
        for l in lessons:
            if l["day"] == day and l["slot"] == slot:
                out[_normalize_week(l.get("week", WEEK_BOTH))] = l
        return out

    rows = []
    for slot in TIME_SLOTS:
        rows.append({
            "slot": slot,
            "cells": {day: cell(day, slot) for day in DAYS},
        })

    return {"days": DAYS, "slots": TIME_SLOTS, "weeks": WEEKS, "rows": rows}


def create_lesson(data: dict) -> dict:
    """Создать пару: проверить конфликт по чётности, отрисовать карточку, пересобрать ячейку."""
    _validate_lesson_payload(data, partial=False)
    week = _normalize_week(data.get("week", WEEK_BOTH))

    conflict = storage.find_conflict(data["day"], data["slot"], week)
    if conflict is not None:
        raise ValueError(
            f"На {data['day']} {data['slot']} ({WEEK_LABELS[week]}) уже есть пара "
            f"«{conflict['subject']}» ({WEEK_LABELS[_normalize_week(conflict.get('week', WEEK_BOTH))]}). "
            "Освободите место, смените чётность недели или используйте PATCH."
        )

    state = storage.load()
    if not state.get("frame_id"):
        init_board()
        state = storage.load()

    lesson_id = storage.new_lesson_id()
    lesson = {
        "id": lesson_id,
        "day": data["day"],
        "slot": data["slot"],
        "week": week,
        "subject": data["subject"].strip(),
        "lesson_type": data["lesson_type"].strip(),
        "format": data["format"].strip(),
        "teacher": data["teacher"].strip(),
        "room": data["room"].strip(),
    }
    item_ids = _create_card_components(lesson, state["frame_id"])
    lesson["miro_item_ids"] = item_ids
    lesson["miro_item_id"] = item_ids[0] if item_ids else ""
    lesson["miro_group_id"] = _group_card(item_ids, lesson)
    storage.add_lesson(lesson)

    _reconcile_placeholders(data["day"], data["slot"])
    return lesson


def update_lesson(lesson_id: str, patch: dict) -> dict:
    """
    Изменить пару (кроме day/slot/week — их меняем через /move).
    Стратегия: пересоздаём всю карточку.
    """
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")

    for forbidden in ("day", "slot", "week"):
        if forbidden in patch and patch[forbidden] != lesson.get(forbidden):
            raise ValueError(
                f"Нельзя изменить '{forbidden}' через PATCH. "
                f"Используйте POST /lessons/{lesson_id}/move."
            )

    _validate_lesson_payload(patch, partial=True)

    fields = {k: v.strip() if isinstance(v, str) else v
              for k, v in patch.items()
              if k in {"subject", "lesson_type", "format", "teacher", "room"}}
    if not fields:
        return lesson
    updated = storage.update_lesson(lesson_id, fields)

    old_ids = updated.get("miro_item_ids") or [updated.get("miro_item_id", "")]
    old_ids = [i for i in old_ids if i]
    _delete_card_components(old_ids)

    state = storage.load()
    new_ids = _create_card_components(updated, state["frame_id"])
    updated["miro_item_ids"] = new_ids
    updated["miro_item_id"] = new_ids[0] if new_ids else ""
    updated["miro_group_id"] = _group_card(new_ids, updated)
    storage.update_lesson(lesson_id, updated)
    return updated


def move_lesson(lesson_id: str, new_day: str, new_slot: str,
                new_week: Optional[str] = None) -> dict:
    """
    Перенос пары в другую ячейку и/или смену чётности недели.
    Сносим старую карточку, рисуем в новой позиции, пересобираем обе ячейки.
    """
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")
    if new_day not in DAYS:
        raise ValueError(f"day должен быть одним из {DAYS}")
    if new_slot not in TIME_SLOTS:
        raise ValueError(f"slot должен быть одним из {TIME_SLOTS}")

    target_week = _normalize_week(new_week if new_week is not None
                                  else lesson.get("week", WEEK_BOTH))

    if (new_day, new_slot, target_week) != (
        lesson["day"], lesson["slot"], _normalize_week(lesson.get("week", WEEK_BOTH))
    ):
        conflict = storage.find_conflict(new_day, new_slot, target_week, exclude_id=lesson_id)
        if conflict is not None:
            raise ValueError(
                f"На {new_day} {new_slot} ({WEEK_LABELS[target_week]}) "
                f"уже есть другая пара «{conflict['subject']}»"
            )

    old_day, old_slot = lesson["day"], lesson["slot"]

    old_ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
    old_ids = [i for i in old_ids if i]
    _delete_card_components(old_ids)

    lesson["day"] = new_day
    lesson["slot"] = new_slot
    lesson["week"] = target_week
    state = storage.load()
    new_ids = _create_card_components(lesson, state["frame_id"])
    lesson["miro_item_ids"] = new_ids
    lesson["miro_item_id"] = new_ids[0] if new_ids else ""
    lesson["miro_group_id"] = _group_card(new_ids, lesson)
    storage.update_lesson(lesson_id, lesson)

    # Пересобрать вспомогательные элементы в обеих затронутых ячейках.
    _reconcile_placeholders(old_day, old_slot)
    _reconcile_placeholders(new_day, new_slot)
    return lesson


def delete_lesson(lesson_id: str) -> dict:
    """Удалить пару: снести все элементы карточки и пересобрать ячейку."""
    lesson = storage.get_lesson(lesson_id)
    if lesson is None:
        raise LookupError(f"Пара {lesson_id} не найдена")

    item_ids = lesson.get("miro_item_ids") or [lesson.get("miro_item_id", "")]
    item_ids = [i for i in item_ids if i]
    _delete_card_components(item_ids)

    storage.remove_lesson(lesson_id)
    _reconcile_placeholders(lesson["day"], lesson["slot"])
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
        try:
            miro_client.delete_frame(state["frame_id"])
        except miro_client.MiroError as e:
            if e.status != 404:
                raise

    storage.reset()
    return {"deleted_cards": deleted_cards, "frame_deleted": delete_frame_too}


# =============================================================================
# Чтение расписания с доски — актуальные позиции карточек
# =============================================================================

def _item_xy(item: dict) -> tuple[float, float]:
    """Достать координаты центра элемента из ответа Miro."""
    pos = item.get("position") or {}
    return float(pos.get("x", 0.0)), float(pos.get("y", 0.0))


def _calibrate(by_id: dict, state: dict) -> tuple[dict, dict]:
    """
    Откалибровать реальные координаты колонок (X по дням) и строк (Y по слотам)
    по фактическому положению шапок дней и меток времени на доске.

    Это делает обратное отображение независимым от того, в какой системе
    координат Miro отдаёт позиции дочерних элементов фрейма — мы сравниваем
    карточки с теми же «якорями», что рисовали сами.
    """
    day_x: dict[str, float] = {}
    for day, hid in (state.get("header_ids") or {}).items():
        it = by_id.get(hid)
        if it is not None:
            day_x[day] = _item_xy(it)[0]
    for day in DAYS:
        day_x.setdefault(day, _day_header_center(day)[0])

    slot_y: dict[str, float] = {}
    for slot, tid in (state.get("time_label_ids") or {}).items():
        it = by_id.get(tid)
        if it is not None:
            slot_y[slot] = _item_xy(it)[1]
    for slot in TIME_SLOTS:
        slot_y.setdefault(slot, _time_label_center(slot)[1])

    return day_x, slot_y


def _detect_week(y: float, slot_center_y: float) -> str:
    """Грубо определить числитель/знаменатель по вертикальному смещению от центра слота."""
    threshold = (CARD_HEIGHT - SUBCELL_GAP) / 4  # ~ четверть высоты ячейки
    if y < slot_center_y - threshold:
        return WEEK_ODD
    if y > slot_center_y + threshold:
        return WEEK_EVEN
    return WEEK_BOTH


def sync_from_board(preview: bool = False, detect_week: bool = False) -> dict:
    """
    Прочитать актуальные позиции карточек на доске и сопоставить их сетке.

    Когда расписание правили прямо в Miro, считываем новое положение каждой
    карточки, определяем для неё ближайшую ячейку (день × слот) и обновляем
    локальное хранилище.

    preview=True   — только показать, что считалось, ничего не записывая.
    detect_week=True — пытаться определить ещё и чётность недели по тому,
                       в верхней или нижней половине ячейки лежит карточка
                       (по умолчанию чётность сохраняем как была).

    Карточки на доске не двигаем (они остаются на своих местах);
    обновляем только метаданные и пересобираем плейсхолдеры.
    """
    state = storage.load()
    if not state.get("frame_id"):
        raise LookupError("Доска не инициализирована — нечего синхронизировать. Сначала POST /api/board/init.")

    items = miro_client.list_items()
    by_id = {it.get("id"): it for it in items if it.get("id")}
    day_x, slot_y = _calibrate(by_id, state)

    moved: list[dict] = []
    missing: list[dict] = []
    proposals: list[tuple[str, str, str, str]] = []  # (lesson_id, day, slot, week)

    for lesson in state["lessons"].values():
        anchor = _card_anchor_id(lesson)
        it = by_id.get(anchor) if anchor else None
        if it is None:
            missing.append({"id": lesson["id"], "subject": lesson.get("subject", "")})
            continue

        x, y = _item_xy(it)
        new_day = min(day_x, key=lambda d: abs(day_x[d] - x))
        new_slot = min(slot_y, key=lambda s: abs(slot_y[s] - y))
        cur_week = _normalize_week(lesson.get("week", WEEK_BOTH))
        new_week = cur_week
        if detect_week and cur_week != WEEK_BOTH:
            detected = _detect_week(y, slot_y[new_slot])
            if detected != WEEK_BOTH:
                new_week = detected

        proposals.append((lesson["id"], new_day, new_slot, new_week))

        if (new_day, new_slot, new_week) != (lesson["day"], lesson["slot"], cur_week):
            moved.append({
                "id": lesson["id"],
                "subject": lesson.get("subject", ""),
                "from": {"day": lesson["day"], "slot": lesson["slot"], "week": cur_week},
                "to": {"day": new_day, "slot": new_slot, "week": new_week},
            })

    # Конфликты: две пары претендуют на одну (день, слот, чётность).
    occupancy: dict[tuple, list[str]] = {}
    for lid, d, s, w in proposals:
        occupancy.setdefault((d, s, w), []).append(lid)
    conflicts = []
    lessons_map = state["lessons"]
    for (d, s, w), lids in occupancy.items():
        # "обе" + любая половина в той же ячейке тоже конфликт
        same_cell = [(d2, s2, w2, lid2) for (lid2, d2, s2, w2) in proposals if d2 == d and s2 == s]
        if len(lids) > 1:
            conflicts.append({
                "day": d, "slot": s, "week": w,
                "lessons": [{"id": lid, "subject": lessons_map[lid].get("subject", "")} for lid in lids],
            })

    if preview:
        return {
            "preview": True,
            "moved": moved,
            "conflicts": conflicts,
            "missing_on_board": missing,
            "message": "Предпросмотр: storage не изменён.",
        }

    # Применяем: обновляем day/slot/week, копим затронутые ячейки для пересборки.
    affected: set[tuple[str, str]] = set()
    for lid, d, s, w in proposals:
        old = lessons_map[lid]
        affected.add((old["day"], old["slot"]))
        affected.add((d, s))
        storage.update_lesson(lid, {"day": d, "slot": s, "week": w})

    for d, s in affected:
        _reconcile_placeholders(d, s)

    return {
        "preview": False,
        "moved": moved,
        "conflicts": conflicts,
        "missing_on_board": missing,
        "lessons": list_lessons(),
        "message": f"Синхронизировано. Перемещено карточек: {len(moved)}.",
    }
