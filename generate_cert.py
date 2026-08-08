"""
Генерирует самоподписанный TLS-сертификат для локального HTTPS.

Работает одинаково на Windows/Linux/macOS — не зависит от того, стоит
ли в системе команда openssl (на Windows её по умолчанию нет, если не
использовать Git Bash). Вся генерация — средствами пакета `cryptography`.

Запуск:
    python generate_cert.py
"""

import datetime
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CERT_FILE = Path(os.environ.get("KINDLE_TLS_CERT", "certs/cert.pem"))
KEY_FILE = Path(os.environ.get("KINDLE_TLS_KEY", "certs/key.pem"))


def generate():
    CERT_FILE.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    KEY_FILE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Сертификат: {CERT_FILE.resolve()}")
    print(f"Ключ:       {KEY_FILE.resolve()}")
    print("Готово. Действителен 365 дней, для localhost и 127.0.0.1.")


if __name__ == "__main__":
    generate()