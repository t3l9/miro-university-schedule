"""
Точка входа. Запуск:  python run.py

Альтернативно из CLI:  uvicorn app.api:app --reload --port 5000
"""
import uvicorn

from app.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG


def main():
    print(f"\n  Swagger UI:  http://localhost:{FLASK_PORT}/docs")
    print(f"  ReDoc:       http://localhost:{FLASK_PORT}/redoc")
    print(f"  OpenAPI:     http://localhost:{FLASK_PORT}/openapi.json\n")
    uvicorn.run(
        "app.api:app",
        host=FLASK_HOST,
        port=FLASK_PORT,
        reload=FLASK_DEBUG,
    )


if __name__ == "__main__":
    main()
