#!/usr/bin/env python3
"""DevSheets - an offline, interactive developer cheat sheet for the terminal.

Run:  python3 main.py            (Windows: py main.py  or  python main.py)
      python3 main.py --search "react routes"
"""
from __future__ import annotations

import argparse
import sys

from services import clipboard, loader, search
from services.display import Display
from services.loader import TERMINAL_SHELLS, step_text

QUIT_WORDS = {"q", "quit", "exit"}
BACK_WORDS = {"b", "back"}


class Quit(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Quit


def parse_search(raw: str):
    """Return the query text, or None when the user typed just 's' / '/'."""
    low = raw.lower()
    if low in ("s", "search", "/"):
        return None
    for prefix in ("search ", "s ", "/"):
        if low.startswith(prefix):
            return raw[len(prefix):].strip()
    return raw


def parse_steps(arg: str, count: int):
    """'2' -> [2]; '1-3' -> [1,2,3]; '1,4' -> [1,4]. Returns None when invalid."""
    chosen = []
    for part in arg.replace(",", " ").split():
        lo, _, hi = part.partition("-")
        if not lo.isdigit() or (hi and not hi.isdigit()):
            return None
        lo, hi = int(lo), int(hi or lo)
        if not 1 <= lo <= hi <= count:
            return None
        chosen.extend(range(lo, hi + 1))
    return chosen or None


def copy_payload(entry: dict, arg: str):
    """Return (text, error). Never executes anything."""
    steps = entry["steps"]
    if not arg:
        terminal = [i for i, s in enumerate(steps, 1) if s["shell"] in TERMINAL_SHELLS]
        if len(terminal) != 1:
            return None, "Several steps here (some may be alternatives). Pick with 'c N' or a range like 'c 1-3'."
        arg = str(terminal[0])
    chosen = parse_steps(arg, len(steps))
    if not chosen:
        return None, f"Use a step number 1-{len(steps)}, a list (1,3) or a range (1-3)."
    picked = [steps[i - 1] for i in chosen]
    shells = {s["shell"] for s in picked if s["shell"] in ("bash", "powershell")}
    if len(shells) > 1:
        return None, "Those steps mix Linux and PowerShell commands. Copy them separately."
    return "\n".join(step_text(s) for s in picked), None


class App:
    def __init__(self, categories, ui: Display, problems: int = 0):
        self.categories, self.ui, self.problems = categories, ui, problems

    def run(self):
        while True:
            self.ui.home(self.categories, self.problems)
            raw = ask("\ndevsheets> ")
            low = raw.lower()
            if not raw:
                continue
            if low in QUIT_WORDS:
                raise Quit
            if low in ("h", "help", "?"):
                self.ui.help()
            elif raw.isdigit():
                cat = next((c for c in self.categories if c["menu"] == int(raw)), None)
                self.category(cat) if cat else self.ui.error(f"No category numbered {raw}.")
            else:
                self.search(parse_search(raw))

    def category(self, cat):
        while True:
            self.ui.category(cat)
            raw = ask("\n" + cat["title"][:24] + "> ")
            low = raw.lower()
            if not raw or low in BACK_WORDS:
                return
            if low in QUIT_WORDS:
                raise Quit
            if raw.isdigit():
                n = int(raw)
                if 1 <= n <= len(cat["entries"]):
                    self.entry(cat["entries"][n - 1])
                else:
                    self.ui.error(f"Choose 1-{len(cat['entries'])}.")
            else:
                self.search(parse_search(raw))

    def search(self, query):
        if query is None:
            query = ask("Search for: ")
        while query:
            results = search.search(self.categories, query)
            if not results:
                self.ui.no_results(query)
                query = ask("Search again (or b to go back): ")
                if query.lower() in BACK_WORDS or not query:
                    return
                if query.lower() in QUIT_WORDS:
                    raise Quit
                continue
            self.ui.results(query, results)
            raw = ask("\nsearch> ")
            low = raw.lower()
            if not raw or low in BACK_WORDS:
                return
            if low in QUIT_WORDS:
                raise Quit
            if raw.isdigit():
                n = int(raw)
                if 1 <= n <= len(results):
                    self.entry(results[n - 1][0])
                else:
                    self.ui.error(f"Choose 1-{len(results)}.")
            else:
                query = parse_search(raw) or ""

    def entry(self, entry):
        self.ui.entry(entry)
        while True:
            raw = ask("[c N] copy step (e.g. c 2, c 1-3)  [b] back  [q] quit > ")
            low = raw.lower()
            if not raw or low in BACK_WORDS:
                return
            if low in QUIT_WORDS:
                raise Quit
            if low == "c" or low.startswith("c "):
                text, err = copy_payload(entry, low[1:].strip())
                if err:
                    self.ui.error(err)
                else:
                    ok, msg = clipboard.copy(text)
                    (self.ui.message if ok else self.ui.error)(msg)
            else:
                self.ui.error("Use c, c N, b or q.")


def build_parser():
    p = argparse.ArgumentParser(prog="devsheets", description="Offline developer cheat sheets.")
    p.add_argument("-s", "--search", metavar="QUERY", help="search and print matching sheets, then exit")
    p.add_argument("--show", metavar="ID", help="print one sheet by id (see --list) and exit")
    p.add_argument("--list", action="store_true", help="list every sheet id and exit")
    p.add_argument("--validate", action="store_true", help="check all cheat-sheet files and exit")
    p.add_argument("--plain", action="store_true", help="disable colours and optional syntax highlighting")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # never crash on odd console encodings
        except Exception:
            pass
    categories, problems = loader.load_all()
    ui = Display(plain=args.plain)

    if args.validate:
        total = sum(len(c["entries"]) for c in categories)
        for p in problems:
            print("PROBLEM:", p)
        print(f"{total} sheets in {len(categories)} categories, {len(problems)} problem(s).")
        return 1 if problems else 0
    if args.list:
        for cat in categories:
            print(f"{cat['menu']}. {cat['title']}")
            for e in cat["entries"]:
                print(f"    {e['id']:<28} {e['title']}")
        return 0
    if args.show:
        entry = loader.find_by_id(categories, args.show)
        if not entry:
            print(f"No sheet with id '{args.show}'. Try --list.", file=sys.stderr)
            return 1
        ui.entry(entry)
        return 0
    if args.search:
        results = search.search(categories, args.search)
        if not results:
            ui.no_results(args.search)
            return 1
        ui.results(args.search, results)
        print("\nOpen one with:  python main.py --show ID")
        for e, _ in results:
            print(f"  {e['id']}")
        return 0

    try:
        App(categories, ui, len(problems)).run()
    except Quit:
        print("Bye!")
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
