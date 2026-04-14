from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Expert:
    name: str
    email: str
    domain: str
    expertise_keywords: list[str]
    bio: str
    availability_notes: str = ""


@dataclass
class TimeSlot:
    start: datetime
    end: datetime

    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)

    def __str__(self) -> str:
        fmt = "%a %b %d, %I:%M %p"
        return f"{self.start.strftime(fmt)} – {self.end.strftime(fmt)}"


@dataclass
class MatchResult:
    expert: Expert
    relevance_score: int  # 0-100
    reasoning: str
    suggested_slots: list[TimeSlot] = field(default_factory=list)
