# Smart Calendar Agent

A Streamlit app that matches you with the best experts for your task using Claude (Anthropic) and suggests meeting times from your Google Calendar.

## How It Works

1. **Expert Matching** — Describe your task and Claude semantically scores and ranks experts from a CSV dataset.
2. **Calendar Integration** — Connects to Google Calendar via OAuth 2.0, computes your free slots, and suggests meeting times with top-ranked experts.

## Prerequisites

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/)
- (Optional) Google Cloud OAuth credentials for Calendar integration

## Setup

```bash
# Clone and enter the project
cd smart_calendar_agent

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Google Calendar (Optional)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Calendar API**.
3. Create OAuth 2.0 credentials (Desktop app) and download `credentials.json`.
4. Place `credentials.json` in the project root.

## Running the App

```bash
streamlit run src/app.py
```

Opens at [http://localhost:8501](http://localhost:8501).

### Usage

1. Enter your Anthropic API key in the sidebar (or set it in `.env`).
2. Type a task or project description in the main text area.
3. Optionally add specific preferences or requirements.
4. Click **Find Experts**.
5. View ranked expert cards with relevance scores and reasoning.
6. If Google Calendar is connected, suggested meeting times appear on each card.

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests use mocks — no API keys or Google credentials needed.

## Project Structure

```
smart_calendar_agent/
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── experts.csv              # Sample expert profiles
├── src/
│   ├── app.py                   # Streamlit entry point
│   ├── calendar_client.py       # Google Calendar OAuth + availability
│   ├── expert_loader.py         # CSV loading and parsing
│   ├── matcher.py               # Claude-based expert matching
│   └── models.py                # Data classes (Expert, TimeSlot, MatchResult)
└── tests/
    ├── test_models.py
    ├── test_expert_loader.py
    ├── test_matcher.py
    └── test_calendar_client.py
```

## Configuration

| Setting | Default | Where |
|---|---|---|
| Anthropic API key | — | `.env` or sidebar |
| Working hours | 9am–5pm | Sidebar sliders |
| Days ahead | 7 | Sidebar slider |
| Timezone | America/New_York | Sidebar dropdown |
| Min slot duration | 30 min | Code default |
| Expert data | `data/experts.csv` | Sidebar CSV upload or default |
