"""
Тонкая обёртка над Miro REST API v2.

Документация:
  https://developers.miro.com/reference/overview

Используем только то, что нужно для расписания:
  - frame (контейнер для всей сетки расписания)
  - text  (заголовки дней и подписи времени)
  - shape (карточка одной пары)

Внутри настроен requests.Session с пулом соединений и автоматическим
повтором запросов при сетевых сбоях (например, обрывы SSL-handshake,
которые случаются из-за антивирусов/прокси с инспекцией трафика).
"""
import time
import requests
from typing import Optional
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from .config import MIRO_ACCESS_TOKEN, MIRO_BOARD_ID, MIRO_API_BASE


class MiroError(Exception):
    """Поднимается, когда Miro API вернул не-2xx ответ."""

    def __init__(self, status: int, message: str, payload: Optional[dict] = None):
        super().__init__(f"Miro API {status}: {message}")
        self.status = status
        self.payload = payload


# --- HTTP Session с ретраями ---
#
# Retry автоматически переоткрывает соединение, если упало по сети.
# total=4         — суммарно до 4 повторов
# backoff_factor  — паузы 0.5s, 1s, 2s, 4s между попытками
# status_forcelist — на каких HTTP-кодах тоже ретраить (от Miro иногда прилетают 429/502/503/504)
# allowed_methods=None — ретраить все методы, включая POST/PATCH/DELETE
#                       (по умолчанию urllib3 ретраит только idempotent методы)
_retry = Retry(
    total=4,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=None,
    raise_on_status=False,
)
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=10, pool_maxsize=10)
_session = requests.Session()
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def _headers() -> dict:
    if not MIRO_ACCESS_TOKEN:
        raise MiroError(500, "MIRO_ACCESS_TOKEN не задан в переменных окружения")
    return {
        "Authorization": f"Bearer {MIRO_ACCESS_TOKEN}",
        "accept": "application/json",
        "content-type": "application/json",
    }


def _board_id(board_id: Optional[str] = None) -> str:
    bid = board_id or MIRO_BOARD_ID
    if not bid:
        raise MiroError(500, "MIRO_BOARD_ID не задан и не передан в запросе")
    return bid


def _request(method: str, path: str, *, board_id: Optional[str] = None,
             json: Optional[dict] = None) -> dict:
    """
    Универсальный вызов Miro API.

    Поверх ретраев из urllib3 добавляем свой внешний цикл — на случай чисто
    сетевых исключений (SSLError, ConnectionError), которые urllib3 умеет,
    но иногда не докрывает (особенно при SSL-инспекции в антивирусах).
    """
    url = f"{MIRO_API_BASE}/boards/{_board_id(board_id)}{path}"

    last_exc: Optional[Exception] = None
    for attempt in range(3):  # 3 захода с экспоненциальной паузой
        try:
            resp = _session.request(method, url, headers=_headers(),
                                    json=json, timeout=20)
            break
        except (requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            last_exc = e
            # Пауза 0.7s, 1.4s, 2.8s перед следующей попыткой
            time.sleep(0.7 * (2 ** attempt))
    else:
        # Все попытки исчерпаны — поднимаем понятную ошибку
        raise MiroError(
            503,
            f"Сеть до Miro API нестабильна ({type(last_exc).__name__}: {last_exc}). "
            f"Часто причина — антивирус/файрвол с инспекцией SSL или VPN. "
            f"Попробуй временно отключить их или сменить сеть.",
            None,
        )

    if not resp.ok:
        try:
            payload = resp.json()
            message = payload.get("message") or payload.get("type") or resp.text
        except ValueError:
            payload = None
            message = resp.text
        raise MiroError(resp.status_code, message, payload)
    # DELETE возвращает 204 без тела
    if resp.status_code == 204 or not resp.text:
        return {}
    return resp.json()


# ============================================================
# FRAME — контейнер для всего расписания
# ============================================================

def create_frame(title: str, x: float, y: float, width: float, height: float,
                 fill_color: str = "#FFFFFFFF",
                 board_id: Optional[str] = None) -> dict:
    """Создать фрейм. В фрейме потом удобно держать всю сетку расписания."""
    body = {
        "data": {"title": title, "format": "custom", "type": "freeform"},
        "style": {"fillColor": fill_color},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width, "height": height},
    }
    return _request("POST", "/frames", board_id=board_id, json=body)


def delete_frame(frame_id: str, board_id: Optional[str] = None) -> None:
    _request("DELETE", f"/frames/{frame_id}", board_id=board_id)


# ============================================================
# TEXT — для заголовков дней и временных меток
# ============================================================

