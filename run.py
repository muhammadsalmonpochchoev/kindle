"""
Поднимает два листенера в одном процессе на общем asyncio-луп:
- HTTP на HTTP_PORT   -> Kindle получает простой e-ink дизайн
- HTTPS на HTTPS_PORT -> телефон/ноутбук получают современный дизайн

Один uvicorn.Server слушает либо HTTP, либо HTTPS — не оба сразу на
одном порту, поэтому портов два. request.url.scheme определяется
uvicorn автоматически по тому, было соединение через TLS или нет —
подделать это заголовком снаружи нельзя.

Если сертификат не найден, сервер просто не поднимает HTTPS и работает
только по HTTP (ничего не падает).
"""

import asyncio
import os

import uvicorn

from main import app

HTTP_PORT = int(os.environ.get("HTTP_PORT", "8000"))
HTTPS_PORT = int(os.environ.get("HTTPS_PORT", "8443"))
# Специально НЕ называем это SSL_CERT_FILE/SSL_KEY_FILE — это широко
# используемые системные переменные (Python/pip/requests берут из
# SSL_CERT_FILE путь к доверенному CA-бандлу для проверки чужих
# сертификатов). Если бы мы использовали то же имя для своего
# сертификата сервера, на системах, где SSL_CERT_FILE уже выставлена
# (нередко на Fedora и других дистрибутивах), наш сервер получил бы
# системный CA-бандл вместо собственного certs/cert.pem и упал бы
# с ошибкой несовпадения ключа и сертификата.
CERT_FILE = os.environ.get("KINDLE_TLS_CERT", "certs/cert.pem")
KEY_FILE = os.environ.get("KINDLE_TLS_KEY", "certs/key.pem")


async def main():
    servers = []

    http_config = uvicorn.Config(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")
    servers.append(uvicorn.Server(http_config))
    print(f"HTTP  (e-ink дизайн, для Kindle):     http://0.0.0.0:{HTTP_PORT}")

    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        https_config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=HTTPS_PORT,
            ssl_certfile=CERT_FILE,
            ssl_keyfile=KEY_FILE,
            log_level="info",
        )
        servers.append(uvicorn.Server(https_config))
        print(f"HTTPS (современный дизайн, для телефона/ПК): https://0.0.0.0:{HTTPS_PORT}")
    else:
        print(
            f"Сертификат не найден ({CERT_FILE} / {KEY_FILE}) — HTTPS не запущен. "
            "Сгенерируй его командой из README, чтобы включить современный дизайн."
        )

    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    asyncio.run(main())
