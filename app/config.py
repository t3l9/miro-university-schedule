"""
Конфигурация приложения.

Все настройки берутся из переменных окружения, чтобы не хранить токены в коде.
Файл .env (если есть) автоматически подгружается через python-dotenv.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Грузим .env из корня проекта (на уровень выше папки app/).
# override=False — переменные, уже заданные в окружении, имеют приоритет над .env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


# --- Miro API ---
MIRO_ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN", "")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID", "")
MIRO_API_BASE = "https://api.miro.com/v2"

# --- Flask / Uvicorn ---
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

# --- Локальное хранилище ---
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_FILE = BASE_DIR / "storage.json"

# --- Структура недели ---
DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

TIME_SLOTS = [
    "09:00-10:30",
    "10:40-12:10",
    "12:40-14:10",
    "14:20-15:50",
    "16:20-17:50",
    "18:00-19:30",
    "19:40-21:10",
]

# =============================================================================
# ДИЗАЙН-СИСТЕМА
# =============================================================================
# Идея: единая дизайн-палитра в стиле современных продуктовых интерфейсов
# (Linear / Notion / Vercel). Один основной тёмный цвет для шапок,
# мягкие пастельные заливки для типов пар, насыщенные акценты для полос.

# --- Базовые токены палитры ---
COLOR_INK        = "#0F172A"  # текст (slate-900) — почти чёрный
COLOR_INK_MUTED  = "#64748B"  # серый текст (slate-500) — для подписей
COLOR_PAPER      = "#FFFFFF"  # фон карточек
COLOR_SURFACE    = "#F8FAFC"  # фон сетки (slate-50)
COLOR_BORDER     = "#E2E8F0"  # рамки (slate-200)

COLOR_HEADER_BG    = "#1E293B"  # тёмная плашка шапки (slate-800)
COLOR_HEADER_TEXT  = "#F8FAFC"  # текст на тёмной шапке
COLOR_ACCENT       = "#3B82F6"  # фирменный синий (blue-500)

# --- Геометрия раскладки ---
# Координаты дочерних элементов фрейма отсчитываются от его левого-верхнего угла.
# Размеры подобраны под крупный читаемый текст (для экспорта в PDF / печати).
CARD_WIDTH = 420
CARD_HEIGHT = 280

COL_GAP = 20        # отступ между колонками-днями
ROW_GAP = 20        # отступ между строками-парами

TITLE_HEIGHT = 140  # высота большой плашки-титула наверху
HEADER_HEIGHT = 90  # высота шапки с названием дня
TIME_COL_WIDTH = 200

FRAME_PADDING = 60  # запас по краям фрейма


# --- Цвета для типов занятий ---
# Каждому типу — три цвета:
#   fill   — мягкая заливка карточки
#   accent — насыщенный цвет полосы-корешка слева и бейджа типа
#   badge_text — цвет текста на бейдже (обычно белый)
# Опираемся на палитру Tailwind для предсказуемости.
COLORS_BY_TYPE: dict[str, dict[str, str]] = {
    "лекция":       {"fill": "#EFF6FF", "accent": "#2563EB", "badge_text": "#FFFFFF"},  # blue
    "практика":     {"fill": "#ECFDF5", "accent": "#059669", "badge_text": "#FFFFFF"},  # emerald
    "лабораторная": {"fill": "#FFF7ED", "accent": "#EA580C", "badge_text": "#FFFFFF"},  # orange
    "семинар":      {"fill": "#FDF2F8", "accent": "#DB2777", "badge_text": "#FFFFFF"},  # pink
    "экзамен":      {"fill": "#FEF2F2", "accent": "#DC2626", "badge_text": "#FFFFFF"},  # red
    "консультация": {"fill": "#F5F3FF", "accent": "#7C3AED", "badge_text": "#FFFFFF"},  # violet
    "default":      {"fill": "#F8FAFC", "accent": "#64748B", "badge_text": "#FFFFFF"},  # slate
}

# --- Шапки дней ---
# Раньше тут была радуга — слишком пёстро. Новая концепция: все шапки
# в одном тёмно-синем тоне, но под каждой — тонкая цветная полоска-акцент.
# Это создаёт визуальный ритм без хаоса цветов.
# accent — цвет тонкой полоски-индикатора под названием дня.
DAY_ACCENTS: dict[str, str] = {
    "Понедельник": "#3B82F6",  # blue
    "Вторник":     "#06B6D4",  # cyan
    "Среда":       "#10B981",  # emerald
    "Четверг":     "#F59E0B",  # amber
    "Пятница":     "#EC4899",  # pink
    "Суббота":     "#8B5CF6",  # violet
}

# --- Иконки формата проведения ---
FORMAT_ICONS = {
    "очно": "🏛",
    "дистанционно": "💻",
    "гибрид": "🔀",
}