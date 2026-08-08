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
