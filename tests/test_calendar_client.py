from datetime import datetime, timedelta, time
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from models import TimeSlot
from calendar_client import get_busy_slots, get_free_slots


TZ = ZoneInfo("America/New_York")


def _make_event(start_iso, end_iso):
    """Helper to create a Google Calendar event dict."""
    return {
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }


def _make_allday_event(date_str):
    return {
        "start": {"date": date_str},
        "end": {"date": date_str},
    }


def _mock_calendar_service(events):
    """Create a mock Google Calendar service returning the given events."""
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {
        "items": events,
    }
    return mock_service


class TestGetBusySlots:
    @patch("calendar_client.build")
    def test_parses_timed_events(self, mock_build):
        events = [
            _make_event("2026-04-13T10:00:00-04:00", "2026-04-13T11:00:00-04:00"),
            _make_event("2026-04-13T14:00:00-04:00", "2026-04-13T15:30:00-04:00"),
        ]
        mock_build.return_value = _mock_calendar_service(events)

        creds = MagicMock()
        slots = get_busy_slots(creds, days_ahead=7, timezone="America/New_York")

        assert len(slots) == 2
        assert slots[0].duration_minutes() == 60
        assert slots[1].duration_minutes() == 90

    @patch("calendar_client.build")
    def test_parses_allday_event(self, mock_build):
        events = [_make_allday_event("2026-04-14")]
        mock_build.return_value = _mock_calendar_service(events)

        creds = MagicMock()
        slots = get_busy_slots(creds, days_ahead=7, timezone="America/New_York")

        assert len(slots) == 1
        assert slots[0].duration_minutes() == 1440  # full day

    @patch("calendar_client.build")
    def test_empty_calendar(self, mock_build):
        mock_build.return_value = _mock_calendar_service([])

        creds = MagicMock()
        slots = get_busy_slots(creds)
        assert slots == []


class TestGetFreeSlots:
    @patch("calendar_client.datetime")
    @patch("calendar_client.get_busy_slots")
    def test_full_day_free_when_no_events(self, mock_busy, mock_dt):
        # Fix "now" to morning of April 13
        fixed_now = datetime(2026, 4, 13, 8, 0, tzinfo=TZ)
        mock_dt.now.return_value = fixed_now
        mock_dt.combine = datetime.combine
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mock_busy.return_value = []

        creds = MagicMock()
        free = get_free_slots(
            creds, days_ahead=1, working_hours=(9, 17), timezone="America/New_York"
        )

        assert len(free) == 1
        assert free[0].start == datetime(2026, 4, 13, 9, 0, tzinfo=TZ)
        assert free[0].end == datetime(2026, 4, 13, 17, 0, tzinfo=TZ)
        assert free[0].duration_minutes() == 480

    @patch("calendar_client.datetime")
    @patch("calendar_client.get_busy_slots")
    def test_single_meeting_splits_day(self, mock_busy, mock_dt):
        fixed_now = datetime(2026, 4, 13, 8, 0, tzinfo=TZ)
        mock_dt.now.return_value = fixed_now
        mock_dt.combine = datetime.combine
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        mock_busy.return_value = [
            TimeSlot(
                start=datetime(2026, 4, 13, 12, 0, tzinfo=TZ),
                end=datetime(2026, 4, 13, 13, 0, tzinfo=TZ),
            ),
        ]

        creds = MagicMock()
        free = get_free_slots(
            creds, days_ahead=1, working_hours=(9, 17), timezone="America/New_York"
        )

        assert len(free) == 2
        # Morning block: 9:00 - 12:00
        assert free[0].start.hour == 9
        assert free[0].end.hour == 12
        # Afternoon block: 13:00 - 17:00
        assert free[1].start.hour == 13
        assert free[1].end.hour == 17

    @patch("calendar_client.datetime")
    @patch("calendar_client.get_busy_slots")
    def test_small_gaps_filtered_by_min_slot(self, mock_busy, mock_dt):
        fixed_now = datetime(2026, 4, 13, 8, 0, tzinfo=TZ)
        mock_dt.now.return_value = fixed_now
        mock_dt.combine = datetime.combine
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # Two meetings with only 15 min gap between them
        mock_busy.return_value = [
            TimeSlot(
                start=datetime(2026, 4, 13, 9, 0, tzinfo=TZ),
                end=datetime(2026, 4, 13, 10, 0, tzinfo=TZ),
            ),
            TimeSlot(
                start=datetime(2026, 4, 13, 10, 15, tzinfo=TZ),
                end=datetime(2026, 4, 13, 17, 0, tzinfo=TZ),
            ),
        ]

        creds = MagicMock()
        free = get_free_slots(
            creds,
            days_ahead=1,
            working_hours=(9, 17),
            timezone="America/New_York",
            min_slot_minutes=30,
        )

        # The 15-min gap should be filtered out
        assert len(free) == 0

    @patch("calendar_client.datetime")
    @patch("calendar_client.get_busy_slots")
    def test_multiple_days(self, mock_busy, mock_dt):
        fixed_now = datetime(2026, 4, 13, 8, 0, tzinfo=TZ)
        mock_dt.now.return_value = fixed_now
        mock_dt.combine = datetime.combine
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mock_busy.return_value = []

        creds = MagicMock()
        free = get_free_slots(
            creds, days_ahead=3, working_hours=(9, 17), timezone="America/New_York"
        )

        assert len(free) == 3  # One full block per day

    @patch("calendar_client.datetime")
    @patch("calendar_client.get_busy_slots")
    def test_past_hours_skipped(self, mock_busy, mock_dt):
        # "now" is 2pm — morning hours should be skipped
        fixed_now = datetime(2026, 4, 13, 14, 0, tzinfo=TZ)
        mock_dt.now.return_value = fixed_now
        mock_dt.combine = datetime.combine
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mock_busy.return_value = []

        creds = MagicMock()
        free = get_free_slots(
            creds, days_ahead=1, working_hours=(9, 17), timezone="America/New_York"
        )

        assert len(free) == 1
        assert free[0].start.hour == 14
        assert free[0].end.hour == 17
