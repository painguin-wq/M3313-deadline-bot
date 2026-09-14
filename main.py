import datetime as dt
import html
import json
import locale
import logging
import os
import re
import time
import urllib.parse
import sys
from pathlib import Path

import requests

DEADLINES_PATH = Path(os.getenv("DEADLINES_PATH") or Path(__file__).with_name("DEADLINES.json"))
DEADLINES_URL = os.getenv("DEADLINES_URL") or ""
BOT_NAME = "dead inside M3313"
BOT_USERNAME = "m3313_deadinside_bot"

API_URL = 'https://api.telegram.org/bot'
TOKEN = os.getenv("TOKEN")
MAIN_GROUP_ID = int(os.getenv("MAIN_GROUP_ID") or '0')
EDIT_MESSAGE_ID = int(os.getenv("EDIT_MESSAGE_ID") or '0')
ADD_CALENDAR_LINK = os.getenv("ADD_CALENDAR_LINK") == 'true'
ADMIN_USER_IDS = {
    int(x) for x in (os.getenv("ADMIN_USER_IDS") or "").replace(" ", "").split(",") if x
}
REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS") or "60")

assert TOKEN, "Missing token!"
assert MAIN_GROUP_ID, "Missing group ID!"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

TYPE_PREFIX_RE = re.compile(r'^\[([^\]]+)\]\s*', flags=re.IGNORECASE)
CMD_RE = re.compile(r'^/([A-Za-z]+)(?:@[\w_]+)?(?:\s+(.*))?$', re.DOTALL)
MOSCOW = dt.timezone(dt.timedelta(hours=3))
SKILL_ALIASES = {
    'web': 'frontend', 'frontend': 'frontend', 'html': 'frontend', 'css': 'frontend',
    'uml': 'uml', 'сети': 'networks', 'networks': 'networks', 'net': 'networks',
    'dwh': 'dwh', 'хранилища': 'dwh', 'warehouse': 'dwh',
    'бд': 'databases', 'db': 'databases', 'databases': 'databases',
    'ml': 'ml', 'телеком': 'telecom', 'telecom': 'telecom',
    'backend': 'backend', 'math': 'math', 'algorithms': 'algorithms',
}
HELP_TEXT = (
    "<b>dead inside M3313</b>\n\n"
    "<code>/add Название | ДД.ММ.ГГГГ ЧЧ:ММ | место | препод | skill | url | описание</code>\n"
    "<code>/edit часть названия | time=15.09.2026 18:50 | place=ауд. 2335</code>\n"
    "<code>/delete часть названия</code>\n"
    "<code>/list</code> — ближайшие 5 лаб\n"
    "<code>/all</code> — все лабы\n"
    "<code>/help</code>"
)


class TelegramException(Exception):
    def __init__(self, *, error_code: int, description: str, **_):
        super().__init__(f'Error {error_code}: {description}')
        self.error_code = error_code
        self.description = description


def telegram_request(method: str, args: dict | None = None, timeout: int = 30):
    try:
        data = requests.post(
            API_URL + f'{TOKEN}/{method}',
            json=args or {},
            timeout=timeout,
        ).json()
        if not data['ok']:
            raise TelegramException(**data)
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error in {method}: {e}")
        raise


def send_message(text: str, chat_id: int | None = None, reply_to: int | None = None) -> int:
    args = {
        'chat_id': chat_id or MAIN_GROUP_ID,
        'parse_mode': 'HTML',
        'text': text,
        'link_preview_options': {'is_disabled': True},
    }
    if reply_to:
        args['reply_parameters'] = {'message_id': reply_to}
    return telegram_request('sendMessage', args)['result']['message_id']


def edit_message(message_id: int, text: str, chat_id: int | None = None) -> int:
    return telegram_request('editMessageText', {
        'chat_id': chat_id or MAIN_GROUP_ID,
        'parse_mode': 'HTML',
        'message_id': message_id,
        'text': text,
        'link_preview_options': {'is_disabled': True},
    })['result']['message_id']


def delete_message(message_id: int, chat_id: int | None = None) -> bool:
    return telegram_request('deleteMessage', {
        'chat_id': chat_id or MAIN_GROUP_ID,
        'message_id': message_id,
    })['result']


def get_current_time() -> str:
    current_time = dt.datetime.now()
    hour = f"{current_time.hour:02d}"
    minute = f"{current_time.minute:02d}"
    return f"{hour}:{minute}"


def get_dt_obj_from_string(time_str: str) -> dt.datetime:
    time_str = time_str.replace('GMT+3', '+0300')
    try:
        locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'C')
    return dt.datetime.strptime(time_str, "%d %b %Y %H:%M:%S %z")


