"""Terminal output. Plain ASCII text always works; 'rich' (optional) only adds syntax colour."""
from __future__ import annotations

import os
import shutil
import sys
import textwrap

from .loader import TERMINAL_SHELLS, step_text

try:  # optional dependency
    from rich.console import Console
    from rich.syntax import Syntax
except Exception:  # pragma: no cover - rich is optional
    Console = Syntax = None

SHELL_BADGE = {
    "bash": ("Linux / macOS / WSL (Bash or Zsh)", "32"),
    "powershell": ("Windows PowerShell", "34"),
    "any": ("Any terminal (same command in Bash, Zsh and PowerShell)", "36"),
    "text": ("Instructions / reference (not a command)", "33"),
}
LEXERS = {"bash": "bash", "powershell": "powershell", "any": "bash", "js": "javascript", "jsx": "jsx",
          "ts": "typescript", "tsx": "tsx", "css": "css", "html": "html", "json": "json", "env": "ini", "text": "text"}
PLATFORM = {"all": "All platforms", "linux": "Linux / macOS / WSL only", "windows": "Windows only",
            "both": "Linux and Windows (separate commands are labelled)"}


class Display:
    def __init__(self, plain: bool = False):
        tty = sys.stdout.isatty()
        self.color = tty and not plain and "NO_COLOR" not in os.environ
        if self.color and os.name == "nt":
            os.system("")  # enables ANSI escape codes in Windows terminals
        self.rich = None
        if Console and not plain and not os.environ.get("DEVSHEETS_PLAIN"):
            console = Console()
            if console.is_terminal:
                self.rich = console

    # ---- helpers ---------------------------------------------------------
    @property
    def width(self) -> int:
        return max(50, min(shutil.get_terminal_size((80, 24)).columns, 100))

    def c(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def bold(self, t): return self.c(t, "1")
    def dim(self, t): return self.c(t, "2")

    def wrap(self, text: str, indent: int = 0, first: str = "") -> str:
        pad = " " * indent
        return textwrap.fill(text, width=self.width, initial_indent=first or pad, subsequent_indent=pad)

    def rule(self, ch: str = "=") -> str:
        return self.dim(ch * self.width)

    def message(self, text: str): print(self.wrap(text))
    def error(self, text: str): print(self.c("! " + text, "31"))

    # ---- screens ---------------------------------------------------------
    def home(self, categories, problems: int = 0):
        print()
        print(self.rule())
        print(self.bold("  DevSheets  -  developer cheat sheets in your terminal"))
        print(self.rule())
        for cat in categories:
            print(f"  {self.c(str(cat['menu']).rjust(2), '36')}) {cat['title']}  {self.dim('(' + str(len(cat['entries'])) + ')')}")
        print()
        print(self.dim("  Type a number to browse, or just type words to search (e.g. 'react routes', 'ssh key')."))
        print(self.dim("  h = help   q = quit"))
        if problems:
            print(self.c(f"  {problems} cheat-sheet problem(s) found - run: python main.py --validate", "33"))

    def help(self):
        print(textwrap.dedent("""
            Commands
              <number>        open a category / result
              <words>         search everything (also: s words, /words)
              c N, c 1-3      (on a sheet) copy step N / steps 1 to 3 to the clipboard
              b               go back
              q               quit
            Tips
              * Search several words: 'vite not found', 'change heading', 'clone repository'.
              * Each step says WHICH shell it is for and WHERE (directory) to run it.
              * Nothing is ever executed by DevSheets - you copy and run commands yourself.
        """))

    def category(self, cat):
        print()
        print(self.rule())
        print(self.bold(f"  {cat['menu']}. {cat['title']}"))
        print(self.rule())
        for i, e in enumerate(cat["entries"], 1):
            print(f"  {self.c(str(i).rjust(2), '36')}) {e['title']}")
        print(self.dim("\n  number = open   b = back   q = quit   or type words to search"))

    def results(self, query: str, results):
        print()
        print(self.bold(f"  Results for '{query}'  ({len(results)})"))
        print(self.rule("-"))
        for i, (e, _) in enumerate(results, 1):
            print(f"  {self.c(str(i).rjust(2), '36')}) {e['title']}  {self.dim('[' + e['category'] + ']')}")
        print(self.dim("\n  number = open   b = back   or type new words to search again"))

    def no_results(self, query: str):
        self.message(f"Nothing found for '{query}'. Try fewer or different words, e.g. 'react routes', "
                     "'ssh key', 'npm install', 'vite not found'.")

    def _code(self, step: dict):
        text = step_text(step)
        if self.rich and Syntax:
            self.rich.print(Syntax(text, LEXERS.get(step["shell"], "text"), theme="ansi_dark",
                                   word_wrap=True, background_color="default", padding=(0, 0, 0, 6)))
            return
        for line in text.splitlines():
            print("      " + self.c(line, "33" if step["shell"] in TERMINAL_SHELLS else "0"))

    def entry(self, e: dict):
        print()
        print(self.rule())
        print(self.bold("  " + e["title"]))
        print(self.rule())
        print(f"  {self.dim('Category')}   {e['category']}    {self.dim('Platform')}  {PLATFORM.get(e.get('os', 'all'), 'All platforms')}")
        for label, key in (("What it does", "summary"), ("When to use", "when"), ("Where to run", "where")):
            if e.get(key):
                print(self.wrap(f"{e[key]}", 15, f"  {self.bold(label.ljust(13))}"))
        if e.get("warning"):
            print()
            print(self.c(self.wrap("WARNING: " + e["warning"], 4, "  [!] "), "31;1"))
        print()
        print(self.bold("  Steps"))
        for i, step in enumerate(e["steps"], 1):
            shell = step["shell"]
            badge, col = SHELL_BADGE.get(shell, ("Code example (edit the file shown)", "35"))
            if shell not in SHELL_BADGE:
                badge = "Code example"
            title = step.get("label") or ("Command" if shell in TERMINAL_SHELLS else "Example")
            print(self.wrap(title, 6, f"  {self.c(str(i).rjust(2), '36')}) "))
            print("      " + self.c("[" + badge + "]", col))
            if shell in TERMINAL_SHELLS:
                print("      " + self.dim("Directory: ") + step.get("dir", "Any directory"))
            elif step.get("file"):
                print("      " + self.dim("File: ") + step["file"])
            self._code(step)
            print()
        if e.get("expected"):
            print(self.wrap(e["expected"], 15, f"  {self.bold('Expected'.ljust(13))}"))
        if e.get("troubleshooting"):
            print()
            print(self.bold("  Troubleshooting"))
            for tip in e["troubleshooting"]:
                print(self.wrap(tip, 6, "   *  "))
        print()
        print(self.rule("-"))
