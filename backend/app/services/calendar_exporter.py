from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

def _format_ics_date(dt: datetime) -> str:
    """Formats datetime into UTC ICS format: YYYYMMDDTHHMMSSZ."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y%m%dT%H%M%SZ")

def generate_ics_calendar(events: List[Dict[str, Any]], cal_name: str = "AutoApply CRM Calendar") -> str:
    """Generates standard RFC 5545 iCalendar string for application events."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AutoApply//Interview CRM Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        f"X-WR-TIMEZONE:UTC",
    ]

    for ev in events:
        uid = ev.get("uid", f"autoapply-{int(datetime.now().timestamp())}")
        summary = ev.get("summary", "Application Event")
        description = ev.get("description", "")
        start_dt = ev.get("start_date") or datetime.now(timezone.utc)
        duration_hours = ev.get("duration_hours", 1)
        end_dt = ev.get("end_date") or (start_dt + timedelta(hours=duration_hours))
        location = ev.get("location", "Video Call / Remote")

        now_str = _format_ics_date(datetime.now(timezone.utc))
        start_str = _format_ics_date(start_dt)
        end_str = _format_ics_date(end_dt)

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description.replace(chr(10), '\\n')}",
            f"LOCATION:{location}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