def format_stored_time(value: dt.datetime) -> str:
    localized = value.astimezone(MOSCOW)
    try:
        locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'C')
    return localized.strftime("%d %b %Y %H:%M:%S") + " GMT+3"


def parse_user_time(raw: str) -> dt.datetime:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty time")
    raw = raw.replace('GMT+3', '+0300')
    patterns = [
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M",
        "%d %B %Y %H:%M",
    ]
    for pattern in patterns:
        try:
            parsed = dt.datetime.strptime(raw, pattern)
            if parsed.tzinfo is None:
                if pattern in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
                    parsed = parsed.replace(hour=23, minute=59)
                parsed = parsed.replace(tzinfo=MOSCOW)
            return parsed
        except ValueError:
            continue
    raise ValueError(raw)


def escape(value) -> str:
    return html.escape(str(value), quote=True) if value is not None else ""


def display_name(item: dict) -> str:
    return TYPE_PREFIX_RE.sub('', item.get('name') or '').strip()


def deadline_type(item: dict) -> str:
    explicit = (item.get('type') or '').strip().lower()
    if explicit:
        return explicit
    match = TYPE_PREFIX_RE.match(item.get('name') or '')
    return match.group(1).lower() if match else ''


def deadline_skills(item: dict) -> list[str]:
    skills = item.get('skills') or []
    if isinstance(skills, str):
        return [skills]
    return [str(s) for s in skills if s]


def normalize_skill(raw: str) -> str:
    key = raw.strip().lower()
    return SKILL_ALIASES.get(key, key.replace(' ', '-') or 'other')


def generate_link(item: dict) -> str:
    dt_obj = get_dt_obj_from_string(item['time'])
    formatted_time = dt_obj.strftime("%Y%m%dT%H%M%S%z")
    details_parts = [
        item.get('description') or '',
        f"Преподаватель: {item['teacher']}" if item.get('teacher') else '',
        f"Ссылка: {item['url']}" if item.get('url') else '',
        f"Дедлайн добавлен ботом {BOT_NAME} (https://t.me/{BOT_USERNAME})",
    ]
    details = urllib.parse.quote('\n'.join(part for part in details_parts if part))
    location = urllib.parse.quote(item.get('place') or '')
    link = (
        "https://calendar.google.com/calendar/u/0/r/eventedit?"
        f"text={urllib.parse.quote(display_name(item))}&"
        f"dates={formatted_time}/{formatted_time}"
        f"&details={details}"
    )
    if location:
        link += f"&location={location}"
    return link


def get_human_timedelta(time_str: str) -> str:
    dt_obj = get_dt_obj_from_string(time_str)
    delta = dt_obj - dt.datetime.now(dt_obj.tzinfo)
    total_seconds = int(delta.total_seconds())
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    if days >= 5:
        return f"{days} дней"
    if days >= 2:
        return f"{days} дня"
    if days == 1:
        return f"1 день {hours}ч {minutes}м"
    return f"{hours}ч {minutes}м"


def get_human_time(time_str: str) -> str:
    dt_obj = get_dt_obj_from_string(time_str)
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'C')
    return dt_obj.strftime("%a, %d %B в %H:%M")


def timestamp_func(a: dict) -> float:
    return get_dt_obj_from_string(a["time"]).timestamp()


def relevant_filter_func(d: dict) -> bool:
    return get_dt_obj_from_string(d["time"]) >= dt.datetime.now(
        get_dt_obj_from_string(d["time"]).tzinfo
    )


def deadline_type_filter_func(d: dict, dtype: str = '') -> bool:
    current = deadline_type(d)
    if not dtype:
        return not current
    return current == dtype.lower()


def empty_payload() -> dict:
    return {"skills": [], "deadlines": []}


def load_deadlines_payload() -> dict:
    if DEADLINES_PATH.exists():
        try:
            with DEADLINES_PATH.open(encoding='utf-8') as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                payload.setdefault("skills", [])
                payload.setdefault("deadlines", [])
                return payload
        except Exception as e:
            logging.error(f"Failed to read {DEADLINES_PATH}: {e}")

    if DEADLINES_URL:
        try:
            payload = requests.get(DEADLINES_URL, timeout=30).json()
            if isinstance(payload, dict):
                payload.setdefault("skills", [])
                payload.setdefault("deadlines", [])
                return payload
        except Exception as e:
            logging.error(f"Failed to fetch deadlines: {e}")

    return empty_payload()


def save_deadlines_payload(payload: dict) -> None:
    tmp_path = DEADLINES_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(DEADLINES_PATH)


