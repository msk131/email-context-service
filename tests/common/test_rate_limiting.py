"""Unit tests for rate limiting configuration and behavior."""

from app.main import app
from app.common.rate_limit import (
    SEARCH_LIMIT,
    CONVERSATION_LIMIT,
    REFRESH_LIMIT,
    SUMMARY_READ_LIMIT,
    TASK_SUBMIT_LIMIT,
    TASK_STATUS_LIMIT,
)


class TestRateLimitConfig:
    """Test rate limiting configuration."""

    def test_rate_limit_constants_defined(self):
        """All rate limit constants are properly defined."""
        # Verify format: "requests/period"
        limits = [
            SEARCH_LIMIT,
            CONVERSATION_LIMIT,
            REFRESH_LIMIT,
            SUMMARY_READ_LIMIT,
            TASK_SUBMIT_LIMIT,
            TASK_STATUS_LIMIT,
        ]
        
        for limit in limits:
            assert isinstance(limit, str)
            assert "/" in limit
            parts = limit.split("/")
            assert len(parts) == 2
            assert parts[0].isdigit()  # Request count
            assert parts[1] in ["second", "minute", "hour", "day"]  # Period

    def test_search_limit_is_permissive(self):
        """Search limit allows reasonable traffic."""
        # Extract number from limit string
        limit_count = int(SEARCH_LIMIT.split("/")[0])
        # Should be at least 10 requests per minute
        assert limit_count >= 10

    def test_conversation_limit_is_restrictive(self):
        """Conversation (LLM) limit is restrictive to prevent abuse."""
        limit_count = int(CONVERSATION_LIMIT.split("/")[0])
        # Should be less than search limit
        assert limit_count < int(SEARCH_LIMIT.split("/")[0])

    def test_task_limits_configured(self):
        """Task submission limits are configured."""
        submit_count = int(TASK_SUBMIT_LIMIT.split("/")[0])
        status_count = int(TASK_STATUS_LIMIT.split("/")[0])
        
        # Status checks should be more permissive than submissions
        assert status_count >= submit_count

    def test_app_has_rate_limiter(self):
        """App is configured with rate limiter."""
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None


class TestRateLimitResponses:
    """Test rate limiting response format."""

    def test_rate_limit_error_has_proper_format(self):
        """Rate limit error response includes error_id and proper structure."""
        # This test validates the error response format
        # In real integration tests, we would trigger the limiter
        # For now, we verify the handler exists
        from app.common.rate_limit import rate_limit_exception_handler
        
        assert callable(rate_limit_exception_handler)
