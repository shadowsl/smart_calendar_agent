from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models import Expert, TimeSlot, MatchResult


class TestExpert:
    def test_creation(self):
        expert = Expert(
            name="Alice",
            email="alice@example.com",
            domain="ML",
            expertise_keywords=["NLP", "transformers"],
            bio="ML engineer",
        )
        assert expert.name == "Alice"
        assert expert.email == "alice@example.com"
        assert expert.expertise_keywords == ["NLP", "transformers"]
        assert expert.availability_notes == ""

    def test_availability_notes_default(self):
        expert = Expert("A", "a@b.com", "D", [], "bio")
        assert expert.availability_notes == ""

    def test_availability_notes_set(self):
        expert = Expert("A", "a@b.com", "D", [], "bio", "mornings only")
        assert expert.availability_notes == "mornings only"


class TestTimeSlot:
    def test_duration_minutes(self):
        start = datetime(2026, 4, 13, 9, 0)
        end = datetime(2026, 4, 13, 10, 30)
        slot = TimeSlot(start=start, end=end)
        assert slot.duration_minutes() == 90

    def test_duration_zero(self):
        t = datetime(2026, 4, 13, 9, 0)
        slot = TimeSlot(start=t, end=t)
        assert slot.duration_minutes() == 0

    def test_str_format(self):
        start = datetime(2026, 4, 13, 9, 0)
        end = datetime(2026, 4, 13, 10, 0)
        slot = TimeSlot(start=start, end=end)
        s = str(slot)
        assert "09:00 AM" in s
        assert "10:00 AM" in s
        assert "–" in s

    def test_duration_multiday(self):
        start = datetime(2026, 4, 13, 9, 0)
        end = datetime(2026, 4, 14, 9, 0)
        slot = TimeSlot(start=start, end=end)
        assert slot.duration_minutes() == 1440


class TestMatchResult:
    def _make_expert(self):
        return Expert("Alice", "a@b.com", "ML", ["NLP"], "bio")

    def test_creation(self):
        expert = self._make_expert()
        result = MatchResult(expert=expert, relevance_score=85, reasoning="Good fit")
        assert result.relevance_score == 85
        assert result.reasoning == "Good fit"
        assert result.suggested_slots == []

    def test_with_slots(self):
        expert = self._make_expert()
        slot = TimeSlot(
            start=datetime(2026, 4, 13, 9, 0),
            end=datetime(2026, 4, 13, 10, 0),
        )
        result = MatchResult(
            expert=expert,
            relevance_score=90,
            reasoning="Great match",
            suggested_slots=[slot],
        )
        assert len(result.suggested_slots) == 1
        assert result.suggested_slots[0].duration_minutes() == 60
