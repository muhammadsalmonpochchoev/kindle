import html
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse

from templates import render_page
from subjects import SUBJECTS
from services.rate_limit import SlidingWindowLimiter
from services.ai_renderer import render_ai_answer

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")

AI_RATE_LIMIT_PER_MINUTE = int(os.environ.get("AI_RATE_LIMIT_PER_MINUTE", "10"))
AI_MAX_MESSAGE_CHARS = int(os.environ.get("AI_MAX_MESSAGE_CHARS", "4000"))
_ai_limiter = SlidingWindowLimiter(AI_RATE_LIMIT_PER_MINUTE, window_seconds=60)

# Серверная история: надёжнее localStorage на экспериментальном браузере Kindle
HISTORY_FILE = Path("data/ai_history.json")
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
MAX_HISTORY = 30


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history_entry(q: str, a: str, a_html: str, subject: Optional[str] = None):
    history = load_history()
    entry = {
        "q": q,
        "a": a,
        "a_html": a_html,
        "subject": subject,
        "time": int(time.time()),
    }
    history.append(entry)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except IOError:
        pass


def clear_history():
    try:
        HISTORY_FILE.write_text("[]", encoding="utf-8")
    except IOError:
        pass


def render_history_html(history: list, limit: int = 20) -> str:
    """Рендерит историю диалога. Новые сообщения — сверху."""
    items = history[-limit:]
    items.reverse()
    parts = []
    for item in items:
        q = html.escape(item.get("q", ""))
        a = item.get("a_html", html.escape(item.get("a", "")))
        subj = item.get("subject")
        subj_label = ""
        if subj and subj in SUBJECTS:
            subj_label = (
                f'<span class="subject-tag">{html.escape(SUBJECTS[subj]["label"])}</span>'
            )
        parts.append(
            f'<div class="exchange">'
            f'<div class="question">{subj_label}{q}</div>'
            f'<div class="answer">{a}</div>'
            f'</div>'
        )
    return "\n".join(parts) if parts else '<p class="status">История пуста. Задай вопрос ниже.</p>'


def render_chat_page(
    request: Request,
    subject: Optional[str] = None,
    status_msg: Optional[str] = None,
) -> str:
    subject_info = SUBJECTS.get(subject)
    placeholder = (
        subject_info["placeholder"] if subject_info else "Задай вопрос..."
    )
    subject_label = (
        f'<p class="status">Режим: {html.escape(subject_info["label"])} — '
        f'<a href="/ai/">выйти в общий чат</a></p>'
        if subject_info
        else ""
    )
    subject_field = (
        f'<input type="hidden" name="subject" value="{html.escape(subject)}">'
        if subject
        else ""
    )

    history = load_history()
    history_html = render_history_html(history)

    status_banner = (
        f'<p class="status">{html.escape(status_msg)}</p>' if status_msg else ""
    )

    body = f"""
    {subject_label}
    {status_banner}
    <div id="ai-history">
        {history_html}
    </div>
    <form method="post" action="/ai/chat" id="ai-form">
      {subject_field}
      <textarea name="message" rows="5" maxlength="{AI_MAX_MESSAGE_CHARS}"
        placeholder="{html.escape(placeholder)}"></textarea>
      <input type="submit" value="Отправить">
      <span id="ai-status" class="status"></span>
    </form>
    <button type="button" onclick="clearAiHistory()">Очистить историю</button>
    """
    return render_page("AI чат", body, active="/ai/", request=request)


@router.get("/", response_class=HTMLResponse)
def chat_page(request: Request, subject: Optional[str] = Query(default=None)):
    return HTMLResponse(render_chat_page(request, subject=subject))


@router.post("/chat", response_class=HTMLResponse)
async def chat(
    request: Request,
    message: str = Form(...),
    subject: Optional[str] = Form(default=None),
):
    subject_info = SUBJECTS.get(subject)
    status_msg = None
    answer = None
    answer_html = None

    if len(message) > AI_MAX_MESSAGE_CHARS:
        status_msg = (
            f"Сообщение слишком длинное ({len(message)} символов, "
            f"лимит {AI_MAX_MESSAGE_CHARS}). Сократи и отправь ещё раз."
        )
    elif not OPENROUTER_API_KEY:
        status_msg = "Ошибка: не задана переменная окружения OPENROUTER_API_KEY."
    elif not _ai_limiter.allow():
        status_msg = (
            f"Слишком много запросов подряд — лимит {AI_RATE_LIMIT_PER_MINUTE} "
            f"в минуту. Подожди немного и попробуй снова."
        )
    else:
        messages = []
        if subject_info:
            messages.append({"role": "system", "content": subject_info["system"]})
        messages.append({"role": "user", "content": message})

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                    json={"model": MODEL, "messages": messages},
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["choices"][0]["message"]["content"]
                answer_html = render_ai_answer(answer)
        except Exception as e:
            status_msg = f"Ошибка запроса к OpenRouter: {e}"

    if answer is not None:
        save_history_entry(
            q=message,
            a=answer,
            a_html=answer_html or html.escape(answer),
            subject=subject,
        )

    return HTMLResponse(
        render_chat_page(request, subject=subject, status_msg=status_msg)
    )


@router.post("/clear", response_class=HTMLResponse)
def clear_ai_history(
    request: Request,
    subject: Optional[str] = Query(default=None),
):
    clear_history()
    return HTMLResponse(
        render_chat_page(request, subject=subject, status_msg="История очищена.")
    )