TWO_WEEKS = dt.timedelta(days=14)
ONE_WEEK = dt.timedelta(days=7)
LIST_LIMIT = 5
EDIT_FIELD_ALIASES = {
    'name': 'name', 'название': 'name',
    'time': 'time', 'date': 'time', 'срок': 'time', 'дата': 'time',
    'place': 'place', 'место': 'place',
    'teacher': 'teacher', 'препод': 'teacher', 'преподаватель': 'teacher',
    'skills': 'skills', 'skill': 'skills',
    'url': 'url', 'link': 'url',
    'description': 'description', 'desc': 'description', 'описание': 'description',
    'type': 'type',
}


def now_msk() -> dt.datetime:
    return dt.datetime.now(MOSCOW)


def due_dt(item: dict) -> dt.datetime:
    return get_dt_obj_from_string(item["time"]).astimezone(MOSCOW)


def remaining(item: dict) -> dt.timedelta:
    return due_dt(item) - now_msk()


def warning_for(item: dict) -> tuple[str, int] | None:
    due = due_dt(item)
    left = due - now_msk()
    if left.total_seconds() < 0:
        return None
    today = now_msk().date()
    due_day = due.date()
    name = display_name(item)
    if due_day == today:
        return (f"Сегодня сдача лабы {name}", 0)
    if due_day == today + dt.timedelta(days=1):
        return (f"Завтра сдача лабы {name}", 1)
    if left < ONE_WEEK:
        return (f"Срочно делать лабу {name}", 2)
    if left <= TWO_WEEKS:
        return (f"Пора начинать лабу {name}", 3)
    return None


def warning_prefix(item: dict) -> str:
    warn = warning_for(item)
    if not warn:
        return ""
    return f"<b>{escape(warn[0])}</b>\n"


def format_item_block(item: dict, index: int, *, warnings: bool = True) -> str:
    name = escape(display_name(item))
    url = item.get('url')
    title = f"<a href='{escape(url)}'>{name}</a>" if url else name
    when = get_human_time(item["time"])
    if ADD_CALENDAR_LINK:
        when = f"<a href='{generate_link(item)}'>{when}</a>"
    left = get_human_timedelta(item['time'])
    lines = []
    if warnings:
        warn = warning_prefix(item)
        if warn:
            lines.append(warn.rstrip())
    lines.append(f"{index}. <b>{title}</b> — {left}")
    lines.append(when)
    details = []
    if item.get('place'):
        details.append(escape(item['place']))
    if item.get('teacher'):
        details.append(escape(item['teacher']))
    if details:
        lines.append(" · ".join(details))
    description = (item.get('description') or "").strip()
    if description:
        if len(description) > 140:
            description = description[:137] + "…"
        lines.append(f"<i>{escape(description)}</i>")
    return "\n".join(lines) + "\n\n"


def add_items(text: str, items: list, *, warnings: bool = True) -> str:
    if not items:
        return text
    for i, item in enumerate(items, start=1):
        text += format_item_block(item, i, warnings=warnings)
    return text


def upcoming_sorted() -> list[dict]:
    payload = load_deadlines_payload()
    relevant = [d for d in payload.get("deadlines", []) if relevant_filter_func(d)]
    relevant.sort(key=timestamp_func)
    return relevant


def split_by_horizon(items: list[dict]) -> tuple[list[dict], list[dict]]:
    near, later = [], []
    for item in items:
        if remaining(item) <= TWO_WEEKS:
            near.append(item)
        else:
            later.append(item)
    return near, later


def labs_in_two_weeks() -> list[dict]:
    near, _later = split_by_horizon(upcoming_sorted())
    return near


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for block in text.split("\n\n"):
        piece = block + "\n\n"
        if current and len(current) + len(piece) > limit:
            chunks.append(current.rstrip())
            current = piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.rstrip())
    return chunks or [text[:limit]]


def labs_upcoming(limit: int | None = None) -> list[dict]:
    items = upcoming_sorted()
    if limit is not None:
        return items[:limit]
    return items


def get_message_parts(*, all_labs: bool = False, warnings: bool = True, limit: int | None = None) -> list[str]:
    if all_labs:
        items = upcoming_sorted()
    elif limit is not None:
        items = labs_upcoming(limit)
    else:
        items = labs_in_two_weeks()
    if not items:
        return ["нет сдач."]
    return chunk_text(add_items("", items, warnings=warnings))


def get_message_text() -> str:
    return get_message_parts()[0]


def ensure_skill(payload: dict, skill_id: str) -> None:
    skills = payload.setdefault("skills", [])
    if any(s.get("id") == skill_id for s in skills):
        return
    skills.append({"id": skill_id, "title": skill_id})


