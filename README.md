# Deadline reminder bot for M3313 — dead inside M3313

Telegram bot [`@m3313_deadinside_bot`](https://t.me/m3313_deadinside_bot) for the M3313 group.

Each deadline is shown with **time**, **place**, **teacher**, **skills**, **link**, and a **short description**.

The group board is replaced (old messages deleted, new ones sent) on `/refresh`, when warning levels change, or every day at 12:00 MSK.

# Commands (in the group chat)

```
/add Название | 16.09.2026 15:30 | ауд. 2414 | Папикян С.С. | frontend | https://… | коротко что сдавать
/edit UML: ЛР 1 | time=15.09.2026 18:50 | place=ауд. 2335
/delete Web: ЛР 1
/refresh
/list
/all
/help
```

`/list` shows the next 5 labs. `/all` shows every remaining lab. Fields after the name in `/add` are optional except the date. Default time is `23:59` MSK. The bot must be a member of the group; commands work even with group privacy mode on.

# Secrets

`TOKEN` and `MAIN_GROUP_ID` come from environment / GitHub Actions secrets. Optional: `ADMIN_USER_IDS` (comma-separated Telegram user ids; if empty, anyone in the group can `/add`, `/edit`, and `/delete`), `ADD_CALENDAR_LINK`, `DEADLINES_PATH`, `BOARD_PATH`, `EDIT_MESSAGE_ID` (extra message id to delete on the first board replace).

# Deadlines file

[`DEADLINES.json`](DEADLINES.json) is the source of truth and is updated when someone uses `/add`, `/edit`, or `/delete`. Mount it as a volume so chat edits survive container rebuilds. Board message ids are stored under `board-data/`.

# How to run

```bash
cp .env.sample .env
docker compose up --build
```

On push to `main`, GitHub Actions writes `.env` from `TOKEN` and `MAIN_GROUP_ID` and deploys.
