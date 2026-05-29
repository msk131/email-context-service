from pathlib import Path
import yaml
from typing import Any, Dict

PROMPTS_PATH = Path(__file__).parent / "prompts.yml"


def load_prompt(name: str) -> Dict[str, Any]:
    with PROMPTS_PATH.open("r", encoding="utf-8") as fh:
        docs = yaml.safe_load(fh)
    if name not in docs:
        raise KeyError(f"Prompt '{name}' not found")
    return docs[name]


def render_prompt(name: str, **kwargs) -> str:
    prompt_def = load_prompt(name)
    template = prompt_def.get("template", "")
    return template.format(**kwargs)