def parse_add_body(body: str) -> dict:
    body = (body or "").strip()
    if not body:
        raise ValueError("empty")
    parts = [p.strip() for p in body.split("|")] if "|" in body else [
        p.strip() for p in body.splitlines() if p.strip()
    ]
    while len(parts) < 7:
        parts.append("")
    name, time_raw, place, teacher, skills_raw, url, description = parts[:7]
    if len(parts) > 7:
        description = " | ".join(parts[6:]).strip() if "|" in body else "\n".join(parts[6:]).strip()
    if not name or not time_raw:
        raise ValueError("need name and time")
    skills = [normalize_skill(s) for s in skills_raw.replace(";", ",").split(",") if s.strip()]
    return {
        "name": name,
        "time": format_stored_time(parse_user_time(time_raw)),
        "place": place,
        "teacher": teacher,
        "skills": skills,
        "url": url,
        "description": description,
        "type": "",
    }


def is_allowed(user_id: int | None) -> bool:
    if not ADMIN_USER_IDS:
        return True
    return user_id in ADMIN_USER_IDS


class Board:
    def __init__(self):
        self.message_ids = [EDIT_MESSAGE_ID] if EDIT_MESSAGE_ID else []
        self.texts: list[str] = []

    def publish(self, force: bool = False) -> None:
        parts = get_message_parts()
        if not force and parts == self.texts and len(self.message_ids) == len(parts):
            return
        new_ids: list[int] = []
        try:
            for i, text in enumerate(parts):
                existing = self.message_ids[i] if i < len(self.message_ids) else 0
                if existing:
                    try:
                        edit_message(existing, text)
                        new_ids.append(existing)
                        continue
                    except TelegramException as e:
                        if e.error_code != 400:
                            logging.error(f"Failed to update board {existing}: {e}")
                            new_ids.append(existing)
                            continue
                        logging.warning(f"Board {existing} missing, sending a new one")
                new_ids.append(send_message(text))
            for extra_id in self.message_ids[len(parts):]:
                try:
                    delete_message(extra_id)
                except TelegramException:
                    pass
            self.message_ids = new_ids
            self.texts = parts
            logging.info(f"Board message ids: {self.message_ids}")
        except TelegramException as e:
            logging.error(f"Failed to publish board: {e}")


def cmd_add(body: str, board: Board) -> str:
    try:
        item = parse_add_body(body)
    except ValueError:
        return HELP_TEXT
    payload = load_deadlines_payload()
    for skill_id in item["skills"]:
        ensure_skill(payload, skill_id)
    payload.setdefault("deadlines", []).append(item)
    save_deadlines_payload(payload)
    board.publish(force=True)
    return (
        f"добавлено: <b>{escape(item['name'])}</b>\n"
        f"{escape(get_human_time(item['time']))}"
    )


def find_deadline(query: str) -> tuple[str | None, dict | None, dict]:
    payload = load_deadlines_payload()
    deadlines = payload.get("deadlines") or []
    q = (query or "").strip().lower()
    if not q:
        return ("укажите часть названия", None, payload)
    matches = [d for d in deadlines if q in (d.get("name") or "").lower()]
    if not matches:
        return ("ничего не нашёл с таким названием", None, payload)
    if len(matches) > 1:
        names = "\n".join(f"• {escape(d['name'])}" for d in matches[:10])
        return ("несколько совпадений, уточните:\n" + names, None, payload)
    return (None, matches[0], payload)


def parse_edit_fields(raw: str) -> dict:
    updates = {}
    chunks = [p.strip() for p in raw.split("|") if p.strip()]
    for chunk in chunks:
        if "=" in chunk:
            key, value = chunk.split("=", 1)
        elif ":" in chunk:
            key, value = chunk.split(":", 1)
        else:
            raise ValueError(chunk)
        field = EDIT_FIELD_ALIASES.get(key.strip().lower())
        if not field:
            raise ValueError(key)
        value = value.strip()
        if field == "time":
            updates[field] = format_stored_time(parse_user_time(value))
        elif field == "skills":
            updates[field] = [normalize_skill(s) for s in value.replace(";", ",").split(",") if s.strip()]
        else:
            updates[field] = value
    if not updates:
        raise ValueError("empty")
    return updates


