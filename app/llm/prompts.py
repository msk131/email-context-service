from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml

PROMPTS_PATH = Path(__file__).parent / "prompts.yml"


@lru_cache(maxsize=1)
def _load_prompts() -> dict[str, Any]:
    with PROMPTS_PATH.open("r", encoding="utf-8") as fh:
        docs = yaml.safe_load(fh) or {}
    return dict(docs)


def load_prompt(name: str) -> dict[str, Any]:
    docs = _load_prompts()
    if name not in docs:
        raise KeyError(f"Prompt '{name}' not found")
    return dict(docs[name])


def render_prompt(name: str, **kwargs: str) -> str:
    prompt_def = load_prompt(name)
    template = str(prompt_def.get("template", ""))
    return template.format(**kwargs)
