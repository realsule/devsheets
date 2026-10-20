"""Load and validate cheat-sheet JSON files.

Cheat-sheet data is only ever *read and displayed*. Nothing in it is executed.

File format (see README):
    {"menu": 4, "menu_title": "React and Vite", "section": "Setup",
     "entries": [ {id, title, keywords, summary, when, where, steps, ...} ]}
Several files may share one menu number; their entries are merged.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "cheatsheets"

# Terminal shells are copyable commands; the rest are code/text examples.
TERMINAL_SHELLS = {"bash", "powershell", "any"}
SHELLS = TERMINAL_SHELLS | {"text", "js", "jsx", "ts", "tsx", "css", "html", "json", "env"}


def step_text(step: dict) -> str:
    code = step.get("code", "")
    return "\n".join(code) if isinstance(code, list) else str(code)


def validate_entry(entry: object) -> list[str]:
    """Return a list of problems (empty list = valid)."""
    if not isinstance(entry, dict):
        return ["entry is not an object"]
    errors = []
    for key in ("id", "title", "summary"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            errors.append(f"missing text field '{key}'")
    for key in ("keywords", "troubleshooting"):
        if key in entry and not isinstance(entry[key], list):
            errors.append(f"'{key}' must be a list")
    steps = entry.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("'steps' must be a non-empty list")
        return errors
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            errors.append(f"step {i} is not an object")
            continue
        if step.get("shell") not in SHELLS:
            errors.append(f"step {i}: unknown shell {step.get('shell')!r}")
        if not step_text(step).strip():
            errors.append(f"step {i}: empty code")
    return errors


def load_all(data_dir: Path | str = DATA_DIR):
    """Return (categories, problems). Bad files/entries are skipped, never fatal."""
    problems: list[str] = []
    files = []
    for path in sorted(Path(data_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path.name}: cannot read ({exc})")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("menu"), int) or not data.get("menu_title"):
            problems.append(f"{path.name}: needs integer 'menu' and a 'menu_title'")
            continue
        files.append((path, data))
    files.sort(key=lambda pd: (pd[1]["menu"], pd[1].get("order", 0), pd[0].name))

    menus: dict[int, dict] = {}
    seen: set[str] = set()
    for path, data in files:
        bucket = menus.setdefault(data["menu"], {"menu": data["menu"], "title": data["menu_title"], "entries": []})
        for raw in data.get("entries", []):
            where = f"{path.name}:{raw.get('id', '?') if isinstance(raw, dict) else '?'}"
            errors = validate_entry(raw)
            if errors:
                problems.extend(f"{where}: {e}" for e in errors)
                continue
            if raw["id"] in seen:
                problems.append(f"{where}: duplicate id")
                continue
            seen.add(raw["id"])
            entry = dict(raw)
            entry.update(menu=data["menu"], category=bucket["title"], section=data.get("section", ""))
            bucket["entries"].append(entry)
    return [menus[k] for k in sorted(menus)], problems


def find_by_id(categories, entry_id: str):
    for cat in categories:
        for entry in cat["entries"]:
            if entry["id"] == entry_id:
                return entry
    return None
