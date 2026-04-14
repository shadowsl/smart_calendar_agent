import tempfile
from pathlib import Path

import pytest

from expert_loader import load_experts


class TestLoadExperts:
    def test_load_default_csv(self):
        experts = load_experts()
        assert len(experts) == 8
        names = [e.name for e in experts]
        assert "Alice Chen" in names
        assert "Henry Adams" in names

    def test_expert_fields_populated(self):
        experts = load_experts()
        alice = next(e for e in experts if e.name == "Alice Chen")
        assert alice.email == "alice@example.com"
        assert alice.domain == "Machine Learning"
        assert "deep learning" in alice.expertise_keywords
        assert "NLP" in alice.expertise_keywords
        assert len(alice.bio) > 0

    def test_keywords_parsed_from_semicolons(self):
        experts = load_experts()
        bob = next(e for e in experts if e.name == "Bob Martinez")
        assert "penetration testing" in bob.expertise_keywords
        assert "cloud security" in bob.expertise_keywords
        assert len(bob.expertise_keywords) == 4

    def test_availability_notes_loaded(self):
        experts = load_experts()
        alice = next(e for e in experts if e.name == "Alice Chen")
        assert "morning" in alice.availability_notes.lower()

    def test_custom_csv_path(self):
        csv_content = (
            "name,email,domain,expertise_keywords,bio\n"
            "Test User,test@test.com,Testing,unit;integration,Tester\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(csv_content)
            f.flush()
            experts = load_experts(f.name)

        assert len(experts) == 1
        assert experts[0].name == "Test User"
        assert experts[0].expertise_keywords == ["unit", "integration"]
        Path(f.name).unlink()

    def test_missing_columns_raises(self):
        csv_content = "name,email\nAlice,alice@test.com\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(csv_content)
            f.flush()
            with pytest.raises(ValueError, match="missing required columns"):
                load_experts(f.name)
        Path(f.name).unlink()

    def test_missing_availability_notes_column(self):
        csv_content = (
            "name,email,domain,expertise_keywords,bio\n"
            "X,x@x.com,D,k1;k2,A bio\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(csv_content)
            f.flush()
            experts = load_experts(f.name)

        assert experts[0].availability_notes == "nan" or experts[0].availability_notes == ""
        Path(f.name).unlink()