def create_text(content: str, x: float, y: float, width: float = 200,
                parent_id: Optional[str] = None, font_size: int = 18,
                bold: bool = False,
                text_color: str = "#1A1A1A",
                fill_color: Optional[str] = None,
                font_family: str = "open_sans",
                text_align: str = "center",
                board_id: Optional[str] = None) -> dict:
    """
    Создать текстовый объект.

    text_color — цвет шрифта (HEX).
    fill_color — цвет фона плашки (HEX); None = прозрачный фон.
    bold — оборачиваем содержимое в <b>...</b>.
    font_size — размер в пикселях (1..288). У text API это работает в
                ПИКСЕЛЯХ, в отличие от shape, где размер часто игнорируется
                inline-CSS в HTML.
    text_align — 'left' / 'center' / 'right'.

    Особенность Miro: минимальная ширина text-объекта = 1.7 × font_size.
    Если запросили меньше — поднимаем до минимума.
    """
    # Валидация font_size — у Miro потолок 288.
    font_size = max(1, min(int(font_size), 288))

    # Минимальная ширина по правилу Miro
    min_width = 1.7 * font_size
    width = max(float(width), min_width)

    style: dict = {
        "fontSize": str(font_size),
        "textAlign": text_align,
        "color": text_color,
        "fontFamily": font_family,
    }
    if fill_color is not None:
        style["fillColor"] = fill_color
        style["fillOpacity"] = "1.0"

    body: dict = {
        "data": {"content": f"<b>{content}</b>" if bold else content},
        "style": style,
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    if parent_id:
        body["parent"] = {"id": parent_id}
    return _request("POST", "/texts", board_id=board_id, json=body)


def delete_text(text_id: str, board_id: Optional[str] = None) -> None:
    _request("DELETE", f"/texts/{text_id}", board_id=board_id)


# ============================================================
# SHAPE — карточка одной пары
# ============================================================
# В Miro у обычной "card" нет нормальной заливки фона и плохо видна вся
# информация. Поэтому пары рисуем как round_rectangle shape с заливкой,
# цветной рамкой и HTML-содержимым в data.content.

def create_shape(content: str, x: float, y: float, width: float, height: float,
                 fill_color: str, border_color: str,
                 shape_kind: str = "round_rectangle",
                 border_width: float = 3,
                 text_align: str = "left",
                 text_align_vertical: str = "top",
                 padding: int = 0,  # noqa: для совместимости с вызовами; Miro padding не поддерживает
                 parent_id: Optional[str] = None,
                 board_id: Optional[str] = None) -> dict:
    """
    Создать shape с HTML-текстом внутри.

    fill_color  — заливка прямоугольника (HEX)
    border_color — цвет рамки (HEX); используется как акцент по типу пары
    shape_kind  — 'round_rectangle' даёт приятные скруглённые углы
    text_align  — 'left' / 'center' / 'right'
    text_align_vertical — 'top' / 'middle' / 'bottom'
    padding     — параметр существует для совместимости; реальный padding в Miro
                  не поддерживается, отступы делаются через margin в HTML.
    """
    _ = padding  # параметр игнорируется

    # Miro API имеет минимальные размеры shape: ширина и высота должны быть >= 8.
    # Если запросили меньше — округляем вверх, чтобы не получать 400 от API.
    width = max(float(width), 8.0)
    height = max(float(height), 8.0)

    # Miro API не принимает borderWidth <= 1.0 (ошибка 2.0703 "must be greater than 1.0").
    # Если вызывающий код хочет "невидимую" рамку (border_width=0), эмулируем её:
    # ставим минимально допустимую ширину и делаем рамку полностью прозрачной.
    if border_width <= 1.0:
        effective_border_width = 2.0
        border_opacity = "0.0"
    else:
        effective_border_width = float(border_width)
        border_opacity = "1.0"

    body = {
        "data": {"content": content, "shape": shape_kind},
        "style": {
            "fillColor": fill_color,
            "fillOpacity": "1.0",
            "borderColor": border_color,
            "borderWidth": str(effective_border_width),
            "borderStyle": "normal",
            "borderOpacity": border_opacity,
            "color": "#1A1A1A",
            "fontFamily": "open_sans",
            "fontSize": "14",
            "textAlign": text_align,
            "textAlignVertical": text_align_vertical,
        },
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width, "height": height},
    }
    if parent_id:
        body["parent"] = {"id": parent_id}
    return _request("POST", "/shapes", board_id=board_id, json=body)


def update_shape(shape_id: str, *, content: Optional[str] = None,
                 fill_color: Optional[str] = None,
                 border_color: Optional[str] = None,
                 board_id: Optional[str] = None) -> dict:
    """Частичное обновление shape — отправляем только заданные поля."""
    body: dict = {}
    if content is not None:
        body["data"] = {"content": content}
    style: dict = {}
    if fill_color is not None:
        style["fillColor"] = fill_color
        style["fillOpacity"] = "1.0"
    if border_color is not None:
        style["borderColor"] = border_color
    if style:
        body["style"] = style
    if not body:
        return _request("GET", f"/shapes/{shape_id}", board_id=board_id)
    return _request("PATCH", f"/shapes/{shape_id}", board_id=board_id, json=body)


def delete_shape(shape_id: str, board_id: Optional[str] = None) -> None:
    _request("DELETE", f"/shapes/{shape_id}", board_id=board_id)