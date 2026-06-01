"""Telegram Bot notification service.

All public functions are no-ops when TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID
are not configured. Set both env vars to enable.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_LOGIN_COOLDOWN_SECONDS = 1800  # suppress duplicate login alerts within 30 min
_login_last_seen: dict[str, float] = {}


def _credentials() -> tuple[str, str]:
    s = get_settings()
    return s.telegram_bot_token, s.telegram_chat_id


def is_configured() -> bool:
    token, chat_id = _credentials()
    return bool(token and chat_id)


async def send_message(text: str) -> bool:
    token, chat_id = _credentials()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            if not resp.is_success:
                logger.warning("Telegram send failed: %s — %s", resp.status_code, resp.text)
                return False
            return True
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False


async def notify_login(doctor) -> None:
    if not doctor or doctor.is_test:
        return
    key = str(doctor.uuid)
    now = time.monotonic()
    if now - _login_last_seen.get(key, 0) < _LOGIN_COOLDOWN_SECONDS:
        return
    _login_last_seen[key] = now

    from zoneinfo import ZoneInfo
    display = doctor.full_name or doctor.username
    tz = ZoneInfo(get_settings().scheduler_timezone or "UTC")
    ts = datetime.now(tz).strftime("%H:%M | %d %b %Y")
    await send_message(f"🔔 <b>{display}</b> ({doctor.username}) signed in\n⏰ {ts}")


async def build_report(db) -> str:
    """Return the formatted 12h report text without sending it."""
    from zoneinfo import ZoneInfo
    from sqlalchemy import text as sqlt

    tz = ZoneInfo(get_settings().scheduler_timezone or "UTC")
    now = datetime.now(tz)
    since = now - timedelta(hours=12)

    rows = db.execute(
        sqlt("""
            SELECT
                d.full_name,
                d.username,
                ds.name        AS dataset_name,
                imgs.image_set_name,
                imgs.index
            FROM image_set_evaluations ise
            JOIN annotation_sessions   ans  ON ans.annotation_session_uuid = ise.annotation_session_uuid
            JOIN doctors               d    ON d.uuid   = ans.doctor_uuid
            JOIN image_sets            imgs ON imgs.uuid = ise.image_set_uuid
            JOIN datasets              ds   ON ds.dataset_uuid = imgs.dataset_uuid
            WHERE ans.submitted_at >= :since
              AND d.is_test = FALSE
            ORDER BY d.full_name, ds.name, imgs.index
        """),
        {"since": since},
    ).fetchall()

    progress = db.execute(
        sqlt("""
            SELECT
                ds.name,
                COUNT(DISTINCT imgs.uuid) AS total,
                COUNT(DISTINCT CASE
                    WHEN d.is_test = FALSE AND ise.id IS NOT NULL
                    THEN imgs.uuid END) AS done
            FROM datasets  ds
            JOIN image_sets imgs ON imgs.dataset_uuid = ds.dataset_uuid
            LEFT JOIN image_set_evaluations ise ON ise.image_set_uuid = imgs.uuid
            LEFT JOIN annotation_sessions   ans ON ans.annotation_session_uuid = ise.annotation_session_uuid
            LEFT JOIN doctors               d   ON d.uuid = ans.doctor_uuid
            GROUP BY ds.dataset_uuid, ds.name
            ORDER BY ds.name
        """)
    ).fetchall()

    time_str = now.strftime("%H:%M | %d %b %Y")
    since_str = since.strftime("%H:%M")
    since_day = "today" if since.date() == now.date() else "yesterday"

    lines = ["📊 <b>MedFabric — 12h Report</b>", f"🕘 {time_str}", ""]

    if not rows:
        lines.append(f"💤 No new submissions since {since_str} {since_day}.")
    else:
        n = len(rows)
        lines.append(
            f"✅ <b>{n}</b> new submission{'s' if n != 1 else ''} since {since_str} {since_day}:"
        )
        lines.append("")
        by_doctor: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        doctor_label: dict[str, str] = {}
        for r in rows:
            doctor_label[r.username] = f"{r.full_name or r.username} ({r.username})"
            by_doctor[r.username][r.dataset_name].append(
                f"• Set #{r.index} — {r.image_set_name}"
            )
        for uname, datasets in by_doctor.items():
            lines.append(f"<b>{doctor_label[uname]}</b>")
            for ds_name, sets in datasets.items():
                lines.append(f"  📁 {ds_name}")
                for s in sets:
                    lines.append(f"    {s}")
            lines.append("")

    lines += ["━━━━━━━━━━━━━━━", "📈 <b>Dataset Progress</b>"]
    for r in progress:
        pct = round(100 * r.done / r.total) if r.total else 0
        lines.append(f"  {r.name}: {r.done}/{r.total} ({pct}%)")

    return "\n".join(lines)


async def send_12h_report(db) -> None:
    text = await build_report(db)
    await send_message(text)
