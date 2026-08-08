from typing import Optional
import html

from fastapi import Request

NAV_LINKS = [
    ("/dashboard", "Дашборд"),
    ("/library", "Библиотека"),
    ("/ai/", "AI чат"),
    ("/proxy/", "Прокси"),
]

_STATUS_ICONS = {"info": "ℹ", "success": "✓", "error": "⚠"}


def render_status(msg: Optional[str], kind: str = "info") -> str:
    """Единая вёрстка для статусных сообщений (успех/ошибка/инфо) —
    используется и на сервере (SSR), и как формат ответа для AJAX-JS.
    kind: 'info' | 'success' | 'error'."""
    if not msg:
        return ""
    icon = _STATUS_ICONS.get(kind, _STATUS_ICONS["info"])
    return (
        f'<p class="status status-{kind}">'
        f'<span class="status-icon">{icon}</span> {html.escape(msg)}'
        f"</p>"
    )


def render_page(title: str, body: str, active: str = "", request: Optional[Request] = None) -> str:
    is_https = bool(request and request.url.scheme == "https")
    css_file = "style-modern.css" if is_https else "style.css"
    body_class = "modern" if is_https else "plain"
    js_file = "app.js" if is_https else "app-kindle.js"

    nav_items = []
    for href, label in NAV_LINKS:
        cls = ' class="active"' if href == active else ""
        nav_items.append(f'<a href="{href}"{cls}>{html.escape(label)}</a>')
    nav = "".join(nav_items)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/static/{css_file}">
</head>
<body class="{body_class}">
<nav>{nav}</nav>
<h1>{html.escape(title)}</h1>
{body}
<script src="/static/app-common.js"></script>
<script src="/static/{js_file}"></script>
</body>
</html>"""