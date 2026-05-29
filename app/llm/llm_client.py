import asyncio
from typing import Any, Dict, Optional

import httpx
from prometheus_client import Counter, Histogram
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

# Metrics
LLM_REQUESTS = Counter("llm_requests_total", "Total LLM requests", ["model", "status"])
LLM_TOKENS = Counter("llm_tokens_total", "Total tokens consumed by LLM calls", ["model", "type"])  # type: in|out
LLM_LATENCY = Histogram("llm_request_duration_seconds", "LLM request duration seconds", ["model"]) 


class LLMClient:
    """Simple async LLM client wrapper with retries + exponential backoff and token estimation.

    This wrapper is purposely small for local development: it centralizes retries, timeouts,
    and token-estimation so callers can be provider-agnostic.
    """

    def __init__(self, api_key: Optional[str], model: str, endpoint: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    async def generate(self, payload: Dict[str, Any], max_attempts: int = 5) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        wait = wait_exponential(multiplier=0.5, max=60)

        async for attempt in AsyncRetrying(reraise=True, stop=stop_after_attempt(max_attempts), wait=wait,
                                          retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError, RuntimeError))):
            with attempt:

                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        with LLM_LATENCY.labels(self.model).time():
                            resp = await client.post(self.endpoint, headers=headers, json=payload)
                        resp.raise_for_status()
                        data = resp.json()

                        # Try to extract usage info from provider response; fall back to heuristic
                        usage = data.get("usage") if isinstance(data, dict) else None
                        prompt_text = None
                        # common placement for prompt text
                        if isinstance(payload.get("prompt"), dict):
                            prompt_text = payload["prompt"].get("text")
                        elif isinstance(payload.get("input"), str):
                            prompt_text = payload.get("input")

                        token_in = 0
                        token_out = 0
                        if isinstance(usage, dict):
                            token_in = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                            token_out = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                        else:
                            token_in = estimate_tokens(prompt_text or "")
                            # can't know output until generated; estimate 1/4 of prompt or leftover
                            token_out = max(1, len(data.get("output", {}).get("text", "")) // 4) if isinstance(data, dict) else 0

                        # Update metrics
                        LLM_REQUESTS.labels(self.model, "success").inc()
                        LLM_TOKENS.labels(self.model, "in").inc(token_in)
                        LLM_TOKENS.labels(self.model, "out").inc(token_out)

                        return data
                except Exception as exc:
                    last_exc = exc
                    LLM_REQUESTS.labels(self.model, "error").inc()
                    # tenacity will sleep according to wait policy before next try
                    raise

        raise RuntimeError("LLM generate failed after retries") from last_exc


def estimate_tokens(text: str) -> int:
    """Heuristic token estimator for local development fallback.

    Uses rough 4 chars per token heuristic.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)
