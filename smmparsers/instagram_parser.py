#!/root/venv/bin/python3
import sys
import re
import json
import requests
from bs4 import BeautifulSoup

def parse_instagram_reel(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Извлекаем shortcode из URL
    shortcode_match = re.search(r"/reel/([^/]+)/?", url)
    if not shortcode_match:
        return {"error": "Не удалось извлечь ID рилса из URL"}
    
    shortcode = shortcode_match.group(1)
    
    # --- Шаг 1: Загружаем страницу рилса для получения username ---
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Ошибка загрузки страницы рилса: {e}"}
    
    html_text = response.text
    soup = BeautifulSoup(html_text, "html.parser")
    username = None
    
    # Способ 1: Ищем в script с type="application/json" и data-sjs
    scripts_json = soup.find_all("script", type="application/json")
    for script in scripts_json:
        if script.string:
            try:
                # Пытаемся распарсить JSON
                data = json.loads(script.string)
                
                # Рекурсивная функция для поиска username в JSON
                def find_username(obj):
                    if isinstance(obj, dict):
                        # Если есть поле username, возвращаем его
                        if "username" in obj and isinstance(obj["username"], str):
                            return obj["username"]
                        # Рекурсивно ищем во всех значениях
                        for value in obj.values():
                            result = find_username(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_username(item)
                            if result:
                                return result
                    return None
                
                found_username = find_username(data)
                if found_username:
                    username = found_username
                    break
            except:
                continue
    
    # Способ 2: Ищем в сыром HTML через regex паттерны
    if not username:
        patterns = [
            r'"username"\s*:\s*"([^"]+)"',
            r'"owner"\s*:\s*\{\s*"username"\s*:\s*"([^"]+)"',
            r'"user"\s*:\s*\{\s*"username"\s*:\s*"([^"]+)"',
            r'instagram\.com/([a-zA-Z0-9._]+)/reel/',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_text)
            if matches:
                # Фильтруем служебные пути
                for match in matches:
                    if match not in ["reel", "reels", "p", "explore", "accounts", "stories"]:
                        username = match
                        break
            if username:
                break
    
    # Способ 3: Ищем через обычные script теги
    if not username:
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "username" in script.string:
                # Ищем объект с owner/user/username
                username_match = re.search(r'"username"\s*:\s*"([^"]+)"', script.string)
                if username_match:
                    potential = username_match.group(1)
                    if potential not in ["reel", "reels", "p", "explore", "accounts", "stories"]:
                        username = potential
                        break
    
    # Способ 4: Ищем meta теги
    if not username:
        meta_tags = [
            soup.find("meta", property="og:url"),
            soup.find("meta", property="al:ios:url"),
            soup.find("meta", property="al:android:url"),
        ]
        
        for meta in meta_tags:
            if meta and meta.get("content"):
                content = meta.get("content")
                username_match = re.search(r"instagram\.com/([^/]+)/", content)
                if username_match:
                    potential = username_match.group(1)
                    if potential not in ["reel", "reels", "p", "explore"]:
                        username = potential
                        break
    
    if not username:
        return {"error": "Не удалось найти username на странице рилса"}
    
    # --- Шаг 2: Переходим на страницу /reels/ профиля ---
    reels_url = f"https://www.instagram.com/{username}/reels/"
    
    try:
        reels_response = requests.get(reels_url, headers=headers, timeout=20)
        reels_response.raise_for_status()
    except Exception as e:
        return {"error": f"Ошибка загрузки страницы reels профиля: {e}"}
    
    soup_reels = BeautifulSoup(reels_response.text, "html.parser")
    
    # Ищем ссылку с нашим shortcode
    reel_link = soup_reels.find("a", href=re.compile(f"reel/{shortcode}"))
    
    if not reel_link:
        return {
            "shortcode": shortcode,
            "username": username,
            "error": "Не удалось найти рилс на странице профиля"
        }
    
    # Парсим статистику
    likes_count = None
    comments_count = None
    views_count = None
    
    # Ищем список статистики внутри ссылки
    stats_list = reel_link.find("ul", class_=re.compile(r"x6s0dn4"))
    
    if stats_list:
        stats_items = stats_list.find_all("li")
        
        # Первый li - лайки, второй - комментарии
        if len(stats_items) >= 1:
            likes_span = stats_items[0].find("span", class_=re.compile(r"html-span.*x1vvkbs"))
            if likes_span:
                likes_text = likes_span.get_text(strip=True).replace(",", "")
                try:
                    likes_count = int(likes_text)
                except:
                    pass
        
        if len(stats_items) >= 2:
            comments_span = stats_items[1].find("span", class_=re.compile(r"html-span.*x1vvkbs"))
            if comments_span:
                comments_text = comments_span.get_text(strip=True).replace(",", "")
                try:
                    comments_count = int(comments_text)
                except:
                    pass
    
    # Ищем просмотры в блоке _aaj_
    views_block = reel_link.find("div", class_="_aaj_")
    
    if views_block:
        views_span = views_block.find("span", class_=re.compile(r"html-span.*x1vvkbs"))
        if views_span:
            views_text = views_span.get_text(strip=True)
            
            # Парсим число с K/M
            if re.match(r"^\d+(\.\d+)?[KkMm]?$", views_text):
                num_match = re.findall(r"\d+\.?\d*", views_text)
                if num_match:
                    num = float(num_match[0])
                    if "K" in views_text.upper():
                        num *= 1_000
                    elif "M" in views_text.upper():
                        num *= 1_000_000
                    views_count = int(num)
    
    return {
        "shortcode": shortcode,
        "username": username,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "views_count": views_count,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Не указана ссылка на рилс"}, ensure_ascii=False))
        sys.exit(1)
    
    url = sys.argv[1]
    result = parse_instagram_reel(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
