from dotenv import load_dotenv

# ВАЖНО: .env должен подгрузиться ДО импорта роутеров ниже — они читают
# переменные окружения (OPENROUTER_API_KEY, лимиты и т.д.) на уровне
# модуля, то есть в момент импорта. Если поменять порядок строк —
# .env перестанет реально на что-либо влиять.
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from routers import books, ai, proxy

app = FastAPI(title="Kindle Server")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(books.router)
app.include_router(ai.router)
app.include_router(proxy.router)


@app.get("/")
def home():
    """Корень сайта ведёт сразу на дашборд — удобнее для Kindle-браузера."""
    return RedirectResponse(url="/dashboard")


@app.get("/status")
def status():
    """Машиночитаемый статус — для скриптов/проверок."""
    return {"service": "Kindle Server", "status": "ok"}