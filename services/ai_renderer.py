import html
import re
import markdown

# Главный фикс: убраны подчёркивания, которые Markdown интерпретировал как жирный текст
_MATH_TOKEN = "KINDLE_MATH_TOKEN_{}"

# Символы, не требующие аргумента — просто замена команды на юникод-глиф.
_SYMBOLS = {
    "cdot": "·", "times": "×", "div": "÷",
    "pm": "±", "mp": "∓", "leq": "≤", "geq": "≥", "le": "≤", "ge": "≥",
    "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "∼", "propto": "∝",
    "infty": "∞", "to": "→", "rightarrow": "→", "leftarrow": "←",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔",
    "circ": "°", "degree": "°", "perp": "⊥", "parallel": "∥", "angle": "∠",
    "in": "∈", "notin": "∉", "subset": "⊂", "cup": "∪", "cap": "∩",
    "forall": "∀", "exists": "∃", "emptyset": "∅",
    "quad": "  ", "qquad": "    ",
    "alpha": "α", "beta": "β", "gamma": "γ", "Gamma": "Γ",
    "delta": "δ", "Delta": "Δ", "epsilon": "ε", "varepsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "Theta": "Θ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "Lambda": "Λ",
    "mu": "μ", "nu": "ν", "xi": "ξ", "Xi": "Ξ",
    "pi": "π", "Pi": "Π", "rho": "ρ", "sigma": "σ", "Sigma": "Σ",
    "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ", "Phi": "Φ",
    "chi": "χ", "psi": "ψ", "Psi": "Ψ", "omega": "ω", "Omega": "Ω",
    "partial": "∂", "nabla": "∇", "sum": "Σ", "int": "∫", "prod": "Π",
}

# Двухсимвольные команды-эскейпы (не буквы после `\`), которые тоже
# нужно уметь заменять — например, "\," (узкий пробел).
_ESCAPES = {
    "\\,": " ", "\\;": " ", "\\ ": " ", "\\{": "{", "\\}": "}",
    "\\%": "%", "\\$": "$", "\\#": "#", "\\&": "&", "\\_": "_",
}

_WRAPPER_CMDS = ("text", "mathrm", "mathbf", "textbf", "operatorname", "mathit")
_TRIVIAL_CMDS = ("left", "right")


def _cmd_at(s: str, i: int, name: str) -> bool:
    """Проверяет, что в позиции i стоит команда \\name, а не префикс более
    длинного имени (например, \\frac не должен сработать на \\fraction)."""
    ln = len(name) + 1  # +1 за обратный слэш
    if s[i : i + ln] != "\\" + name:
        return False
    nxt = s[i + ln : i + ln + 1]
    return not nxt.isalpha()


def _match_group(s: str, i: int):
    """s[i] == '{' — возвращает (содержимое, индекс после закрывающей '}')
    с учётом вложенных фигурных скобок."""
    depth = 0
    j = i
    n = len(s)
    while j < n:
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
        j += 1
    return s[i + 1 :], n  # незакрытая скобка — берём до конца


def _match_atom(s: str, i: int):
    """Аргумент для ^ и _: либо {...}-группа, либо один токен (команда
    или символ), например x^2 или x^\\circ."""
    n = len(s)
    if i >= n:
        return "", i
    if s[i] == "{":
        return _match_group(s, i)
    if s[i] == "\\":
        m = re.match(r"\\[A-Za-z]+", s[i:])
        if m:
            return m.group(0), i + len(m.group(0))
        return s[i : i + 2], min(i + 2, n)
    return s[i], i + 1


def _convert(s: str) -> str:
    """Рекурсивно превращает LaTeX-подобную строку в HTML/юникод.
    Поддерживает произвольную вложенность \\frac, \\sqrt, ^, _."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]

        # \frac{a}{b} — рекурсивно на a и b, так вложенные дроби работают
        if _cmd_at(s, i, "frac"):
            j = i + 5
            while j < n and s[j] == " ":
                j += 1
            if j < n and s[j] == "{":
                num, j2 = _match_group(s, j)
                k = j2
                while k < n and s[k] == " ":
                    k += 1
                if k < n and s[k] == "{":
                    den, k2 = _match_group(s, k)
                    out.append(
                        '<span class="frac"><span class="frac-num">{}</span>'
                        '<span class="frac-den">{}</span></span>'.format(
                            _convert(num), _convert(den)
                        )
                    )
                    i = k2
                    continue
            i += 5
            continue

        # \sqrt{a} и \sqrt[n]{a}
        if _cmd_at(s, i, "sqrt"):
            j = i + 5
            index_html = ""
            if j < n and s[j] == "[":
                end = s.find("]", j)
                if end != -1:
                    index_html = _convert(s[j + 1 : end])
                    j = end + 1
            while j < n and s[j] == " ":
                j += 1
            if j < n and s[j] == "{":
                body, j2 = _match_group(s, j)
                idx_span = (
                    '<sup class="sqrt-idx">{}</sup>'.format(index_html)
                    if index_html
                    else ""
                )
                out.append(
                    '<span class="sqrt">{}<span class="sqrt-sign">√</span>'
                    '<span class="sqrt-body">{}</span></span>'.format(
                        idx_span, _convert(body)
                    )
                )
                i = j2
                continue
            out.append("√")
            i = j
            continue

        # x^{...} / x^2 — степень (рекурсивно, чтобы дробь тоже могла
        # оказаться в показателе степени)
        if ch == "^":
            atom, j = _match_atom(s, i + 1)
            out.append("<sup>{}</sup>".format(_convert(atom)))
            i = j
            continue

        # x_{...} / x_2 — индекс
        if ch == "_":
            atom, j = _match_atom(s, i + 1)
            out.append("<sub>{}</sub>".format(_convert(atom)))
            i = j
            continue

        # \text{...}, \mathrm{...} и т.п. — просто содержимое без обёртки
        wrapped = False
        for cmd in _WRAPPER_CMDS:
            if _cmd_at(s, i, cmd):
                j = i + len(cmd) + 1
                while j < n and s[j] == " ":
                    j += 1
                if j < n and s[j] == "{":
                    body, j2 = _match_group(s, j)
                    out.append(_convert(body))
                    i = j2
                    wrapped = True
                break
        if wrapped:
            continue

        # \left / \right — убираем саму команду, разделитель после неё
        # (скобка и т.п.) обработается как обычный символ на следующем шаге
        trivial = False
        for cmd in _TRIVIAL_CMDS:
            if _cmd_at(s, i, cmd):
                i += len(cmd) + 1
                trivial = True
                break
        if trivial:
            continue

        # Обычная команда \something — символ из таблицы либо голое имя
        if ch == "\\":
            m = re.match(r"\\[A-Za-z]+", s[i:])
            if m:
                name = m.group(0)[1:]
                out.append(_SYMBOLS.get(name, name))
                i += len(m.group(0))
                continue
            two = s[i : i + 2]
            if two in _ESCAPES:
                out.append(_ESCAPES[two])
                i += 2
                continue
            i += 1  # одинокий "\" — отбрасываем
            continue

        # Скобки группировки, которые не были поглощены выше (например,
        # осиротевшая "}") — просто убираем, это не видимый символ.
        if ch in "{}":
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _protect_math(text: str):
    blocks = []

    # Блочная математика: $$...$$ и \[...\]
    pattern_display = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)

    def repl_display(match):
        raw = match.group(1) if match.group(1) is not None else match.group(2)
        idx = len(blocks)
        blocks.append(
            '<div class="math math-display">{}</div>'.format(
                _convert(html.escape(raw, quote=False).strip())
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
                _convert(html.escape(raw, quote=False).strip())
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
