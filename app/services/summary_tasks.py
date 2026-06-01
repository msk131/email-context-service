"""Backward-compatible alias for summary task services."""

import sys

from app.services import summaries as _summaries

sys.modules[__name__] = _summaries
