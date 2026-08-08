// app.js — Modern JS для телефона/ноутбука (HTTPS, современный движок)

document.addEventListener("DOMContentLoaded", function() {
    // Прокси: недавние URL в datalist
    var proxyInput = document.getElementById("proxy-url");
    var proxyDatalist = document.getElementById("recent-urls");
    if (proxyInput && proxyDatalist) {
        try {
            var urls = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
            proxyDatalist.innerHTML = urls.slice(0, 10).map(function(u) {
                return '<option value="' + u.replace(/"/g, "&quot;") + '">';
            }).join("");
        } catch (e) {}

        var proxyForm = document.getElementById("proxy-form");
        if (proxyForm) {
            proxyForm.addEventListener("submit", function() {
                var val = proxyInput.value.trim();
                if (!val) return;
                var urls = JSON.parse(localStorage.getItem("proxy_urls") || "[]");
                urls = urls.filter(function(u) { return u !== val; });
                urls.unshift(val);
                localStorage.setItem("proxy_urls", JSON.stringify(urls.slice(0, 10)));
            });
        }
    }
});