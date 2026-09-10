#!/usr/bin/env python3
"""
Парсер статистики Instagram Reels — версия С КУКАМИ сессии.

Собран из того, что уже работает у заказчика, а не написан заново:
  * извлечение username четырьмя запасными способами — из /root/instagram_parser.py;
  * разбор og:description (лайки, комментарии, автор) — из узлов Code4/Code5 воркфлоу n8n;
  * запрос страницы профиля с куками — из узла HTTP Request3 того же воркфлоу.

ЗАЧЕМ КУКИ. Проверено живьём 10.09.2026 с серверного адреса, двумя замерами:
  * `instagram.com/<username>/reels/` отвечает 302 на `/accounts/login/` — просмотров не видно;
  * страница самого рилса отдаёт 625 КБ пустой оболочки БЕЗ og:description и og:url, причём
    ровно столько же на заведомо несуществующий код.
То есть анонимно не отдаётся уже ничего, и куки нужны для ОБОИХ шагов. Прежний путь «лайки и
комментарии из метатегов без сессии» (узлы Code4/Code5 в n8n) на сегодня мёртв — он писался,
когда метатеги ещё отдавались.

ГДЕ БРАТЬ КУКИ. Браузер → вход в Instagram → DevTools → Application → Cookies. Нужны шесть:
sessionid, csrftoken, ds_user_id, mid, ig_did, rur. Значение csrftoken дублируется заголовком
X-CSRFToken — так делает браузер, и без него Instagram отвечает иначе.

  export IG_COOKIE='sessionid=...; csrftoken=...; ds_user_id=...; mid=...; ig_did=...; rur=...'
  python3 instagram_parser_cookies.py https://www.instagram.com/reel/XXXXXXXXX/

ЦЕНА, НАЗВАННАЯ ВСЛУХ. Куки — это живая сессия аккаунта: Instagram может её ограничить или
заблокировать. Держите под это ОТДЕЛЬНЫЙ аккаунт, а не рабочий. Куки протухают — сервис обязан
показывать их состояние, а не молча отдавать пустые просмотры.
"""
from __future__ import annotations

import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SERVICE_PATHS = {"reel", "reels", "p", "explore", "accounts", "stories"}


def headers(cookie: str | None = None) -> dict[str, str]:
    """Заголовки браузера. csrftoken дублируется в X-CSRFToken — иначе Instagram отвечает иначе."""
    out = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if cookie:
        out["Cookie"] = cookie
        token = re.search(r"csrftoken=([^;]+)", cookie)
        if token:
            out["X-CSRFToken"] = token.group(1)
    return out


def shortcode_of(url: str) -> str | None:
    m = re.search(r"/(?:reel|reels|p)/([^/?#]+)", url)
    return m.group(1) if m else None


def from_og(html: str) -> dict:
    """
    Лайки, комментарии и автора Instagram кладёт в og:description ещё до входа.
    Формат: «1,728 likes, 211 comments - username on ...». Это дешевле разбора вёрстки и
    переживает её перестановки — вёрстка меняется, метатеги живут годами.
    """
    out: dict = {"username": None, "likes_count": None, "comments_count": None, "shortcode": None}
    desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    if desc:
        text = desc.group(1)
        lc = re.search(r"([\d,]+)\s+likes,\s+([\d,]+)\s+comments", text)
        if lc:
            out["likes_count"] = int(lc.group(1).replace(",", ""))
            out["comments_count"] = int(lc.group(2).replace(",", ""))
        who = re.search(r"-\s*([\w.]+)\s+on\s+", text)
        if who:
            out["username"] = who.group(1)
    og_url = re.search(
        r'<meta property="og:url" content="https://www\.instagram\.com/[^/]+/reel/([\w-]+)/"', html
    )
    if og_url:
        out["shortcode"] = og_url.group(1)
    return out


