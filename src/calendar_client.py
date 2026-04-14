from __future__ import annotations

from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from models import TimeSlot

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json"
CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json"


def authenticate(credentials_path: Path | None = None) -> Credentials:
    """Run OAuth 2.0 flow and return valid credentials, caching in token.json."""
    creds_file = credentials_path or CREDENTIALS_PATH
    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    return creds


def get_busy_slots(
    creds: Credentials,
    days_ahead: int = 7,
    timezone: str = "America/New_York",
) -> list[TimeSlot]:
    """Fetch busy time slots from the user's primary Google Calendar."""
    service = build("calendar", "v3", credentials=creds)
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    busy: list[TimeSlot] = []
    for event in events_result.get("items", []):
        start_raw = event["start"].get("dateTime")
        end_raw = event["end"].get("dateTime")
        if not start_raw or not end_raw:
            # All-day event — treat as full-day busy
            date_str = event["start"].get("date", "")
            if date_str:
                day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
                busy.append(TimeSlot(start=day, end=day + timedelta(days=1)))
            continue
        busy.append(
            TimeSlot(
                start=datetime.fromisoformat(start_raw),
                end=datetime.fromisoformat(end_raw),
            )
        )
    return busy


def get_free_slots(
    creds: Credentials,
    days_ahead: int = 7,
    working_hours: tuple[int, int] = (9, 17),
    timezone: str = "America/New_York",
    min_slot_minutes: int = 30,
) -> list[TimeSlot]:
    """Compute free time slots by subtracting busy periods from working hours."""
    tz = ZoneInfo(timezone)
    busy = get_busy_slots(creds, days_ahead, timezone)
    now = datetime.now(tz)

    free: list[TimeSlot] = []
    for day_offset in range(days_ahead):
        day = (now + timedelta(days=day_offset)).date()
        work_start = datetime.combine(day, time(working_hours[0]), tzinfo=tz)
        work_end = datetime.combine(day, time(working_hours[1]), tzinfo=tz)

        # Skip times in the past
        if work_end <= now:
            continue
        if work_start < now:
            work_start = now.replace(second=0, microsecond=0)

        # Collect busy periods that overlap this working day
        day_busy = sorted(
            [
                TimeSlot(start=max(b.start, work_start), end=min(b.end, work_end))
                for b in busy
                if b.start < work_end and b.end > work_start
            ],
            key=lambda s: s.start,
        )

        cursor = work_start
        for b in day_busy:
            if b.start > cursor:
                slot = TimeSlot(start=cursor, end=b.start)
                if slot.duration_minutes() >= min_slot_minutes:
                    free.append(slot)
            cursor = max(cursor, b.end)

        if cursor < work_end:
            slot = TimeSlot(start=cursor, end=work_end)
            if slot.duration_minutes() >= min_slot_minutes:
                free.append(slot)

    return free
