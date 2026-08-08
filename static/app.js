// Всё написано под старый WebKit Kindle PW1: только var, function(){},
// без стрелочных функций, без fetch/Promise, без шаблонных строк.

function storageGet(key, fallback) {
  try {
    var raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    return fallback;
  }
}

function storageSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    // localStorage может быть недоступен (приватный режим и т.п.) — просто игнорируем
  }
}

function escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ---------- Библиотека: живой поиск по названиям ----------
function filterBooks() {
  var input = document.getElementById('book-filter');
  if (!input) return;
  var filter = input.value.toLowerCase();
  var items = document.getElementsByClassName('book-item');
  for (var i = 0; i < items.length; i++) {
    var titleEl = items[i].getElementsByClassName('book-title')[0];
    var text = titleEl ? titleEl.textContent.toLowerCase() : '';
    items[i].style.display = text.indexOf(filter) !== -1 ? '' : 'none';
  }
}

// ---------- AI-чат: история в localStorage ----------
function renderAiHistory() {
  var list = document.getElementById('ai-history');
  if (!list) return;
  var history = storageGet('ai_history', []);
  var out = '';
  for (var i = 0; i < history.length; i++) {
    out += '<div class="msg"><div class="who">Вы:</div>' + escapeHtml(history[i].q) + '</div>';
    out += '<div class="msg"><div class="who">AI:</div>' + escapeHtml(history[i].a) + '</div>';
  }
  list.innerHTML = out;
}

function saveLatestAiExchange() {
  var dataEl = document.getElementById('latest-exchange');
  if (!dataEl) return;
  try {
    var latest = JSON.parse(dataEl.textContent);
    var history = storageGet('ai_history', []);
    history.push(latest);
    if (history.length > 50) history = history.slice(history.length - 50);
    storageSet('ai_history', history);
  } catch (e) {}
}

function clearAiHistory() {
  try { localStorage.removeItem('ai_history'); } catch (e) {}
  renderAiHistory();
}

function onAiSubmit() {
  var status = document.getElementById('ai-status');
  if (status) status.textContent = 'Думаю...';
  return true;
}

// ---------- Прокси: недавние URL ----------
function initProxyForm() {
  var form = document.getElementById('proxy-form');
  if (!form) return;
  var input = document.getElementById('proxy-url');
  var list = document.getElementById('recent-urls');
  var recent = storageGet('proxy_recent', []);

  if (list) {
    list.innerHTML = '';
    for (var i = 0; i < recent.length; i++) {
      var opt = document.createElement('option');
      opt.value = recent[i];
      list.appendChild(opt);
    }
  }

  form.addEventListener('submit', function () {
    var status = document.getElementById('proxy-status');
    if (status) status.textContent = 'Загрузка страницы...';
    if (input && input.value) {
      var recent2 = storageGet('proxy_recent', []);
      var idx = recent2.indexOf(input.value);
      if (idx !== -1) recent2.splice(idx, 1);
      recent2.unshift(input.value);
      recent2 = recent2.slice(0, 10);
      storageSet('proxy_recent', recent2);
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  filterBooks();
  saveLatestAiExchange();
  renderAiHistory();
  initProxyForm();
});
