import html
import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse

from templates import render_page
from subjects import SUBJECTS
from services.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/ai", tags=["ai"])

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")

AI_RATE_LIMIT_PER_MINUTE = int(os.environ.get("AI_RATE_LIMIT_PER_MINUTE", "10"))
AI_MAX_MESSAGE_CHARS = int(os.environ.get("AI_MAX_MESSAGE_CHARS", "4000"))
_ai_limiter = SlidingWindowLimiter(AI_RATE_LIMIT_PER_MINUTE, window_seconds=60)


def json_script(data) -> str:
    """Безопасно сериализует данные для вставки в <script type="application/json">."""
    raw = json.dumps(data, ensure_ascii=False)
    return raw.replace("</", "<\\/")


def render_chat_page(request: Request, subject: Optional[str] = None, latest: Optional[dict] = None) -> str:
    subject_info = SUBJECTS.get(subject)
    placeholder = subject_info["placeholder"] if subject_info else "Задай вопрос..."
    subject_label = (
        f'<p class="status">Режим: {subject_info["label"]} — '
        f'<a href="/ai/">выйти в общий чат</a></p>'
        if subject_info
        else ""
    )
    subject_field = f'<input type="hidden" name="subject" value="{subject}">' if subject_info else ""

    latest_block = (
        f'<script id="latest-exchange" type="application/json">{json_script(latest)}</script>'
        if latest
        else ""
    )
    body = f"""
    {subject_label}
    <div id="ai-history"></div>
    {latest_block}
    <form method="post" action="/ai/chat" onsubmit="return onAiSubmit()" id="ai-form">
      {subject_field}
      <textarea name="message" rows="5" maxlength="{AI_MAX_MESSAGE_CHARS}" placeholder="{placeholder}"></textarea>
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
async def chat(request: Request, message: str = Form(...), subject: Optional[str] = Form(default=None)):
    subject_info = SUBJECTS.get(subject)

    if len(message) > AI_MAX_MESSAGE_CHARS:
        answer = (
            f"Сообщение слишком длинное ({len(message)} символов, "
            f"лимит {AI_MAX_MESSAGE_CHARS}). Сократи и отправь ещё раз."
        )
    elif not OPENROUTER_API_KEY:
        answer = "Ошибка: не задана переменная окружения OPENROUTER_API_KEY."
    elif not _ai_limiter.allow():
        answer = (
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
        except Exception as e:
            answer = f"Ошибка запроса к OpenRouter: {e}"

    return HTMLResponse(
        render_chat_page(request, subject=subject, latest={"q": message, "a": answer})
    )
