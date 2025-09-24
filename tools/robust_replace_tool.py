import os
import shutil
import hashlib
import tempfile
import difflib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

class ReplaceError(Exception): pass

def _detect_eol(b: bytes) -> str:
    crlf = b.count(b"\r\n")
    lf   = b.count(b"\n")
    return "\r\n" if crlf >= 0.8 * max(1, lf) else "\n"

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def unified_diff(a: str, b: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=f"{path} (original)",
            tofile=f"{path} (modified)",
            lineterm="",
        )
    )

def preview_line(text: str, lineno: int, col: int) -> str:
    lines = text.splitlines()
    if 1 <= lineno <= len(lines):
        line = lines[lineno - 1]
        caret = " " * max(col - 1, 0) + "^"
        return f"{line}\n{caret}"
    return ""

def _balance_quotes(s: str) -> str:
    for q in ("'", '"'):
        if s.count(q) % 2 != 0:
            s += q
    return s

def _balance_brackets(s: str) -> str:
    braces = s.count("{") - s.count("}")
    brackets = s.count("[") - s.count("]")
    parens = s.count("(") - s.count(")")
    if braces > 0:
        s += "}" * braces
    if brackets > 0:
        s += "]" * brackets
    if parens > 0:
        s += ")" * parens
    return s

def _fix_comma_delimiters(s: str) -> str:
    s = re.sub(r'(":[^,\{\[\n]+?)\s+?(")', r"\1, \2", s)
    s = re.sub(r'([\}\]])\s+(")', r"\1, \2", s)
    s = re.sub(r'(:\s*(?:-?\d+(?:\.\d+)?|true|false|null))\s+(")', r"\1, \2", s)
    return s

def repair_jsonish(s: str) -> str:
    s2 = _balance_quotes(s)
    s2 = _balance_brackets(s2)
    s2 = _fix_comma_delimiters(s2)
    return s2

def detect_python_syntax(text: str) -> List[str]:
    issues: List[str] = []
    try:
        compile(text, "<string>", "exec")
    except SyntaxError as e:
        prev = preview_line(text, e.lineno or 0, e.offset or 0)
        issues.append(
            f"Python SyntaxError: {e.msg} at line {e.lineno}, col {e.offset}\n{prev}"
        )
    return issues

def detect_json_syntax(text: str) -> Tuple[List[str], Optional[str]]:
    issues: List[str] = []
    try:
        json.loads(text)
        return issues, None
    except json.JSONDecodeError as e:
        prev = preview_line(text, e.lineno, e.colno)
        issues.append(f"JSON error: {e.msg} at line {e.lineno}, col {e.colno}\n{prev}")
        repaired = repair_jsonish(text)
        try:
            json.loads(repaired)
            return issues, repaired
        except Exception:
            return issues, repaired
    except Exception as e:
        issues.append(f"JSON unknown error: {e}")
        return issues, None

def detect_generic_balance(text: str) -> List[str]:
    issues: List[str] = []
    pairs = {"{ ": "}", "[": "]", "(": ")"}
    for open_c, close_c in pairs.items():
        diff = text.count(open_c) - text.count(close_c)
        if diff != 0:
            issues.append(f"Unbalanced {open_c}{close_c}: {diff:+d}")
    for q in ("'", '"'):
        if text.count(q) % 2 != 0:
            issues.append(f"Unbalanced quotes {q}")
    return issues

def load_rules(path: Optional[str]) -> Dict[str, List[Dict[str, str]]]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    compiled: Dict[str, List[Dict[str, object]]] = {}
    for ext, rules in data.items():
        compiled_rules = []
        for r in rules:
            pat_literal = r["pattern"]
            pat = pat_literal
            if pat.startswith("r'") and pat.endswith("'"):
                pat = pat[2:-1]
            elif pat.startswith('r"') and pat.endswith('"'):
                pat = pat[2:-1]
            flag_val = 0
            for name in (r.get("flags") or "").split("|"):
                name = name.strip().upper()
                if not name:
                    continue
                flag_val |= getattr(re, name, 0)
            compiled_rules.append(
                {"regex": re.compile(pat, flag_val), "repl": r.get("repl", "")}
            )
        compiled[ext] = compiled_rules
    return compiled

def apply_rules(text: str, ext: str, rules: Dict[str, List[Dict[str, object]]]) -> str:
    def apply_group(key: str, s: str) -> str:
        for r in rules.get(key, []):
            s = r["regex"].sub(str(r["repl"]), s)
        return s

    out = apply_group(ext, text)
    out = apply_group("*", out)
    return out

def guess_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".py":
        return "python"
    if ext in (".json", ".json5"):
        return "json"
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        return "code"
    return "text"

def process_file(
    path: Path, write: bool, rules: Dict[str, List[Dict[str, object]]]
) -> int:
    original = path.read_text(encoding="utf-8", errors="replace")
    kind = guess_kind(path)

    issues: List[str] = []
    suggested: Optional[str] = None

    if kind == "python":
        issues.extend(detect_python_syntax(original))
    elif kind == "json":
        json_issues, repaired = detect_json_syntax(original)
        issues.extend(json_issues)
        suggested = repaired
    else:
        issues.extend(detect_generic_balance(original))

    modified = apply_rules(original, path.suffix.lower(), rules)

    if suggested and suggested != original and modified == original:
        modified = suggested

    if modified != original:
        diff = unified_diff(original, modified, str(path))
        print(diff)
        if write:
            path.write_text(modified, encoding="utf-8")
            print(f"[APPLIED] {path}")
        else:
            print(f"[DRY-RUN] Changes not written. Use --write to apply.")
    else:
        print(f"[OK] {path} — no changes")

    if issues:
        print(f"[ISSUES] {path}:")
        for msg in issues:
            print(f"  - {msg}")

    return 1 if issues else 0
