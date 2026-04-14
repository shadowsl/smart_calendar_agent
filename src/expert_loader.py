from __future__ import annotations

from pathlib import Path

import pandas as pd

from models import Expert

REQUIRED_COLUMNS = {"name", "email", "domain", "expertise_keywords", "bio"}
DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "experts.csv"


def load_experts(csv_path: Path | str | None = None) -> list[Expert]:
    """Load expert profiles from a CSV file into Expert objects."""
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    df = pd.read_csv(path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    experts: list[Expert] = []
    for _, row in df.iterrows():
        keywords_raw = row.get("expertise_keywords", "")
        keywords = [k.strip() for k in str(keywords_raw).split(";") if k.strip()]

        experts.append(
            Expert(
                name=str(row["name"]),
                email=str(row["email"]),
                domain=str(row["domain"]),
                expertise_keywords=keywords,
                bio=str(row["bio"]),
                availability_notes=str(row.get("availability_notes", "")),
            )
        )
    return experts
