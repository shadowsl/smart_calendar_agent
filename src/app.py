import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
import os

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from expert_loader import load_experts
from matcher import match_experts
from models import Expert, TimeSlot

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

st.set_page_config(page_title="Smart Calendar Agent", page_icon="📅", layout="wide")
st.title("📅 Smart Calendar Agent")
st.caption("Find the best experts for your task and schedule meetings")

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
    )

    st.divider()
    st.subheader("Google Calendar")

    calendar_connected = False
    free_slots: list[TimeSlot] = []

    timezone = st.selectbox(
        "Timezone",
        ["America/New_York", "America/Chicago", "America/Denver",
         "America/Los_Angeles", "Europe/London", "Europe/Berlin",
         "Asia/Tokyo", "UTC"],
        index=0,
    )

    work_start = st.slider("Work day starts", 6, 12, 9)
    work_end = st.slider("Work day ends", 13, 22, 17)
    days_ahead = st.slider("Days to look ahead", 1, 14, 7)

    credentials_path = Path(__file__).resolve().parent.parent / "credentials.json"

    if credentials_path.exists():
        if st.button("Connect Google Calendar"):
            try:
                from calendar_client import authenticate, get_free_slots

                creds = authenticate(credentials_path)
                free_slots = get_free_slots(
                    creds,
                    days_ahead=days_ahead,
                    working_hours=(work_start, work_end),
                    timezone=timezone,
                )
                st.session_state["free_slots"] = free_slots
                calendar_connected = True
                st.success(f"Connected! Found {len(free_slots)} free slots.")
            except Exception as e:
                st.error(f"Calendar auth failed: {e}")
    else:
        st.info("Place `credentials.json` in the project root to enable Calendar.")

    if "free_slots" in st.session_state:
        free_slots = st.session_state["free_slots"]
        calendar_connected = True

    st.divider()
    st.subheader("Expert Data")

    uploaded = st.file_uploader("Upload experts CSV (optional)", type=["csv"])

# ── Load experts ─────────────────────────────────────────────────────────────

try:
    if uploaded:
        import tempfile, shutil

        tmp = Path(tempfile.mktemp(suffix=".csv"))
        tmp.write_bytes(uploaded.getvalue())
        experts = load_experts(tmp)
        tmp.unlink()
    else:
        experts = load_experts()
    st.sidebar.success(f"Loaded {len(experts)} experts")
except Exception as e:
    st.error(f"Failed to load experts: {e}")
    experts = []

# ── Main area ────────────────────────────────────────────────────────────────

task = st.text_area(
    "Describe your task or project",
    placeholder="e.g., We need to migrate our monolith to microservices on Kubernetes and set up a CI/CD pipeline...",
    height=120,
)

preferences = st.text_input(
    "Any specific preferences or requirements?",
    placeholder="e.g., Must have experience with AWS, prefer someone who can start this week",
)

if st.button("🔍 Find Experts", type="primary", disabled=not api_key):
    if not task.strip():
        st.warning("Please describe your task first.")
    elif not experts:
        st.warning("No experts loaded. Upload a CSV or use the default.")
    else:
        with st.spinner("Matching experts with Claude..."):
            try:
                results = match_experts(task, preferences, experts, api_key)
            except Exception as e:
                st.error(f"Matching failed: {e}")
                results = []

        if not results:
            st.info("No matching experts found.")
        else:
            # Assign up to 3 free slots to top experts
            slot_idx = 0
            for r in results:
                slots_for_expert: list[TimeSlot] = []
                if free_slots:
                    for _ in range(3):
                        if slot_idx < len(free_slots):
                            slots_for_expert.append(free_slots[slot_idx])
                            slot_idx += 1
                r.suggested_slots = slots_for_expert

            st.subheader("Recommended Experts")

            for r in results:
                score_color = (
                    "🟢" if r.relevance_score >= 70
                    else "🟡" if r.relevance_score >= 40
                    else "🔴"
                )

                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {r.expert.name}")
                        st.markdown(f"**Domain:** {r.expert.domain}  ")
                        st.markdown(
                            f"**Keywords:** {', '.join(r.expert.expertise_keywords)}"
                        )
                        st.markdown(f"*{r.reasoning}*")
                    with col2:
                        st.metric("Relevance", f"{r.relevance_score}/100")
                        st.markdown(f"{score_color} Match")

                    if r.suggested_slots:
                        st.markdown("**Suggested meeting times:**")
                        for slot in r.suggested_slots:
                            st.markdown(f"- {slot}")
                    elif calendar_connected:
                        st.caption("No free slots available for this expert.")
                    else:
                        st.caption(
                            "Connect Google Calendar to see available meeting times."
                        )

if not api_key:
    st.info("Enter your Anthropic API key in the sidebar to get started.")
