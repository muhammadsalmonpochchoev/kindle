// app-kindle.js — ES5 для Kindle Paperwhite 1 (AppleWebKit/534.26+)
// Критично: нет let/const, стрелок, fetch, Promise. Только var и function.
// Формы работают через обычную отправку (не AJAX) — это надёжнее старого движка.

function $(id) {
    return document.getElementById(id);
}

// --- Библиотека: фильтр книг ---
function filterBooks() {
    var input = $("book-filter");
    if (!input) return;
    var filter = input.value.toLowerCase();
    var list = $("book-list");
    if (!list) return;
    var items = list.getElementsByTagName("li");

    for (var i = 0; i < items.length; i++) {
        var title = items[i].getElementsByClassName("book-title")[0];
        if (title) {
            var text = title.textContent || title.innerText || "";
            items[i].style.display = text.toLowerCase().indexOf(filter) > -1 ? "" : "none";
        }
    }
}

// --- AI чат: очистка истории через сервер ---
function clearAiHistory() {
    var form = document.createElement("form");
    form.method = "post";
    form.action = "/ai/clear" + window.location.search;
    document.body.appendChild(form);
    form.submit();
}

// --- Прокси: заполняем datalist недавних URL из localStorage ---
function initProxy() {
    var input = $("proxy-url");
    var datalist = $("recent-urls");
    if (!input || !datalist) return;

    try {
        var urls = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
        var html = "";
        for (var i = 0; i < urls.length && i < 10; i++) {
            html += '<option value="' + urls[i].replace(/"/g, "&quot;") + '">';
        }
        datalist.innerHTML = html;
    } catch (e) {}

    var form = $("proxy-form");
    if (form) {
        form.onsubmit = function() {
            try {
                var val = input.value.replace(/^\s+|\s+$/g, "");
                if (!val) return true;
                var urls = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
                var idx = -1;
                for (var j = 0; j < urls.length; j++) {
                    if (urls[j] === val) { idx = j; break; }
                }
                if (idx > -1) urls.splice(idx, 1);
                urls.unshift(val);
                if (urls.length > 10) urls = urls.slice(0, 10);
                localStorage.setItem("proxy_urls", JSON.stringify(urls));
            } catch (e) {}
            return true;
        };
    }
}

// --- Инициализация ---
function initPage() {
    initProxy();
}

if (document.addEventListener) {
    document.addEventListener("DOMContentLoaded", initPage);
} else if (window.attachEvent) {
    window.attachEvent("onload", initPage);
} else {
    window.onload = initPage;
}