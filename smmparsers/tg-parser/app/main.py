"""
Парсер сообщений Telegram по ключевому слову — веб-обёртка над Telethon.

Задача заказчика (3 сентября 2026): развернуть на сервере скрипт telethon.py,
дать интерфейс с авторизацией в Telegram, диапазоном дат, группой и ключевым словом,
закрыть доступ паролем, результат отдавать CSV.

Два отличия от исходного скрипта названы вслух, потому что они меняют выборку:
  1. Обе даты ВКЛЮЧИТЕЛЬНО. В скрипте стояло offset_date=date_to, а Telethon отдаёт
     сообщения строго СТАРШЕ этой отметки — последний день диапазона терялся молча.
  2. Даты понимаются по Киеву, а не по UTC: человек, который пишет «1–31 августа»,
     имеет в виду свой календарь. Так же считают отчёты CRM.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

# ---------------------------------------------------------------- конфигурация

DATA = Path(os.environ.get("DATA_DIR", "/data"))
RESULTS = DATA / "results"
# У каждого вошедшего СВОЙ файл: и ключи приложения, и сессия Telegram.
# Общими они быть не должны — по чужому api_id человек работает от чужого имени
# перед Telegram, а увидев чужой номер, ещё и читает чужие чаты.
SESSIONS = DATA / "sessions"
TZ = ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Kyiv"))
ROOT = os.environ.get("ROOT_PATH", "").rstrip("/")

PANEL_HASH = os.environ["PANEL_PASSWORD_HASH"]      # scrypt: соль:хеш, оба hex
# Разделитель ДВОЕТОЧИЕ, а не $: docker compose трактует $ в env_file как подстановку
# переменной и вырезает его — до контейнера приезжал хеш без разделителя.
COOKIE_SECRET = os.environ["COOKIE_SECRET"]
FERNET = Fernet(os.environ["SESSION_KEY"].encode())

RESULTS.mkdir(parents=True, exist_ok=True)
SESSIONS.mkdir(parents=True, exist_ok=True)
COOKIE = "tgp"
signer = URLSafeTimedSerializer(COOKIE_SECRET, salt="tg-parser")

env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(["html"]),
)

# ------------------------------------------------------------------- пароль

def verify_password(raw: str) -> bool:
    """Сравнение с хешем scrypt. hmac.compare_digest — чтобы время ответа не выдавало пароль."""
    try:
        salt_hex, want_hex = PANEL_HASH.split(":", 1)
    except ValueError:
        return False
    got = hashlib.scrypt(raw.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(got.hex(), want_hex)


_fails: dict[str, list[float]] = {}

def throttled(ip: str) -> int:
    """Сколько секунд ждать. Пять неудач за пять минут — минута паузы."""
    now = time.time()
    tries = [t for t in _fails.get(ip, []) if now - t < 300]
    _fails[ip] = tries
    if len(tries) >= 5:
        return int(60 - (now - tries[-1])) or 1
    return 0


def note_fail(ip: str) -> None:
    _fails.setdefault(ip, []).append(time.time())


def sid_of(request: Request) -> str:
    """Идентификатор ВОШЕДШЕГО. Пароль общий, но подключённый Telegram — у каждого свой:
    иначе один человек видит чужой номер и, что хуже, читает чаты чужим аккаунтом."""
    raw = request.cookies.get(COOKIE)
    if not raw:
        return ""
    try:
        data = signer.loads(raw, max_age=60 * 60 * 12)
    except BadSignature:
        return ""
    sid = str(data.get("sid", ""))
    return sid if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", sid) else ""


def authed(request: Request) -> bool:
    return bool(sid_of(request))

# --------------------------------------------------------------- Telegram

_clients: dict[str, TelegramClient] = {}
_client_lock = asyncio.Lock()
_login_phone: dict[str, str] = {}   # телефон -> phone_code_hash, живёт до ввода кода


def _read(path: Path) -> dict:
    """Всё на диске лежит зашифрованным, ключ — в окружении, не на томе:
    украденная копия тома сама по себе не даёт ни войти в Telegram, ни взять ключи."""
    if not path.exists():
        return {}
    try:
        return json.loads(FERNET.decrypt(path.read_bytes()).decode())
    except (InvalidToken, ValueError, OSError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.write_bytes(FERNET.encrypt(json.dumps(data).encode()))
    path.chmod(0o600)


def session_path(sid: str) -> Path:
    return SESSIONS / f"{sid}.enc"


def load_state(sid: str) -> dict:
    return _read(session_path(sid))


def patch_state(sid: str, patch: dict) -> None:
    state = load_state(sid)
    state.update(patch)
    _write(session_path(sid), state)


async def get_client(sid: str) -> TelegramClient:
    """И ключи, и сессия — личные, у каждого вошедшего свои. Зашивать ключи в конфиг
    нельзя: тогда смена аккаунта — это деплой, а команда не подключит свой."""
    state = load_state(sid)
    if not state.get("api_id") or not state.get("api_hash"):
        raise RuntimeError("Сначала задайте свои api_id и api_hash на главной странице.")
    async with _client_lock:
        client = _clients.get(sid)
        if client is None:
            client = TelegramClient(
                StringSession(state.get("session") or ""),
                int(state["api_id"]), state["api_hash"],
                # Мелкие паузы Telegram отсиживаем сами; о крупных сообщаем человеку.
                flood_sleep_threshold=120,
            )
            _clients[sid] = client
        if not client.is_connected():
            await client.connect()
        return client


async def tg_status(sid: str) -> dict:
    state = load_state(sid)
    if not state.get("api_id") or not state.get("api_hash"):
        return {"connected": False, "needs_keys": True}
    client = await get_client(sid)
    if not await client.is_user_authorized():
        return {"connected": False, "needs_keys": False}
    me = await client.get_me()
    name = " ".join(x for x in [me.first_name or "", me.last_name or ""] if x).strip()
    return {"connected": True, "needs_keys": False, "name": name or "—",
            "username": me.username or "", "phone": me.phone or ""}

# ------------------------------------------------------------------ работа

@dataclass
class Job:
    id: str
    state: str = "running"          # running | done | error
    scanned: int = 0
    found: int = 0
    position: str = ""              # до какой даты дошли
    error: str = ""
    waiting_until: float = 0.0      # пауза, назначенная Telegram
    file: Path | None = None
    rows: list[dict] = field(default_factory=list)
    truncated: bool = False
    started: float = field(default_factory=time.time)
    params: dict = field(default_factory=dict)


_job: Job | None = None
FIELDS = ["message_id", "date", "count", "user_id", "username", "name", "text", "views", "link"]

# Сколько строк отдаём НА ЭКРАН. Файл собирается целиком — потолок только у таблицы,
# иначе браузер планшета ляжет на длинной истории. Об усечении говорим вслух:
# молча показанная половина хуже отказа.
SCREEN_LIMIT = 5000

# Сколько прогонов держим. Результат кладём на диск рядом с файлом выгрузки, иначе
# перезагрузка страницы (и тем более перезапуск приложения) теряла бы работу,
# за которую Telegram уже отдал историю — а он отдаёт её небыстро и не бесконечно.
KEEP_RUNS = 20


def result_path(job_id: str) -> Path:
    return RESULTS / f"{job_id}.json"


def save_result(job: "Job") -> None:
    result_path(job.id).write_text(json.dumps({
        "id": job.id, "params": job.params, "scanned": job.scanned, "found": job.found,
        "truncated": job.truncated, "limit": SCREEN_LIMIT,
        "finished": time.time(), "rows": job.rows,
    }, ensure_ascii=False), encoding="utf-8")
    prune_runs()


def load_result(job_id: str) -> dict | None:
    p = result_path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def history() -> list[dict]:
    """Последние прогоны, свежие сверху. Читаем шапку файла, не таща строки."""
    out = []
    for p in sorted(RESULTS.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        d = load_result(p.stem)
        if d:
            out.append({k: d.get(k) for k in ("id", "params", "found", "scanned", "finished")})
    return out


def prune_runs() -> None:
    files = sorted(RESULTS.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    for p in files[KEEP_RUNS:]:
        p.unlink(missing_ok=True)
        (RESULTS / f"{p.stem}.csv").unlink(missing_ok=True)


def parse_target(raw: str) -> str | int:
    """Группа задаётся именем, ссылкой или числовым id — принимаем всё три вида."""
    s = raw.strip()
    s = re.sub(r"^https?://(t\.me|telegram\.me)/", "", s)
    s = s.removeprefix("@").strip("/")
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


# Кеш списка чатов — ПО КЛЮЧУ сессии Telegram: общий кеш показал бы одному
# человеку чаты другого.
_dialogs: dict[str, dict] = {}


async def list_dialogs(client: TelegramClient, force: bool = False) -> list[dict]:
    """Группы и каналы аккаунта. Обход диалогов не бесплатный, поэтому держим
    пять минут в памяти: список нужен и выпадашке, и поиску по названию."""
    key = str(id(client))
    hit = _dialogs.get(key)
    if not force and hit and time.time() - hit["at"] < 300:
        return hit["items"]
    items = []
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            items.append({"id": d.id, "title": d.name or "—",
                          "username": getattr(d.entity, "username", None) or ""})
    items.sort(key=lambda x: x["title"].lower())
    _dialogs[key] = {"at": time.time(), "items": items}
    return items


async def resolve_entity(client: TelegramClient, raw: str):
    target = parse_target(raw)
    try:
        return await client.get_entity(target)
    except (ValueError, TypeError):
        pass

    # Дальше ищем среди диалогов аккаунта. Числовой id без access_hash иначе не
    # разрешается вовсе, а НАЗВАНИЕ Telethon не понимает в принципе — хотя человек
    # знает группу именно по названию, и вводит его.
    dialogs = await list_dialogs(client)
    if isinstance(target, int):
        want = abs(target)
        bare = int(str(want)[3:]) if str(want).startswith("100") else want
        for d in dialogs:
            if abs(d["id"]) in (want, bare, int("100" + str(bare))):
                return await client.get_entity(d["id"])
        raise ValueError(
            "Группы с таким id нет среди чатов этого аккаунта. Проверьте id — "
            "и то, что аккаунт состоит в группе."
        )

    needle = target.strip().lower()
    exact = [d for d in dialogs if d["title"].strip().lower() == needle]
    if len(exact) == 1:
        return await client.get_entity(exact[0]["id"])
    part = exact or [d for d in dialogs if needle in d["title"].lower()]
    if len(part) == 1:
        return await client.get_entity(part[0]["id"])
    if len(part) > 1:
        names = ", ".join(f'«{d["title"]}»' for d in part[:6])
        raise ValueError(
            f"Под это название подходит несколько чатов: {names}. "
            "Выберите нужный из списка рядом с полем."
        )
    raise ValueError(
        "Не нашёл такую группу среди чатов этого аккаунта. Выберите её из списка "
        "рядом с полем — там ровно те чаты, в которых состоит подключённый аккаунт."
    )


def message_link(entity, channel_id: int, message_id: int) -> str:
    uname = getattr(entity, "username", None)
    if uname:
        return f"https://t.me/{uname}/{message_id}"
    return f"https://t.me/c/{channel_id}/{message_id}"


async def run_job(job: Job, sid: str, target: str, keyword: str, d_from: str, d_to: str) -> None:
    global _job
    try:
        client = await get_client(sid)
        entity = await resolve_entity(client, target)

        # Границы: обе даты включительно, по киевскому календарю.
        start = datetime.strptime(d_from, "%Y-%m-%d").replace(tzinfo=TZ).astimezone(timezone.utc)
        end_excl = (datetime.strptime(d_to, "%Y-%m-%d").replace(tzinfo=TZ)
                    + timedelta(days=1)).astimezone(timezone.utc)

        raw_id = abs(entity.id)
        channel_id = int(str(raw_id)[3:]) if str(raw_id).startswith("100") else raw_id
        needle = keyword.lower()
        rows: list[dict] = []

        async for message in client.iter_messages(entity, limit=None, offset_date=end_excl):
            if message.date < start:
                break
            job.scanned += 1
            job.position = str(message.date.astimezone(TZ))[:10]
            if not message.text or needle not in message.text.lower():
                continue

            sender = message.sender
            user_id = username = name = ""
            if sender is not None:
                user_id = sender.id
                username = getattr(sender, "username", None) or getattr(sender, "title", None) or ""
                first = getattr(sender, "first_name", "") or ""
                last = getattr(sender, "last_name", "") or ""
                name = (first + " " + last).strip() or getattr(sender, "title", "") or ""

            rows.append({
                "message_id": message.id,
                "date": str(message.date.astimezone(TZ))[:10],
                "count": 1,
                "user_id": user_id,
                "username": username,
                "name": name,
                "text": message.text,
                "views": message.views or "",
                "link": message_link(entity, channel_id, message.id),
            })
            job.found += 1

        path = RESULTS / f"{job.id}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        job.file = path
        job.rows = rows[:SCREEN_LIMIT]
        job.truncated = len(rows) > SCREEN_LIMIT
        job.state = "done"
        save_result(job)

    except errors.FloodWaitError as e:
        job.state = "error"
        job.error = (f"Telegram попросил подождать {e.seconds} с — это защита от частых запросов. "
                     f"Повторите позже; уже просмотренное не потеряно, но файл не собран.")
    except ValueError as e:
        job.state = "error"
        job.error = str(e)
    except Exception as e:  # noqa: BLE001 — текст ошибки нужен человеку целиком
        job.state = "error"
        job.error = human(e)

# --------------------------------------------------------------------- HTTP

# root_path НЕ задаём намеренно. Starlette при заданном root_path срезает этот префикс
# с пути ДО поиска маршрута — и маршруты, у которых тот же сегмент стоял в адресе
# (/tg/keys при root_path=/tg), переставали находиться вовсе: 404 на верной форме.
# Префикс нужен только для ссылок и cookie, и мы подставляем его сами через ROOT.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def human(e: Exception) -> str:
    """Наши собственные сообщения показываем как есть; чужие — с типом, иначе
    непонятно, что вообще случилось."""
    if isinstance(e, (RuntimeError, ValueError)):
        return str(e)
    return f"{type(e).__name__}: {e}"


def page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(env.get_template(name).render(base=ROOT, **ctx))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not authed(request):
        return page("login.html")
    try:
        status = await tg_status(sid_of(request))
    except Exception as e:  # noqa: BLE001
        status = {"connected": False, "warn": f"{type(e).__name__}: {e}"}
    return page("index.html", tg=status, job=_job)


@app.post("/login")
async def login(request: Request, password: str = Form("")):
    ip = request.client.host if request.client else "?"
    wait = throttled(ip)
    if wait:
        return page("login.html", error=f"Слишком много попыток. Подождите {wait} с.")
    if not verify_password(password):
        note_fail(ip)
        return page("login.html", error="Неверный пароль.")
    resp = RedirectResponse(f"{ROOT}/", status_code=303)
    resp.set_cookie(COOKIE, signer.dumps({"sid": secrets.token_urlsafe(12), "t": time.time()}),
                    httponly=True,
                    secure=True, samesite="lax", max_age=60 * 60 * 12, path=ROOT or "/")
    return resp


@app.post("/logout")
async def logout():
    resp = RedirectResponse(f"{ROOT}/", status_code=303)
    resp.delete_cookie(COOKIE, path=ROOT or "/")
    return resp


@app.post("/keys")
async def tg_keys(request: Request, api_id: str = Form(...), api_hash: str = Form(...)):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    if not api_id.strip().isdigit() or len(api_hash.strip()) < 16:
        return page("index.html", tg={"connected": False, "needs_keys": True}, job=_job,
                    error="api_id — только цифры, api_hash — длинная строка из my.telegram.org.")
    sid = sid_of(request)
    new_id, new_hash = int(api_id.strip()), api_hash.strip()
    was = load_state(sid)
    # Сессию Telegram сбрасываем ТОЛЬКО если ключи реально другие: она привязана к
    # api_id, под которым выдана. Повторный ввод тех же ключей не должен стоить
    # человеку ещё одного кода из мессенджера.
    same = was.get("api_id") == new_id and was.get("api_hash") == new_hash
    patch = {"api_id": new_id, "api_hash": new_hash}
    if not same:
        patch["session"] = ""
    patch_state(sid, patch)
    _clients.pop(sid, None)
    return RedirectResponse(f"{ROOT}/", status_code=303)


@app.post("/send-code")
async def send_code(request: Request, phone: str = Form(...)):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    phone = phone.strip()
    try:
        client = await get_client(sid_of(request))
        sent = await client.send_code_request(phone)
        _login_phone[phone] = sent.phone_code_hash
        return page("code.html", phone=phone)
    except Exception as e:  # noqa: BLE001
        return page("index.html", tg=await tg_status(sid_of(request)), job=_job,
                    error=f"Не удалось отправить код: {human(e)}")


@app.post("/sign-in")
async def sign_in(request: Request, phone: str = Form(...), code: str = Form(...)):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    sid = sid_of(request)
    try:
        client = await get_client(sid)
        await client.sign_in(phone=phone, code=code.strip(),
                             phone_code_hash=_login_phone.get(phone))
    except errors.SessionPasswordNeededError:
        return page("password.html", phone=phone)
    except Exception as e:  # noqa: BLE001
        return page("code.html", phone=phone, error=human(e))
    patch_state(sid, {"session": client.session.save()})
    _login_phone.pop(phone, None)
    return RedirectResponse(f"{ROOT}/", status_code=303)


@app.post("/tg-password")
async def tg_password(request: Request, phone: str = Form(...), password: str = Form(...)):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    sid = sid_of(request)
    try:
        client = await get_client(sid)
        await client.sign_in(password=password)
    except Exception as e:  # noqa: BLE001
        return page("password.html", phone=phone, error=human(e))
    patch_state(sid, {"session": client.session.save()})
    return RedirectResponse(f"{ROOT}/", status_code=303)


@app.post("/disconnect")
async def tg_disconnect(request: Request):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    sid = sid_of(request)
    try:
        client = await get_client(sid)
        await client.log_out()
    except Exception:  # noqa: BLE001
        pass
    patch_state(sid, {"session": ""})   # ключи свои оставляем: меняется аккаунт, не приложение
    _clients.pop(sid, None)
    return RedirectResponse(f"{ROOT}/", status_code=303)


@app.post("/run")
async def run(request: Request, target: str = Form(...), keyword: str = Form(...),
              date_from: str = Form(...), date_to: str = Form(...)):
    global _job
    if not authed(request):
        return JSONResponse({"error": "нет доступа"}, status_code=403)
    if _job and _job.state == "running":
        return JSONResponse({"error": "Один прогон уже идёт — дождитесь его конца."}, status_code=409)
    if date_from > date_to:
        return JSONResponse({"error": "Начало диапазона позже конца."}, status_code=400)
    if not keyword.strip():
        return JSONResponse({"error": "Укажите ключевое слово."}, status_code=400)

    _job = Job(id=uuid.uuid4().hex[:12],
               params={"target": target, "keyword": keyword, "from": date_from, "to": date_to})
    asyncio.create_task(run_job(_job, sid_of(request), target, keyword.strip(), date_from, date_to))
    return JSONResponse({"job": _job.id})


@app.get("/dialogs")
async def dialogs(request: Request, refresh: str = ""):
    """Список групп аккаунта для выпадашки — чтобы название не набирали руками."""
    if not authed(request):
        return JSONResponse({"error": "нет доступа"}, status_code=403)
    try:
        client = await get_client(sid_of(request))
        if not await client.is_user_authorized():
            return JSONResponse({"items": []})
        return JSONResponse({"items": await list_dialogs(client, force=bool(refresh))})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": human(e), "items": []}, status_code=200)


@app.get("/progress")
async def progress(request: Request):
    if not authed(request):
        return JSONResponse({"error": "нет доступа"}, status_code=403)
    if not _job:
        return JSONResponse({"state": "idle"})
    return JSONResponse({
        "state": _job.state, "scanned": _job.scanned, "found": _job.found,
        "position": _job.position, "error": _job.error, "id": _job.id,
        "seconds": int(time.time() - _job.started),
        "ready": bool(_job.file and _job.file.exists()),
    })


@app.get("/results/{job_id}")
async def results(request: Request, job_id: str):
    """Готовый результат для таблицы на странице. Фильтры и сортировка делаются в браузере:
    набор уже в памяти, и гонять его на сервер за каждым нажатием незачем."""
    if not authed(request):
        return JSONResponse({"error": "нет доступа"}, status_code=403)
    safe = re.sub(r"[^a-f0-9]", "", job_id)
    data = load_result(safe)
    if data is None and _job and _job.id == safe:
        data = {"id": _job.id, "params": _job.params, "found": _job.found,
                "truncated": _job.truncated, "limit": SCREEN_LIMIT, "rows": _job.rows}
    if data is None:
        return JSONResponse({"error": "результат не найден"}, status_code=404)
    data["shown"] = len(data.get("rows") or [])
    data["total"] = data.get("found", data["shown"])
    return JSONResponse(data)


@app.get("/history")
async def history_list(request: Request):
    """Последние прогоны — чтобы результат не пропадал при перезагрузке страницы
    и можно было вернуться к предыдущему поиску, не гоняя Telegram заново."""
    if not authed(request):
        return JSONResponse({"error": "нет доступа"}, status_code=403)
    running = None
    if _job and _job.state == "running":
        running = {"id": _job.id, "params": _job.params}
    return JSONResponse({"items": history(), "running": running})


@app.get("/download/{job_id}")
async def download(request: Request, job_id: str):
    if not authed(request):
        return RedirectResponse(f"{ROOT}/", status_code=303)
    path = RESULTS / f"{re.sub(r'[^a-f0-9]', '', job_id)}.csv"
    if not path.exists():
        return JSONResponse({"error": "Файл не найден — возможно, прогон ещё идёт."}, status_code=404)
    return FileResponse(path, media_type="text/csv", filename=f"telegram-{job_id}.csv")


@app.get("/healthz")
async def healthz():
    return {"ok": True}
