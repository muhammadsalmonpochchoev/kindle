from typing import Optional
import html
import os

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from templates import render_page, render_status
from services.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/proxy", tags=["proxy"])

PROXY_RATE_LIMIT_PER_MINUTE = int(os.environ.get("PROXY_RATE_LIMIT_PER_MINUTE", "20"))
_proxy_limiter = SlidingWindowLimiter(PROXY_RATE_LIMIT_PER_MINUTE, window_seconds=60)

ALLOWED_TAGS = {"p", "h1", "h2", "h3", "h4", "a", "ul", "ol", "li", "br", "b", "i", "strong", "em"}

FORM = """
<form method="get" action="/proxy/" id="proxy-form">
  <input type="text" name="url" id="proxy-url" list="recent-urls"
         placeholder="https://example.com" value="{value}">
  <datalist id="recent-urls"></datalist>
  <input type="submit" value="Открыть">
  <span id="proxy-status" class="status"></span>
</form>
"""


@router.get("/", response_class=HTMLResponse)
async def proxy_page(request: Request, url: Optional[str] = Query(default=None)):
    if not url:
        return HTMLResponse(render_page("Прокси-браузер", FORM.format(value=""), active="/proxy/", request=request))

    if not _proxy_limiter.allow():
        body = FORM.format(value=url) + render_status(
            f"Слишком много запросов подряд — лимит "
            f"{PROXY_RATE_LIMIT_PER_MINUTE} в минуту. Подожди немного.",
            "error",
        )
        return HTMLResponse(render_page("Прокси-браузер", body, active="/proxy/", request=request))

    fetch_url = url if url.startswith(("http://", "https://")) else f"https://{url}"

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
    except Exception as e:
        body = FORM.format(value=url) + render_status(f"Ошибка загрузки: {e}", "error")
        return HTMLResponse(render_page("Прокси-браузер", body, active="/proxy/", request=request))

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "svg", "noscript", "iframe", "form", "img"]):
        tag.decompose()

    page_title = soup.title.string if soup.title else fetch_url
    content = soup.body or soup

    for tag in list(content.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()

    plain_text = content.get_text("\n", strip=True)

    save_form = f"""
    <form method="post" action="/save-article">
      <input type="hidden" name="title" value="{html.escape(str(page_title))}">
      <textarea name="content" style="display:none">{html.escape(plain_text)}</textarea>
      <input type="submit" value="Сохранить в библиотеку (прочитать позже)">
    </form>
    """

    body = (
        FORM.format(value=url)
        + f'<div class="proxy-content"><h2>{page_title}</h2>{save_form}{content}</div>'
    )
    return HTMLResponse(render_page("Прокси-браузер", body, active="/proxy/", request=request))
