// app-common.js — общая логика для Kindle (AppleWebKit/531-534, ES5) и
// современных браузеров. Критично: НИКАКИХ let/const, стрелочных функций,
// шаблонных строк, fetch/Promise, Array.prototype.includes — только var,
// function, XMLHttpRequest и ручные циклы. Если какой-то вызов бросит
// исключение на старом движке, остальная страница не должна сломаться —
// поэтому почти всё обёрнуто в try/catch, а формы и так работают без JS
// (это просто прогрессивное улучшение, не обязательное условие работы).

function $(id) {
    return document.getElementById(id);
}

// ---------- Библиотека: фильтр книг ----------
function filterBooks() {
    var input = $("book-filter");
    var list = $("book-list");
    if (!input || !list) {
        return;
    }
    var filter = input.value.toLowerCase();
    var items = list.getElementsByTagName("li");
    var visible = 0;
    var i, titleEl, text;

    for (i = 0; i < items.length; i++) {
        if (items[i].id === "book-empty-state") {
            continue;
        }
        titleEl = items[i].getElementsByClassName
            ? items[i].getElementsByClassName("book-title")[0]
            : null;
        if (!titleEl) {
            continue;
        }
        text = titleEl.textContent || titleEl.innerText || "";
        if (text.toLowerCase().indexOf(filter) > -1) {
            items[i].style.display = "";
            visible++;
        } else {
            items[i].style.display = "none";
        }
    }

    var empty = $("book-empty-state");
    if (empty) {
        empty.style.display = visible === 0 ? "" : "none";
    }
}

// ---------- Статус-баннер (используется и AI-чатом) ----------
function renderStatus(el, msg, kind) {
    if (!el) {
        return;
    }
    if (!msg) {
        el.innerHTML = "";
        el.className = "";
        return;
    }
    var icons = { info: "\u2139", success: "\u2713", error: "\u26A0" };
    var icon = icons[kind] || icons.info;
    el.innerHTML = '<span class="status-icon">' + icon + "</span> " + msg;
    el.className = "status status-" + (kind || "info");
}

// ---------- AI чат: счётчик символов ----------
function updateCharCount() {
    var ta = $("ai-message");
    var counter = $("ai-charcount");
    if (!ta || !counter) {
        return;
    }
    var max = parseInt(ta.getAttribute("maxlength"), 10);
    var used = ta.value.length;
    counter.innerHTML = used + " / " + max;
    if (max && used > max * 0.9) {
        counter.className = "charcount charcount-warn";
    } else {
        counter.className = "charcount";
    }
}

function setChatLoading(isLoading) {
    var btn = $("ai-submit");
    if (btn) {
        btn.disabled = isLoading;
        btn.value = isLoading ? "Думаю…" : "Отправить";
    }
    var status = $("ai-status");
    if (isLoading) {
        renderStatus(status, "Жду ответ от ИИ…", "loading");
    }
}

// ---------- AI чат: отправка вопроса без перезагрузки страницы ----------
function initAiChat() {
    var form = $("ai-form");
    var textarea = $("ai-message");
    var historyBox = $("ai-history");
    var status = $("ai-status");

    if (textarea) {
        textarea.onkeyup = updateCharCount;
        updateCharCount();
    }

    // Без XMLHttpRequest форма всё равно отправится обычным способом —
    // сервер прекрасно умеет отвечать полной страницей.
    if (!form || !historyBox || !window.XMLHttpRequest) {
        return;
    }

    form.onsubmit = function () {
        var message = textarea ? textarea.value : "";
        if (!message || !/\S/.test(message)) {
            return false;
        }

        var xhr = new XMLHttpRequest();
        try {
            xhr.open("POST", form.action, true);
        } catch (e) {
            return true; // не смогли открыть XHR — пусть форма отправится как обычно
        }
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

        setChatLoading(true);

        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) {
                return;
            }
            setChatLoading(false);

            if (xhr.status < 200 || xhr.status >= 300) {
                renderStatus(status, "Ошибка соединения с сервером. Попробуй ещё раз.", "error");
                return;
            }

            var data;
            try {
                data = JSON.parse(xhr.responseText);
            } catch (e) {
                // сервер ответил не JSON-ом — подстраховка, грузим страницу целиком
                form.submit();
                return;
            }

            historyBox.innerHTML = data.history_html;
            renderStatus(status, data.status_msg, data.status_kind);

            if (data.ok && textarea) {
                textarea.value = "";
                updateCharCount();
            }
        };

        var params = "message=" + encodeURIComponent(message);
        var subjectField = form.elements ? form.elements.namedItem("subject") : null;
        if (subjectField) {
            params += "&subject=" + encodeURIComponent(subjectField.value);
        }

        xhr.send(params);
        return false;
    };
}

// ---------- AI чат: очистка истории ----------
function clearAiHistory() {
    if (window.confirm && !window.confirm("Очистить всю историю чата? Это необратимо.")) {
        return;
    }

    var url = "/ai/clear" + window.location.search;
    var historyBox = $("ai-history");

    if (historyBox && window.XMLHttpRequest) {
        var xhr = new XMLHttpRequest();
        var done = false;
        try {
            xhr.open("POST", url, true);
            xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        } catch (e) {
            done = true;
        }
        if (!done) {
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== 4) {
                    return;
                }
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        historyBox.innerHTML = data.history_html;
                        renderStatus($("ai-status"), data.status_msg, data.status_kind);
                        return;
                    } catch (e) {}
                }
                _submitClearForm(url);
            };
            xhr.send();
            return;
        }
    }

    _submitClearForm(url);
}

function _submitClearForm(url) {
    var form = document.createElement("form");
    form.method = "post";
    form.action = url;
    document.body.appendChild(form);
    form.submit();
}

// ---------- Прокси: недавние URL из localStorage ----------
function initProxy() {
    var input = $("proxy-url");
    var datalist = $("recent-urls");
    if (!input || !datalist) {
        return;
    }

    try {
        var urls = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
        var optionsHtml = "";
        for (var i = 0; i < urls.length && i < 10; i++) {
            optionsHtml += '<option value="' + urls[i].replace(/"/g, "&quot;") + '">';
        }
        datalist.innerHTML = optionsHtml;
    } catch (e) {}

    var form = $("proxy-form");
    if (form) {
        form.onsubmit = function () {
            try {
                var val = input.value.replace(/^\s+|\s+$/g, "");
                if (!val) {
                    return true;
                }
                var urls2 = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
                var idx = -1;
                for (var j = 0; j < urls2.length; j++) {
                    if (urls2[j] === val) {
                        idx = j;
                        break;
                    }
                }
                if (idx > -1) {
                    urls2.splice(idx, 1);
                }
                urls2.unshift(val);
                if (urls2.length > 10) {
                    urls2 = urls2.slice(0, 10);
                }
                localStorage.setItem("proxy_urls", JSON.stringify(urls2));
            } catch (e) {}
            return true;
        };
    }
}

// ---------- Инициализация ----------
function initCommonPage() {
    initProxy();
    initAiChat();
}

if (document.addEventListener) {
    document.addEventListener("DOMContentLoaded", initCommonPage);
} else if (window.attachEvent) {
    window.attachEvent("onload", initCommonPage);
} else {
    window.onload = initCommonPage;
}
