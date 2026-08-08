from typing import Optional

from fastapi import Request

NAV_LINKS = [
    ("/dashboard", "Дашборд"),
    ("/library", "Библиотека"),
    ("/ai/", "AI чат"),
    ("/proxy/", "Прокси"),
]


def render_page(title: str, body: str, active: str = "", request: Optional[Request] = None) -> str:
    """HTML-структура одна на оба дизайна — меняется только CSS-файл
    в зависимости от того, как реально пришёл запрос (HTTP или HTTPS).
    request.url.scheme выставляется самим uvicorn на основе того, было
    ли соединение через TLS — подделать его снаружи запросом нельзя."""
    is_https = bool(request and request.url.scheme == "https")
    css_file = "style-modern.css" if is_https else "style.css"
    body_class = "modern" if is_https else "plain"

    nav_items = []
    for href, label in NAV_LINKS:
        cls = ' class="active"' if href == active else ""
        nav_items.append(f'<a href="{href}"{cls}>{label}</a>')
    nav = "".join(nav_items)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/static/{css_file}">
</head>
<body class="{body_class}">
<nav>{nav}</nav>
<h1>{title}</h1>
{body}
<script src="/static/app.js"></script>
</body>
</html>"""
