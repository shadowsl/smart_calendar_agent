from __future__ import annotations

import json

import anthropic

from models import Expert, MatchResult

SYSTEM_PROMPT = """\
You are an expert-matching assistant. Given a user's task description and \
preferences, score each candidate expert on relevance (0-100) and provide \
brief reasoning. Return ONLY valid JSON — no markdown fences, no extra text.

Return a JSON array sorted by relevance (highest first):
[
  {
    "expert_name": "...",
    "relevance_score": 85,
    "reasoning": "One-sentence explanation"
  }
]
"""


def match_experts(
    task_description: str,
    preferences: str,
    experts: list[Expert],
    api_key: str,
    model: str = "claude-sonnet-4-6",
) -> list[MatchResult]:
    """Use Claude to semantically rank experts against the user's task."""
    expert_profiles = "\n\n".join(
        f"**{e.name}** ({e.domain})\n"
        f"Keywords: {', '.join(e.expertise_keywords)}\n"
        f"Bio: {e.bio}"
        for e in experts
    )

    user_message = (
        f"## Task\n{task_description}\n\n"
        f"## Preferences\n{preferences or 'None specified'}\n\n"
        f"## Candidate Experts\n{expert_profiles}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    scored = json.loads(raw)

    experts_by_name = {e.name: e for e in experts}

    results: list[MatchResult] = []
    for entry in scored:
        name = entry["expert_name"]
        expert = experts_by_name.get(name)
        if not expert:
            continue
        results.append(
            MatchResult(
                expert=expert,
                relevance_score=int(entry["relevance_score"]),
                reasoning=entry["reasoning"],
            )
        )

    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results
