import html
import re
import markdown

# Главный фикс: убраны подчёркивания, которые Markdown интерпретировал как жирный текст
_MATH_TOKEN = "KINDLE_MATH_TOKEN_{}"


def _latex_to_readable(value: str) -> str:
    """Превращает LaTeX в читаемый HTML/Unicode для старого WebKit."""
    value = value.strip()

    # Текстовые команды
    value = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\mathrm\s*\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\mathbf\s*\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\textbf\s*\{([^{}]*)\}", r"\1", value)

    # Символы
    symbols = {
        r"\cdot": "·", r"\times": "×", r"\div": "÷",
        r"\pm": "±", r"\mp": "∓", r"\leq": "≤", r"\geq": "≥",
        r"\neq": "≠", r"\approx": "≈", r"\equiv": "≡",
        r"\infty": "∞", r"\to": "→", r"\rightarrow": "→",
        r"\left": "", r"\right": "", r"\,": " ",
        r"\quad": "  ", r"\qquad": "    ",
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
        r"\delta": "δ", r"\theta": "θ", r"\lambda": "λ",
        r"\mu": "μ", r"\pi": "π", r"\sigma": "σ",
        r"\phi": "φ", r"\omega": "ω",
        r"\sum": "Σ", r"\int": "∫", r"\sqrt": "√",
        r"\partial": "∂", r"\nabla": "∇",
    }
    for old, new in symbols.items():
        value = value.replace(old, new)

    # Дроби
    value = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", value)

    # Степени и индексы
    value = re.sub(r"\^\{([^{}]+)\}", r"<sup>\1</sup>", value)
    value = re.sub(r"_\{([^{}]+)\}", r"<sub>\1</sub>", value)
    value = re.sub(r"\^([A-Za-z0-9+\-])", r"<sup>\1</sup>", value)
    value = re.sub(r"_([A-Za-z0-9+\-])", r"<sub>\1</sub>", value)

    # Оставшиеся команды — убираем обратный слэш
    value = re.sub(r"\\([A-Za-z]+)", r"\1", value)

    # Чистим лишние скобки
    value = value.replace("{", "").replace("}", "")
    return value


def _protect_math(text: str):
    blocks = []

    # Блочная математика: $$...$$ и \[...\]
    pattern_display = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)

    def repl_display(match):
        raw = match.group(1) if match.group(1) is not None else match.group(2)
        idx = len(blocks)
        blocks.append(
            '<div class="math math-display">{}</div>'.format(
                _latex_to_readable(html.escape(raw, quote=False))
            )
        )
        return _MATH_TOKEN.format(idx)

    text = pattern_display.sub(repl_display, text)

    # Строчная математика: $...$ и \(...\)
    # Negative lookbehind/lookahead чтобы не словить "$5" как валюту
    pattern_inline = re.compile(r"(?<!\$)\$([^\n$]+?)\$(?!\$)|\\\((.+?)\\\)", re.S)

    def repl_inline(match):
        raw = match.group(1) if match.group(1) is not None else match.group(2)
        idx = len(blocks)
        blocks.append(
            '<span class="math math-inline">{}</span>'.format(
                _latex_to_readable(html.escape(raw, quote=False))
            )
        )
        return _MATH_TOKEN.format(idx)

    text = pattern_inline.sub(repl_inline, text)
    return text, blocks


def render_ai_answer(text: str) -> str:
    """Безопасно рендерит Markdown + таблицы + математику на сервере."""
    # Экранируем HTML-инъекции от AI
    safe_text = html.escape(text or "", quote=False)
    safe_text, math_blocks = _protect_math(safe_text)

    # Markdown: таблицы, код, списки
    rendered = markdown.markdown(
        safe_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )

    # Вставляем заранее отрендеренную математику обратно
    for idx, block in enumerate(math_blocks):
        rendered = rendered.replace(_MATH_TOKEN.format(idx), block)

    return rendered