"""Small, dependency-free keyword search with light stemming and synonyms."""
from __future__ import annotations

import re

from .loader import step_text

_WORD = re.compile(r"[a-z0-9][a-z0-9.+#_-]*")
STOP = {"a", "an", "the", "to", "how", "do", "i", "my", "in", "on", "of", "for", "with", "and", "is", "it", "me", "can"}
ALIASES = {
    "ts": "typescript", "js": "javascript", "repo": "repository", "repos": "repository",
    "repositories": "repository", "router": "route", "routing": "route", "routes": "route",
    "edit": "change", "modify": "change", "update": "change", "editing": "change",
    "nodejs": "node", "node.js": "node", "gh": "github", "deps": "dependency",
    "dependencies": "dependency", "dir": "directory", "folder": "directory",
    "powershell": "powershell", "pwsh": "powershell", "zsh": "bash",
}
# Field weights: how strongly a match in that field counts.
W_TITLE, W_KEYWORD, W_TEXT, W_CODE = 5, 4, 2, 1


def stem(word: str) -> str:
    word = ALIASES.get(word, word)
    for _ in range(2):
        for suffix in ("ing", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3 and not word.endswith("ss"):
                word = word[: -len(suffix)]
                break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


def _stems(text: str) -> set[str]:
    return {stem(w.rstrip(".")) for w in _WORD.findall(text.lower())}


def _index(entry: dict) -> dict:
    idx = entry.get("_idx")
    if idx:
        return idx
    steps = entry["steps"]
    idx = {
        "title": entry["title"].lower(),
        "keywords": [k.lower() for k in entry.get("keywords", [])],
        "fields": [
            (W_TITLE, _stems(entry["title"])),
            (W_KEYWORD, _stems(" ".join(entry.get("keywords", [])))),
            (W_TEXT, _stems(" ".join([entry["summary"], entry.get("when", ""), entry.get("category", ""),
                                      " ".join(s.get("label", "") for s in steps)]))),
            (W_CODE, _stems(" ".join([entry.get("expected", "")] + entry.get("troubleshooting", [])
                                     + [step_text(s) for s in steps]))),
        ],
    }
    entry["_idx"] = idx
    return idx


def search(categories, query: str, limit: int = 15):
    """Return [(entry, score)] best-first. Most query words must match."""
    tokens = list(dict.fromkeys(stem(t.rstrip(".")) for t in _WORD.findall(query.lower()) if t not in STOP))
    if not tokens:
        return []
    phrase = " ".join(query.lower().split())
    need = len(tokens) if len(tokens) <= 2 else len(tokens) - 1
    found = []
    for cat in categories:
        for entry in cat["entries"]:
            idx = _index(entry)
            matched = score = 0
            for tok in tokens:
                best = max((w for w, stems in idx["fields"] if tok in stems), default=0)
                if best:
                    matched += 1
                    score += best
            if matched < need:
                continue
            if phrase in idx["keywords"]:
                score += 15                      # exact keyword phrase, e.g. "vite not found"
            elif any(phrase in k for k in idx["keywords"]):
                score += 6
            if phrase in idx["title"]:
                score += 4
            found.append((matched, score, entry))
    found.sort(key=lambda r: (-r[0], -r[1], r[2]["title"]))
    return [(entry, score) for _, score, entry in found[:limit]]
