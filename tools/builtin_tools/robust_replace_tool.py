# tools/builtin_tools/robust_replace_tool.py
"""
Robust replace tool implementation with helper functions
"""

import os
import re
import difflib
import tempfile
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class ReplaceError(Exception):
    """Custom exception for replacement errors"""
    pass

def _detect_eol(data: bytes) -> str:
    """Detect end-of-line character from bytes"""
    if b"\r\n" in data:
        return "\r\n"
    elif b"\r" in data:
        return "\r"
    else:
        return "\n"

def _sha256(data: bytes) -> str:
    """Compute SHA256 hash of data"""
    return hashlib.sha256(data).hexdigest()

def unified_diff(a: str, b: str, fromfile: str = '', tofile: str = '') -> str:
    """Generate unified diff between two strings"""
    return '\n'.join(difflib.unified_diff(
        a.splitlines(), b.splitlines(), fromfile=fromfile, tofile=tofile, lineterm=''
    ))

def preview_line(text: str, max_length: int = 100) -> str:
    """Preview a line with length limit"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

class RobustReplaceTool(BaseTool):
    """Robust text replacement tool"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="robust_replace",
            description=(
                "Performs robust text replacement in a file using literal, anchor-based, regex, or fuzzy matching. "
                "Guarantees encoding/EOL preservation, atomic writes, and provides detailed telemetry. "
            ),
            parameters={
                "file_path": {"type": "string", "description": "Path to the file to modify."},
                "new_string": {"type": "string", "description": "The string to replace with."},
                "old_string": {"type": "string", "description": "The string to be replaced (literal match)."},
                "start_anchor": {"type": "string", "description": "Start anchor for replacement."},
                "end_anchor": {"type": "string", "description": "End anchor for replacement."},
                "regex_pattern": {"type": "string", "description": "Regex pattern for replacement."},
                "occurrence_index": {"type": "integer", "description": "Index of the occurrence to replace (0-based)."},
                "expect_count": {"type": "integer", "description": "Expected number of replacements."},
                "allow_fuzzy": {"type": "boolean", "description": "Allow fuzzy matching."},
                "dry_run": {"type": "boolean", "description": "Perform a dry run without writing changes."},
            },
            required=["file_path", "new_string"],
            tool_type=ToolType.REPLACEMENT,
            keywords=["replace", "file", "text", "modify", "regex"],
            examples=[
                {"file_path": "example.txt", "new_string": "new content", "old_string": "old content"},
                {"file_path": "config.json", "new_string": "{\"key\": \"value\"}", "start_anchor": "{", "end_anchor": "}"},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            file_path = parameters["file_path"]
            new_string = parameters["new_string"]
            old_string = parameters.get("old_string")
            start_anchor = parameters.get("start_anchor")
            end_anchor = parameters.get("end_anchor")
            regex_pattern = parameters.get("regex_pattern")
            occurrence_index = parameters.get("occurrence_index")
            expect_count = parameters.get("expect_count", 1)
            allow_fuzzy = parameters.get("allow_fuzzy", False)
            dry_run = parameters.get("dry_run", False)

            # Read file and detect encoding/EOL
            path_obj = Path(file_path)
            with open(path_obj, "rb") as f:
                raw = f.read()
            eol = _detect_eol(raw)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1")
            before_hash = _sha256(raw)

            mode_used = None
            occurrences = 0
            new_text = text

            # 1) literal replacement
            if old_string is not None and not (start_anchor or end_anchor or regex_pattern or allow_fuzzy):
                hits = [m.start() for m in re.finditer(re.escape(old_string), text)]
                if hits:
                    if expect_count is not None and len(hits) != expect_count and occurrence_index is None:
                        raise ReplaceError(f"Literal match count {len(hits)} != expect_count {expect_count}. "
                                           f"Provide occurrence_index or switch to anchors.")
                    if occurrence_index is None:
                        count = expect_count if expect_count is not None else 0
                        new_text = text.replace(old_string, new_string, count if count else text.count(old_string))
                        occurrences = (count if count else text.count(old_string))
                    else:
                        start = hits[occurrence_index]
                        end = start + len(old_string)
                        new_text = text[:start] + new_string + text[end:]
                        occurrences = 1
                    mode_used = "literal"

            # 2) anchor-based replacement
            if mode_used is None and start_anchor and end_anchor:
                s = text.find(start_anchor)
                if s != -1:
                    s_end = s + len(start_anchor)
                    e = text.find(end_anchor, s_end)
                    if e != -1 and e >= s_end:
                        new_text = text[:s_end] + new_string + text[e:]
                        mode_used = "anchors"
                        occurrences = 1

            # 3) regex replacement
            if mode_used is None and regex_pattern:
                pat = re.compile(regex_pattern, re.DOTALL)
                new_text, n = pat.subn(new_string, text, count=(expect_count or 0) or 0)
                if n > 0:
                    mode_used = "regex"
                    occurrences = n

            # 4) fuzzy matching
            if mode_used is None and allow_fuzzy and old_string:
                target_len = max(10, len(old_string))
                best = (0.0, 0, 0)
                for i in range(0, max(1, len(text) - target_len), max(1, target_len // 3)):
                    j = min(len(text), i + int(target_len * 1.6))
                    s = text[i:j]
                    r = difflib.SequenceMatcher(a=old_string, b=s).ratio()
                    if r > best[0]:
                        best = (r, i, j)
                ratio, i, j = best
                if ratio >= 0.85:
                    new_text = text[:i] + new_string + text[j:]
                    mode_used = "fuzzy"
                    occurrences = 1

            # No match found
            if mode_used is None:
                raise ReplaceError(
                    "No match found. Try anchors or a tighter regex. "
                    "Avoid copying truncated snippets or mismatched whitespace."
                )

            # No changes needed
            if new_text == text:
                return ToolResult(
                    status=ToolExecutionStatus.SUCCESS,
                    result={
                        "path": file_path,
                        "status": "no-op",
                        "reason": "Result identical to original",
                        "mode_used": mode_used,
                        "occurrences": occurrences,
                        "hash": before_hash,
                    },
                    execution_time=time.time() - start_time
                )

            # Generate diff preview
            diff = unified_diff(text, new_text, fromfile=file_path, tofile=file_path)
            preview = "\n".join(diff.splitlines()[:50])

            if dry_run:
                return ToolResult(
                    status=ToolExecutionStatus.SUCCESS,
                    result={
                        "path": file_path, "status": "dry-run",
                        "mode_used": mode_used, "occurrences": occurrences,
                        "diff_head": preview
                    },
                    execution_time=time.time() - start_time
                )

            # Atomic write with EOL preservation
            new_bytes = (new_text.replace("\n", eol)).encode("utf-8")
            backup = str(path_obj) + ".bak"
            if not os.path.exists(backup):
                with open(backup, "wb") as f:
                    f.write(raw)

            dir_ = os.path.dirname(file_path) or "."
            fd, tmp = tempfile.mkstemp(prefix=".edit_", dir=dir_)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(new_bytes)
                os.replace(tmp, file_path)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass

            with open(path_obj, "rb") as f:
                after_raw = f.read()
            after_hash = _sha256(after_raw)

            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={
                    "path": file_path,
                    "status": "ok",
                    "mode_used": mode_used,
                    "occurrences": occurrences,
                    "bytes_changed": len(after_raw) - len(raw),
                    "hash_before": before_hash,
                    "hash_after": after_hash,
                    "eol_preserved": _detect_eol(after_raw) == eol,
                    "diff_head": preview
                },
                execution_time=time.time() - start_time
            )
        except ReplaceError as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"An unexpected error occurred: {e}",
                execution_time=time.time() - start_time
            )