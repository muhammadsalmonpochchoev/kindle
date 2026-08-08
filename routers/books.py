from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pathlib import Path
from urllib.parse import quote
import os
import re
import shutil
from typing import Optional

from converters.ebook import convert_book, ConverterNotFound
from templates import render_page
from subjects import SUBJECTS

router = APIRouter(prefix="", tags=["books"])

BOOKS = (Path(__file__).parent.parent / "books").resolve()
BOOKS.mkdir(exist_ok=True)


MEDIA_TYPES = {
    ".mobi": "application/x-mobipocket-ebook",
    ".prc": "application/x-mobipocket-ebook",
    ".azw": "application/vnd.amazon.ebook",
    ".azw3": "application/vnd.amazon.ebook",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".epub": "application/epub+zip",
}

# Форматы, которые PW1 умеет открывать нативно, без стороннего софта.
# PRC сюда не входит как ЦЕЛЬ конвертации — calibre умеет PRC только
# читать, но не создавать; если у тебя уже есть готовый .prc, его можно
# просто скачать как есть. Обычный AZW (без "3") тоже не выходной формат
# calibre — только AZW3 (KF8), который PW1 частично поддерживает.
KINDLE_NATIVE_FORMATS = ["mobi", "azw3", "txt"]

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def safe_book_path(filename: str) -> Path:
    """Защита от path traversal: резолвим путь и проверяем,
    что он реально лежит внутри BOOKS."""
    candidate = (BOOKS / filename).resolve()
    if BOOKS not in candidate.parents and candidate != BOOKS:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Book not found")
    return candidate


@router.get("/books")
def books_json():
    """JSON-версия — для телефона/скриптов."""
    files = sorted(f.name for f in BOOKS.iterdir() if f.is_file())
    return {"books": files}


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """Общий обзор системы — точка входа вместо разрозненных страниц."""
    files = sorted(
        (f for f in BOOKS.iterdir() if f.is_file()),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    last_book = files[0].name if files else "пока пусто"
    calibre_ok = shutil.which("ebook-convert") is not None
    ai_ok = bool(os.environ.get("OPENROUTER_API_KEY"))

    def status_line(label, ok, ok_text, bad_text):
        mark = "✔" if ok else "✘"
        return f"<li>{mark} {label}: {ok_text if ok else bad_text}</li>"

    subject_buttons = "".join(
        f'<a class="subject-btn" href="/ai/?subject={sid}">{s["label"]}</a>'
        for sid, s in SUBJECTS.items()
    )

    body = f"""
    <ul>
      <li>Книг в библиотеке: {len(files)}</li>
      <li>Последняя добавленная: {last_book}</li>
      {status_line("Calibre", calibre_ok, "найден, конвертация доступна", "не найден — /convert будет выдавать ошибку")}
      {status_line("AI-ключ", ai_ok, "задан, чат работает", "не задан OPENROUTER_API_KEY — чат будет отвечать ошибкой")}
    </ul>
    <h2>Предметы</h2>
    <div class="subject-grid">{subject_buttons}</div>
    <h2>Разделы</h2>
    <p>
      <a href="/library">Библиотека</a> ·
      <a href="/ai/">AI чат (общий)</a> ·
      <a href="/proxy/">Прокси-браузер</a>
    </p>
    """
    return HTMLResponse(render_page("Kindle Workspace", body, active="/dashboard", request=request))


@router.get("/library", response_class=HTMLResponse)
def library_page(request: Request, msg: Optional[str] = Query(default=None)):
    """HTML-версия — то, что реально открывает Kindle-браузер."""
    files = sorted(f.name for f in BOOKS.iterdir() if f.is_file())
    items = "".join(
        f'<li class="book-item">'
        f'<span class="book-title">{f}</span>'
        f'<div class="book-actions">'
        f'<a href="/download/{f}">Скачать как есть</a>'
        + "".join(
            f'<a href="/convert/{f}?to={fmt}">→ {fmt}</a>'
            for fmt in KINDLE_NATIVE_FORMATS
            if not f.lower().endswith(f".{fmt}")
        )
        + '</div></li>'
        for f in files
    )
    banner = f'<p class="status">{msg}</p>' if msg else ""
    body = f"""
    {banner}
    <input type="text" id="book-filter" placeholder="Поиск по названию..." onkeyup="filterBooks()">
    <ul class="book-list" id="book-list">{items or "<li>Пока пусто</li>"}</ul>
    <h2>Загрузить книгу</h2>
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Загрузить">
      <span class="status">(лимит {MAX_UPLOAD_MB} МБ)</span>
    </form>
    """
    return HTMLResponse(render_page("Моя библиотека", body, active="/library", request=request))


@router.get("/download/{filename}")
def download(filename: str):
    file = safe_book_path(filename)
    media_type = MEDIA_TYPES.get(file.suffix.lower(), "application/octet-stream")
    return FileResponse(file, filename=file.name, media_type=media_type)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Загрузка книги — например, с телефона. Пишем стримом с проверкой
    размера на лету, чтобы не читать гигантский файл целиком в память
    и не забить диск одной случайной загрузкой."""
    dest = (BOOKS / file.filename).resolve()
    if BOOKS not in dest.parents:
        raise HTTPException(status_code=400, detail="Invalid filename")

    size = 0
    chunk_size = 1024 * 1024  # 1 МБ
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    f.close()
                    dest.unlink(missing_ok=True)
                    msg = quote(f"Файл слишком большой (лимит {MAX_UPLOAD_MB} МБ)")
                    return RedirectResponse(url=f"/library?msg={msg}", status_code=303)
                f.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    return RedirectResponse(url="/library", status_code=303)


@router.get("/convert/{filename}")
def convert(filename: str, to: str = Query("mobi")):
    src = safe_book_path(filename)
    try:
        convert_book(src, to)
    except (ConverterNotFound, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    return RedirectResponse(url="/library", status_code=303)


def slugify_filename(title: str) -> str:
    """Превращает заголовок статьи в безопасное имя файла."""
    name = re.sub(r"[^\w\-. а-яА-ЯёЁ]", "_", title).strip()
    return (name or "article")[:80]


@router.post("/save-article")
async def save_article(title: str = Form(...), content: str = Form(...)):
    """Сохраняет статью из прокси как .txt-книгу в библиотеке ('прочитать позже')."""
    filename = slugify_filename(title) + ".txt"
    dest = (BOOKS / filename).resolve()
    if BOOKS not in dest.parents:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # если файл с таким именем уже есть — не затираем, добавляем счётчик
    counter = 1
    base = dest
    while dest.exists():
        dest = base.with_name(f"{base.stem}_{counter}{base.suffix}")
        counter += 1

    dest.write_text(f"{title}\n\n{content}", encoding="utf-8")
    return RedirectResponse(url="/library?msg=Статья+сохранена+в+библиотеку", status_code=303)