def cmd_edit(body: str, board: Board) -> str:
    body = (body or "").strip()
    if "|" in body:
        query, rest = body.split("|", 1)
    elif "\n" in body:
        query, rest = body.split("\n", 1)
    else:
        query, rest = body, ""
    err, item, payload = find_deadline(query)
    if err:
        if not query:
            return (
                "изменить дедлайн:\n"
                "<code>/edit UML: ЛР 1 | time=15.09.2026 18:50 | place=ауд. 2335</code>\n"
                "поля: name, time, place, teacher, skills, url, description"
            )
        return err
    if not rest.strip():
        return (
            f"<b>{escape(item['name'])}</b>\n"
            f"{escape(get_human_time(item['time']))}\n"
            "поля: <code>name time place teacher skills url description</code>\n"
            "<code>/edit UML: ЛР 1 | time=15.09.2026 18:50</code>"
        )
    try:
        updates = parse_edit_fields(rest)
    except ValueError:
        return (
            "не понял поля. пример:\n"
            "<code>/edit UML: ЛР 1 | time=15.09.2026 18:50 | place=ауд. 2335</code>"
        )
    item.update(updates)
    for skill_id in deadline_skills(item):
        ensure_skill(payload, skill_id)
    save_deadlines_payload(payload)
    board.publish(force=True)
    return (
        f"изменено: <b>{escape(item['name'])}</b>\n"
        f"{escape(get_human_time(item['time']))}"
    )


def cmd_delete(body: str, board: Board) -> str:
    err, removed, payload = find_deadline(body)
    if err:
        if not (body or "").strip():
            return "укажите часть названия: <code>/delete Web: ЛР 1</code>"
        return err
    payload["deadlines"] = [d for d in payload.get("deadlines") or [] if d is not removed]
    save_deadlines_payload(payload)
    board.publish(force=True)
    return f"удалено: <b>{escape(removed['name'])}</b>"


def cmd_all() -> list[str]:
    return get_message_parts(all_labs=True, warnings=False)


def cmd_list() -> list[str]:
    return get_message_parts(warnings=False, limit=LIST_LIMIT)


def handle_command(command: str, body: str, board: Board) -> str | list[str] | None:
    command = command.lower()
    if command in ("help", "start"):
        return HELP_TEXT
    if command == "add":
        return cmd_add(body, board)
    if command == "edit":
        return cmd_edit(body, board)
    if command in ("delete", "del", "remove"):
        return cmd_delete(body, board)
    if command in ("list", "deadlines", "board"):
        return cmd_list()
    if command == "all":
        return cmd_all()
    return None


def handle_update(update: dict, board: Board) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id != MAIN_GROUP_ID:
        return
    user_id = (message.get("from") or {}).get("id")
    text = message.get("text") or message.get("caption") or ""
    match = CMD_RE.match(text.strip())
    if not match:
        return
    command = match.group(1).lower()
    mutating = command in ("add", "edit", "delete", "del", "remove")
    if mutating and not is_allowed(user_id):
        send_message("недостаточно прав", chat_id, message.get("message_id"))
        return
    reply = handle_command(command, (match.group(2) or "").strip(), board)
    if not reply:
        return
    chunks = reply if isinstance(reply, list) else [reply]
    reply_to = message.get("message_id")
    for chunk in chunks:
        send_message(chunk, chat_id, reply_to)
        reply_to = None


def setup_bot() -> None:
    try:
        telegram_request("deleteWebhook", {"drop_pending_updates": False})
    except TelegramException as e:
        logging.warning(f"deleteWebhook: {e}")
    try:
        telegram_request("setMyCommands", {
            "commands": [
                {"command": "all", "description": "Все лабы"},
                {"command": "list", "description": "Ближайшие 5 лаб"},
                {"command": "add", "description": "Добавить дедлайн"},
                {"command": "edit", "description": "Изменить дедлайн"},
                {"command": "delete", "description": "Удалить дедлайн"},
                {"command": "help", "description": "Справка"},
            ]
        })
    except TelegramException as e:
        logging.warning(f"setMyCommands: {e}")


def main() -> None:
    setup_bot()
    board = Board()
    board.publish(force=True)
    offset = 0
    last_refresh = time.time()
    logging.info("Polling Telegram for commands")

    while True:
        try:
            data = telegram_request(
                "getUpdates",
                {"timeout": 25, "offset": offset, "allowed_updates": ["message"]},
                timeout=40,
            )
            for update in data.get("result") or []:
                offset = update["update_id"] + 1
                try:
                    handle_update(update, board)
                except Exception as e:
                    logging.error(f"Failed to handle update: {e}")
        except TelegramException as e:
            if e.error_code == 429:
                logging.warning("Rate limited, waiting 30s")
                time.sleep(30)
            else:
                logging.error(f"getUpdates failed: {e}")
                time.sleep(5)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(5)

        now = time.time()
        if now - last_refresh >= REFRESH_SECONDS:
            board.publish()
            last_refresh = now


if __name__ == '__main__':
    main()