def username_from_page(html: str) -> str | None:
    """Четыре способа подряд — как в исходном парсере: вёрстка меняется, и какой-то из них отказывает."""
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except ValueError:
            continue

        def find(obj):
            if isinstance(obj, dict):
                if isinstance(obj.get("username"), str):
                    return obj["username"]
                for v in obj.values():
                    got = find(v)
                    if got:
                        return got
            elif isinstance(obj, list):
                for x in obj:
                    got = find(x)
                    if got:
                        return got
            return None

        got = find(data)
        if got:
            return got

    for pattern in (
        r'"username"\s*:\s*"([^"]+)"',
        r'"owner"\s*:\s*\{\s*"username"\s*:\s*"([^"]+)"',
        r'instagram\.com/([a-zA-Z0-9._]+)/reel/',
    ):
        for hit in re.findall(pattern, html):
            if hit not in SERVICE_PATHS:
                return hit

    for prop in ("og:url", "al:ios:url", "al:android:url"):
        meta = soup.find("meta", property=prop)
        if meta and meta.get("content"):
            hit = re.search(r"instagram\.com/([^/]+)/", meta["content"])
            if hit and hit.group(1) not in SERVICE_PATHS:
                return hit.group(1)
    return None


def views_from_profile(username: str, shortcode: str, cookie: str) -> tuple[int | None, str | None]:
    """
    Просмотры лежат ТОЛЬКО на странице профиля, а она с сентября 2026 требует входа.
    Возвращаем (просмотры, причина_отказа): пустое значение обязано объяснить себя, иначе
    протухшие куки неотличимы от рилса без просмотров.
    """
    url = f"https://www.instagram.com/{username}/reels/"
    try:
        r = requests.get(url, headers=headers(cookie), timeout=25, allow_redirects=False)
    except requests.RequestException as e:
        return None, f"страница профиля не открылась: {e}"

    if r.status_code in (301, 302) and "accounts/login" in r.headers.get("location", ""):
        return None, "Instagram увёл на вход — куки протухли или их не приняли"
    if r.status_code != 200:
        return None, f"страница профиля ответила {r.status_code}"

    soup = BeautifulSoup(r.text, "html.parser")
    link = soup.find("a", href=re.compile(f"reel/{re.escape(shortcode)}"))
    if not link:
        return None, "рилса нет на первой странице профиля (мог уехать вниз по ленте)"

    block = link.find("div", class_="_aaj_")
    span = block.find("span", class_=re.compile(r"html-span.*x1vvkbs")) if block else None
    if not span:
        return None, "блок просмотров не найден — вёрстка Instagram изменилась"

    raw = span.get_text(strip=True)
    num = re.findall(r"\d+\.?\d*", raw)
    if not num:
        return None, f"не разобрал число просмотров: {raw!r}"
    value = float(num[0])
    if "K" in raw.upper():
        value *= 1_000
    elif "M" in raw.upper():
        value *= 1_000_000
    return int(value), None


def parse(url: str, cookie: str | None) -> dict:
    code = shortcode_of(url)
    if not code:
        return {"error": "в ссылке нет кода рилса"}

    if not cookie:
        return {
            "shortcode": code,
            "error": "нужны куки: с сентября 2026 Instagram не отдаёт данные рилса анонимно",
        }

    try:
        page = requests.get(url, headers=headers(cookie), timeout=25)
        page.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"страница рилса не открылась: {e}"}

    out = from_og(page.text)
    out["shortcode"] = out.get("shortcode") or code
    out["username"] = out.get("username") or username_from_page(page.text)
    out["views_count"] = None
    out["views_note"] = None

    if not out["username"]:
        out["error"] = (
            "не нашёл автора: метатеги пусты. Обычно это протухшие куки — страница отдаётся "
            "как гостю. Обновите IG_COOKIE."
        )
        return out

    out["views_count"], out["views_note"] = views_from_profile(out["username"], out["shortcode"], cookie)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "не указана ссылка на рилс"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(parse(sys.argv[1], os.environ.get("IG_COOKIE")), ensure_ascii=False, indent=2))
