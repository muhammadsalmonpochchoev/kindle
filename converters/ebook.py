import shutil
import subprocess
from pathlib import Path


class ConverterNotFound(RuntimeError):
    pass


def convert_book(input_path: Path, output_format: str) -> Path:
    """Конвертирует книгу через calibre's ebook-convert.

    Требует, чтобы 'ebook-convert' был доступен в PATH (ставится вместе
    с Calibre — см. README про лёгкие варианты установки).
    """
    if shutil.which("ebook-convert") is None:
        raise ConverterNotFound(
            "ebook-convert не найден в PATH. Установи Calibre "
            "(см. README.md — там же лёгкие варианты установки) "
            "или используй kindlegen для epub/html -> mobi."
        )

    output_path = input_path.with_suffix(f".{output_format}")
    result = subprocess.run(
        ["ebook-convert", str(input_path), str(output_path)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Конвертация не удалась: {result.stderr.strip()}")
    return output_path
