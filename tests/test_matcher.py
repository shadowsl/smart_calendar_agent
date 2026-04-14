import json
from unittest.mock import MagicMock, patch

from models import Expert, MatchResult
from matcher import match_experts


def _make_experts():
    return [
        Expert("Alice", "a@b.com", "ML", ["NLP", "transformers"], "ML engineer"),
        Expert("Bob", "b@b.com", "Security", ["pentesting"], "Security architect"),
    ]


def _mock_claude_response(scored_json):
    """Create a mock Anthropic response with the given JSON payload."""
    content_block = MagicMock()
    content_block.text = json.dumps(scored_json)
    response = MagicMock()
    response.content = [content_block]
    return response


class TestMatchExperts:
    @patch("matcher.anthropic.Anthropic")
    def test_returns_ranked_results(self, mock_anthropic_cls):
        experts = _make_experts()
        scored = [
            {"expert_name": "Alice", "relevance_score": 90, "reasoning": "NLP expert"},
            {"expert_name": "Bob", "relevance_score": 40, "reasoning": "Less relevant"},
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(scored)
        mock_anthropic_cls.return_value = mock_client

        results = match_experts("Build an NLP pipeline", "", experts, "fake-key")

        assert len(results) == 2
        assert results[0].expert.name == "Alice"
        assert results[0].relevance_score == 90
        assert results[1].expert.name == "Bob"
        assert results[1].relevance_score == 40

    @patch("matcher.anthropic.Anthropic")
    def test_results_sorted_descending(self, mock_anthropic_cls):
        experts = _make_experts()
        # Return in ascending order — should be re-sorted
        scored = [
            {"expert_name": "Bob", "relevance_score": 80, "reasoning": "Good"},
            {"expert_name": "Alice", "relevance_score": 60, "reasoning": "OK"},
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(scored)
        mock_anthropic_cls.return_value = mock_client

        results = match_experts("Security audit", "", experts, "fake-key")

        assert results[0].relevance_score >= results[1].relevance_score

    @patch("matcher.anthropic.Anthropic")
    def test_unknown_expert_name_skipped(self, mock_anthropic_cls):
        experts = _make_experts()
        scored = [
            {"expert_name": "Alice", "relevance_score": 90, "reasoning": "Match"},
            {"expert_name": "Unknown", "relevance_score": 50, "reasoning": "???"},
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(scored)
        mock_anthropic_cls.return_value = mock_client

        results = match_experts("task", "", experts, "fake-key")

        assert len(results) == 1
        assert results[0].expert.name == "Alice"

    @patch("matcher.anthropic.Anthropic")
    def test_empty_response(self, mock_anthropic_cls):
        experts = _make_experts()

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response([])
        mock_anthropic_cls.return_value = mock_client

        results = match_experts("task", "", experts, "fake-key")
        assert results == []

    @patch("matcher.anthropic.Anthropic")
    def test_api_called_with_correct_params(self, mock_anthropic_cls):
        experts = _make_experts()
        scored = [
            {"expert_name": "Alice", "relevance_score": 70, "reasoning": "OK"},
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(scored)
        mock_anthropic_cls.return_value = mock_client

        match_experts("Build NLP", "prefer NLP", experts, "test-key")

        mock_anthropic_cls.assert_called_once_with(api_key="test-key")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs["max_tokens"] == 1024
        assert "Build NLP" in call_kwargs["messages"][0]["content"]
        assert "prefer NLP" in call_kwargs["messages"][0]["content"]

    @patch("matcher.anthropic.Anthropic")
    def test_result_is_match_result_type(self, mock_anthropic_cls):
        experts = _make_experts()
        scored = [
            {"expert_name": "Alice", "relevance_score": 80, "reasoning": "Good"},
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(scored)
        mock_anthropic_cls.return_value = mock_client

        results = match_experts("task", "", experts, "fake-key")

        assert isinstance(results[0], MatchResult)
        assert isinstance(results[0].expert, Expert)
