from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def load_catalog() -> list[dict]:
    """Names + one-line descriptions only. This is all route() sees."""
    return yaml.safe_load((SKILLS_DIR / "catalog.yaml").read_text())["skills"]


def load_skill(name: str) -> dict:
    """Load one skill file on demand: front-matter tool schema + instructions body."""
    _, front, body = (SKILLS_DIR / f"{name}.md").read_text().split("---", 2)
    return {"name": name, "tool": yaml.safe_load(front)["tool"], "instructions": body.strip()}
