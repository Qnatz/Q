# tools/tool_registry.py
"""
Tool Registry System - Dynamic function calling for QAI Agent
Provides extensible tool system with schema validation and execution
"""

import os
import json
import inspect
import importlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Type, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import re
import difflib
import tempfile
import hashlib
import shutil

# Import for Stepwise tools
from pydantic.dataclasses import PrivateAttr
from utils.validation_utils import SchemaValidatorTool

# Import helper functions for RobustReplaceTool
from tools.robust_replace_tool import ReplaceError, _detect_eol, _sha256, unified_diff, preview_line

# Configure logging
logger = logging.getLogger(__name__)

class ToolType(Enum):
    SEARCH = "search"
    FILE_OPERATION = "file_operation"
    CODE_ANALYSIS = "code_analysis"
    WEB_REQUEST = "web_request"
    SYSTEM_INFO = "system_info"
    CUSTOM = "custom"
    PLANNING = "planning" # Added for stepwise tools
    IMPLEMENTATION = "implementation" # Added for stepwise tools
    REPLACEMENT = "replacement" # Added for robust replace tool

class ToolExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]
    tool_type: ToolType
    keywords: List[str]
    examples: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'tool_type': self.tool_type.value
        }

@dataclass
class ToolResult:
    status: ToolExecutionStatus
    result: Any
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'status': self.status.value
        }

class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self):
        self.name = self.__class__.__name__.lower().replace('tool', '')
        self.schema = self._define_schema()
    
    @abstractmethod
    def _define_schema(self) -> ToolSchema:
        """Define the tool's schema"""
        pass
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters against schema"""
        try:
            # Check required parameters
            for required_param in self.schema.required:
                if required_param not in parameters:
                    logger.error(f"Missing required parameter: {required_param}")
                    return False
            
            # Basic type validation
            for param_name, param_config in self.schema.parameters.items():
                if param_name in parameters:
                    expected_type = param_config.get('type', 'string')
                    actual_value = parameters[param_name]
                    
                    if expected_type == 'string' and not isinstance(actual_value, str):
                        logger.error(f"Parameter {param_name} must be string, got {type(actual_value)}")
                        return False
                    elif expected_type == 'integer' and not isinstance(actual_value, int):
                        logger.error(f"Parameter {param_name} must be integer, got {type(actual_value)}")
                        return False
                    elif expected_type == 'boolean' and not isinstance(actual_value, bool):
                        logger.error(f"Parameter {param_name} must be boolean, got {type(actual_value)}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Parameter validation error: {e}")
            return False

# Built-in Tool Implementations

class WebSearchTool(BaseTool):
    """Web search functionality"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="web_search",
            description="Search the web for information",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5},
                "search_type": {"type": "string", "description": "Type of search", "enum": ["general", "news", "images"]}
            },
            required=["query"],
            tool_type=ToolType.SEARCH,
            keywords=["search", "web", "google", "find", "lookup", "internet"],
            examples=[
                {"query": "Python web frameworks", "max_results": 3},
                {"query": "latest AI news", "search_type": "news"}
            ]
        )
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            query = parameters["query"]
            max_results = parameters.get("max_results", 5)
            search_type = parameters.get("search_type", "general")
            
            # Simulate web search (replace with actual implementation)
            simulated_results = [
                {
                    "title": f"Result {i+1} for '{query}'",
                    "url": f"https://example.com/result{i+1}",
                    "snippet": f"This is a sample search result for {query}. Contains relevant information about the topic.",
                    "type": search_type
                }
                for i in range(min(max_results, 3))
            ]
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={
                    "query": query,
                    "results": simulated_results,
                    "total_found": len(simulated_results)
                },
                metadata={
                    "search_type": search_type,
                    "max_results": max_results
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

class FileOperationTool(BaseTool):
    """File system operations"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="file_operation",
            description="Perform file system operations",
            parameters=    {
                "operation": {"type": "string", "enum": ["read", "write", "list", "exists", "delete"]},
                "path": {"type": "string", "description": "File or directory path"},
                "content": {"type": "string", "description": "Content to write (for write operation)"},
                "encoding": {"type": "string", "default": "utf-8"}
            },
            required=["operation", "path"],
            tool_type=ToolType.FILE_OPERATION,
            keywords=["file", "read", "write", "directory", "folder", "filesystem"],
            examples=[
                {"operation": "read", "path": "config.json"},
                {"operation": "write", "path": "output.txt", "content": "Hello World"},
                {"operation": "list", "path": "./projects"}
            ]
        )
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            operation = parameters["operation"]
            path = Path(parameters["path"])
            encoding = parameters.get("encoding", "utf-8")
            
            if operation == "read":
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                
                content = path.read_text(encoding=encoding)
                result = {"content": content, "size": len(content)}
                
            elif operation == "write":
                content = parameters.get("content", "")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding=encoding)
                result = {"bytes_written": len(content), "path": str(path)}
                
            elif operation == "list":
                if not path.exists():
                    raise FileNotFoundError(f"Directory not found: {path}")
                
                items = []
                for item in path.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                result = {"items": items, "total": len(items)}
                
            elif operation == "exists":
                result = {"exists": path.exists(), "is_file": path.is_file(), "is_dir": path.is_dir()}
                
            elif operation == "delete":
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        import shutil
                        shutil.rmtree(path)
                    result = {"deleted": True}
                else:
                    result = {"deleted": False, "reason": "File not found"}
            
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=result,
                metadata={"operation": operation, "path": str(path)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

class CodeAnalysisTool(BaseTool):
    """Code analysis and validation"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="code_analysis",
            description="Analyze code for syntax, style, and complexity",
            parameters=    {
                "code": {"type": "string", "description": "Code to analyze"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
                "analysis_type": {"type": "string", "enum": ["syntax", "style", "complexity", "all"], "default": "all"}
            },
            required=["code"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["code", "analyze", "syntax", "style", "lint", "complexity"],
            examples=[
                {"code": "def hello():\n    print('Hello')", "language": "python"},
                {"code": "function test() { return true; }", "language": "javascript", "analysis_type": "syntax"}
            ]
        )
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            code = parameters["code"]
            language = parameters.get("language", "python")
            analysis_type = parameters.get("analysis_type", "all")
            
            # Basic code analysis (extend with real analyzers)
            analysis_result = {
                "language": language,
                "lines_of_code": len(code.split('\n')),
                "character_count": len(code),
                "issues": [],
                "metrics": {}
            }
            
            # Syntax check for Python
            if language.lower() == "python":
                try:
                    compile(code, '<string>', 'exec')
                    analysis_result["syntax_valid"] = True
                except SyntaxError as e:
                    analysis_result["syntax_valid"] = False
                    analysis_result["issues"].append({
                        "type": "syntax_error",
                        "message": str(e),
                        "line": getattr(e, 'lineno', None)
                    })
            
            # Basic complexity metrics
            if analysis_type in ["complexity", "all"]:
                analysis_result["metrics"] = {
                    "cyclomatic_complexity": self._estimate_complexity(code),
                    "function_count": code.count("def ") if language == "python" else code.count("function"),
                    "class_count": code.count("class ") if language == "python" else 0
                }
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=analysis_result,
                metadata={"language": language, "analysis_type": analysis_type},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def _estimate_complexity(self, code: str) -> int:
        """Simple complexity estimation based on control structures"""
        complexity = 1  # Base complexity
        control_structures = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally']
        
        for structure in control_structures:
            complexity += code.lower().count(structure)
        
        return complexity

class SystemInfoTool(BaseTool):
    """System information and monitoring"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="system_info",
            description="Get system information and resource usage",
            parameters=    {
                "info_type": {"type": "string", "enum": ["cpu", "memory", "disk", "network", "all"], "default": "all"}
            },
            required=[],
            tool_type=ToolType.SYSTEM_INFO,
            keywords=["system", "cpu", "memory", "disk", "resources", "monitor"],
            examples=[
                {"info_type": "cpu"},
                {"info_type": "all"}
            ]
        )
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        import platform
        import os
        start_time = time.time()
        
        try:
            info_type = parameters.get("info_type", "all")
            
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node()
            }
            
            # Add resource information (simplified)
            if info_type in ["cpu", "all"]:
                try:
                    import psutil
                    system_info["cpu"] = {
                        "count": psutil.cpu_count(),
                        "usage_percent": psutil.cpu_percent(interval=1)
                    }
                except ImportError:
                    system_info["cpu"] = {"count": os.cpu_count(), "usage_percent": "unavailable"}
            
            if info_type in ["memory", "all"]:
                try:
                    import psutil
                    mem = psutil.virtual_memory()
                    system_info["memory"] = {
                        "total": mem.total,
                        "available": mem.available,
                        "used_percent": mem.percent
                    }
                except ImportError:
                    system_info["memory"] = {"status": "unavailable"}
            
            if info_type in ["disk", "all"]:
                try:
                    import psutil
                    disk = psutil.disk_usage('/')
                    system_info["disk"] = {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "used_percent": (disk.used / disk.total) * 100
                    }
                except ImportError:
                    system_info["disk"] = {"status": "unavailable"}
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=system_info,
                metadata={"info_type": info_type},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

class RobustReplaceTool(BaseTool):
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="robust_replace",
            description=(
                "Performs robust text replacement in a file using literal, anchor-based, regex, or fuzzy matching. "
                "Guarantees encoding/EOL preservation, atomic writes, and provides detailed telemetry. "
            ),
            parameters=    {
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
            tool_type=ToolType.REPLACEMENT, # Changed to REPLACEMENT type
            keywords=["replace", "file", "text", "modify", "regex"],
            examples=[
                {"file_path": "example.txt", "new_string": "new content", "old_string": "old content"},
                {"file_path": "config.json", "new_string": "{\"key\": \"value\"}", "start_anchor": "{", "end_anchor": "}"},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
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

            # --- read + fingerprint ---
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

            # --- 1) literal ---
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

            # --- 2) anchors ---
            if mode_used is None and start_anchor and end_anchor:
                s = text.find(start_anchor)
                if s != -1:
                    s_end = s + len(start_anchor)
                    e = text.find(end_anchor, s_end)
                    if e != -1 and e >= s_end:
                        new_text = text[:s_end] + new_string + text[e:]
                        mode_used = "anchors"
                        occurrences = 1

            # --- 3) regex ---
            if mode_used is None and regex_pattern:
                pat = re.compile(regex_pattern, re.DOTALL)
                new_text, n = pat.subn(new_string, text, count=(expect_count or 0) or 0)
                if n > 0:
                    mode_used = "regex"
                    occurrences = n

            # --- 4) fuzzy (optional) ---
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

            # --- no-op / failure handling ---
            if mode_used is None:
                raise ReplaceError(
                    "No match found. Try anchors or a tighter regex. "
                    "Avoid copying truncated snippets or mismatched whitespace."
                )
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

            # --- diff preview ---
            diff = "\n".join(
                difflib.unified_diff(
                    text.splitlines(), new_text.splitlines(),
                    fromfile=file_path, tofile=file_path, lineterm=""
                )
            )
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

            # --- atomic write with EOL preservation ---
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

class StepwisePlannerTool(BaseTool):
    name: str = "Stepwise Planner Tool"
    description: str = "Generates a stepwise project plan for a given prompt, breaking it down by sections."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_planner",
            description="Generates a stepwise project plan for a given prompt, breaking it down by sections.",
            parameters=    {
                "refined_prompt": {"type": "string", "description": "The refined prompt for which to generate a plan."}, 
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["refined_prompt"],
            tool_type=ToolType.PLANNING,
            keywords=["plan", "project", "stepwise", "breakdown", "sections"],
            examples=[
                {"refined_prompt": "Develop a simple e-commerce website.", "system_instruction": "Focus on scalability."}
            ]
        )

    def _generate_sections(self, refined_prompt: str) -> List[str]:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates a list of components for a software project."
            },
            {
                "role": "user",
                "content": f"Based on the following project description, what are the main components or sections of this project? "
                           f"Return a JSON list of strings. For example, for a web application, you might return: "
                           f'["Frontend (UI/UX)", "Backend (API)", "Database", "Authentication", "Deployment"]'
                           f"For a data analysis script, you might return: "
                           f'["Data Ingestion", "Data Cleaning", "Data Analysis", "Visualization", "Reporting"]'
                           f"\n\nProject Description: {refined_prompt}"
            }
        ]
        
        response = self._llm.generate(messages, use_tools=False)
        
        try:
            sections = json.loads(response)
            if isinstance(sections, list) and all(isinstance(s, str) for s in sections):
                return sections
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback to default sections
        return ["UI/UX", "Backend", "Database", "API", "Integration"]

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            refined_prompt = parameters["refined_prompt"]
            system_instruction = parameters.get("system_instruction")
            
            sections = self._generate_sections(refined_prompt)

            final_plan = {"project": {"name": "", "description": ""}, "files": [], "tasks": []}
            plan_summary = ""
            
            for section in sections:
                prompt = f"Generate the {section} section of the project plan for: {refined_prompt}"
                if plan_summary:
                    prompt += f"\n\nSummary of previously generated sections:\n{plan_summary}"
                
                if system_instruction:
                    prompt = f"{system_instruction}\n\n{prompt}"
                
                chunk_output = self._llm.generate_with_plan(
                    prompt,
                    system_instruction=system_instruction,
                    chunk_size=512,
                    step_size=256
                )
                
                try:
                    chunk_json = json.loads(chunk_output)
                    SchemaValidatorTool()._run(json.dumps(chunk_json), 'plan')
                except Exception:
                    continue
                
                final_plan["tasks"].extend(chunk_json.get("tasks", []))
                final_plan["files"].extend(chunk_json.get("files", []))
                
                plan_summary = self.summarize_plan(final_plan)
            
            SchemaValidatorTool()._run(json.dumps(final_plan), 'plan')
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=final_plan,
                metadata={"refined_prompt": refined_prompt},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

    def summarize_plan(self, current_plan: dict) -> str:
        summary = "Generated Files:\n" + "\n".join(
            [f"- {f['file_path']}" for f in current_plan.get("files", [])]
        )
        summary += "\n\nGenerated Tasks:\n" + "\n".join(
            [f"- {t['task']}" for t in current_plan.get("tasks", [])]
        )
        return summary


class StepwiseImplementationTool(BaseTool):
    name: str = "Stepwise Implementation Tool"
    description: str = "Implements tasks one by one from a provided list of tasks."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_implementation",
            description="Implements tasks one by one from a provided list of tasks.",
            parameters=    {
                "tasks": {"type": "array", "description": "A list of tasks to implement, each with 'task' and 'description' fields."}, 
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["tasks"],
            tool_type=ToolType.IMPLEMENTATION,
            keywords=["implement", "task", "stepwise", "code", "develop"],
            examples=[
                {"tasks": [{"task": "Create a user authentication module.", "description": "Implement login and registration."}], "system_instruction": "Use PostgreSQL."}, 
                {"tasks": [{"task": "Design database schema.", "description": "Define tables for users and products."}], "system_instruction": "Use PostgreSQL."}
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            tasks = parameters["tasks"]
            system_instruction = parameters.get("system_instruction")
            
            all_outputs = []
            implementation_summary = ""
            has_errors = False
            
            for idx, task in enumerate(tasks, start=1):
                try:
                    prompt = (
                        f"Implement task {idx}: {task['task']}\n"
                        f"Description: {task['description']}\n"
                        f"Include necessary files and code."
                    )
                    if implementation_summary:
                        prompt += f"\n\nSummary of previously implemented tasks:\n{implementation_summary}"
                    
                    if system_instruction:
                        prompt = f"{system_instruction}\n\n{prompt}"
                    
                    chunk_output = self._llm.generate_with_plan(
                        prompt,
                        system_instruction=system_instruction,
                        chunk_size=512,
                        step_size=256
                    )
                    
                    chunk_json = json.loads(chunk_output)
                    SchemaValidatorTool()._run(json.dumps(chunk_json), 'implementation')
                    all_outputs.append(chunk_json)
                    implementation_summary = self.summarize_implementation(all_outputs)
                except Exception as e:
                    logger.error(f"Error implementing task {task['task']}: {e}")
                    has_errors = True
                    continue
            
            execution_time = time.time() - start_time
            status = ToolExecutionStatus.SUCCESS if not has_errors else ToolExecutionStatus.ERROR
            return ToolResult(
                status=status,
                result=all_outputs,
                metadata={"tasks_count": len(tasks)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

    def summarize_implementation(self, all_outputs: list) -> str:
        summary = "Completed Implementations:\n"
        for output in all_outputs:
            for file_impl in output.get("files", []):
                summary += f"- File: {file_impl['file_path']}, Action: {file_impl['action']}\n"
        return summary

class StepwiseQATool(BaseTool):
    name: str = "Stepwise QA Tool"
    description: str = "Performs quality assurance checks on implemented files based on a plan."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_qa",
            description="Performs quality assurance checks on implemented files based on a plan.",
            parameters=    {
                "implemented_files": {"type": "array", "description": "List of paths to implemented files."},
                "plan": {"type": "object", "description": "The project plan, including declared files."},
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["implemented_files"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["qa", "test", "quality", "assurance", "check", "validate"],
            examples=[
                {"implemented_files": ["src/main.py"], "plan": {"files": [{"path": "src/main.py"}]}},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            implemented_files = parameters["implemented_files"]
            plan = parameters.get("plan", {})
            system_instruction = parameters.get("system_instruction")

            # This is a simplified example. In a real scenario, you'd call the QAModule's logic here.
            # For now, we'll simulate a basic check and LLM interaction.
            qa_report = []
            overall_status = "PASS"

            for fpath in implemented_files:
                # Simulate reading file content (replace with actual file read)
                file_content = f"Content of {fpath}" # Placeholder

                prompt = f"Perform QA on file: {fpath}\nContent:\n{file_content}\n\nPlan details: {json.dumps(plan)}"
                if system_instruction:
                    prompt = f"{system_instruction}\n\n{prompt}"

                # Use LLM for QA analysis (simplified)
                llm_qa_feedback = self._llm.generate_with_plan(
                    prompt,
                    system_instruction=system_instruction,
                    chunk_size=512,
                    step_size=256
                )
                
                # Simulate QA check result
                status = "PASS" if "error" not in llm_qa_feedback.lower() else "FAIL"
                if status == "FAIL":
                    overall_status = "FAIL"

                qa_report.append({
                    "file": fpath,
                    "status": status,
                    "feedback": llm_qa_feedback
                })
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={"qa_report": qa_report, "overall_status": overall_status},
                metadata={"files_checked": len(implemented_files)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

class StepwiseReviewTool(BaseTool):
    name: str = "Stepwise Review Tool"
    description: str = "Performs code review on implemented files."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_review",
            description="Performs code review on implemented files.",
            parameters=    {
                "implemented_files": {"type": "array", "description": "List of paths to implemented files."},
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["implemented_files"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["review", "code", "feedback", "critique", "quality"],
            examples=[
                {"implemented_files": ["src/utils.py"]},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            implemented_files = parameters["implemented_files"]
            system_instruction = parameters.get("system_instruction")

            # This is a simplified example. In a real scenario, you'd call the ReviewModule's logic here.
            # For now, we'll simulate a basic review and LLM interaction.
            review_report = []

            for fpath in implemented_files:
                # Simulate reading file content (replace with actual file read)
                file_content = f"Content of {fpath}" # Placeholder

                prompt = f"Review file: {fpath}\nContent:\n{file_content}"
                if system_instruction:
                    prompt = f"{system_instruction}\n\n{prompt}"

                # Use LLM for review analysis (simplified)
                llm_review_feedback = self._llm.generate_with_plan(
                    prompt,
                    system_instruction=system_instruction,
                    chunk_size=512,
                    step_size=256
                )
                
                review_report.append({
                    "file": fpath,
                    "feedback": llm_review_feedback
                })
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={"review_report": review_report},
                metadata={"files_reviewed": len(implemented_files)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

class ToolRegistry:
    """
    Main tool registry for managing and executing tools
    """
    
    def __init__(self, config_path: Optional[str] = None, llm: Any = None):
        self.tools: Dict[str, BaseTool] = {}
        self.config_path = config_path or "config/tools.yaml"
        self.execution_history: List[Dict[str, Any]] = []
        self.llm = llm # Store the LLM instance
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Load custom tools from config
        self._load_custom_tools()
        
        logger.info(f"Tool registry initialized with {len(self.tools)} tools")
    
    def _register_builtin_tools(self):
        """Register built-in tools"""
        builtin_tools = [
            WebSearchTool(),
            FileOperationTool(),
            CodeAnalysisTool(),
            SystemInfoTool(),
            RobustReplaceTool(), # Add RobustReplaceTool here
            StepwisePlannerTool(llm=self.llm), # Pass LLM to planner tool
            StepwiseImplementationTool(llm=self.llm), # Pass LLM to implementation tool
            StepwiseQATool(llm=self.llm), # Pass LLM to QA tool
            StepwiseReviewTool(llm=self.llm) # Pass LLM to review tool
        ]
        
        for tool in builtin_tools:
            self.register_tool(tool)
    
    def _load_custom_tools(self):
        """Load custom tools from configuration"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                # Load and register custom tools from config
                # This would parse YAML/JSON config and dynamically load tool modules
                pass
        except Exception as e:
            logger.warn(f"Failed to load custom tools: {e}")
    
    def register_tool(self, tool: BaseTool) -> bool:
        """Register a new tool"""
        try:
            self.tools[tool.schema.name] = tool
            logger.info(f"Registered tool: {tool.schema.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool {tool.schema.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                    context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Tool '{tool_name}' not found"
            )
        
        try:
            tool = self.tools[tool_name]
            result = tool.execute(parameters, context)
            
            # Log execution
            self.execution_history.append({
                "tool_name": tool_name,
                "parameters": parameters,
                "result_status": result.status.value,
                "execution_time": result.execution_time,
                "timestamp": time.time()
            })
            
            # Keep only last 100 executions
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            logger.info(f"Executed tool {tool_name}: {result.status.value}")
            return result
            
        except Exception as e:
            error_result = ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Tool execution failed: {str(e)}"
            )
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return error_result
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool"""
        if tool_name in self.tools:
            return self.tools[tool_name].schema.to_dict()
        return None
    
    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by type"""
        tools_info = []
        
        for tool_name, tool in self.tools.items():
            if tool_type is None or tool.schema.tool_type == tool_type:
                tools_info.append({
                    "name": tool_name,
                    "description": tool.schema.description,
                    "type": tool.schema.tool_type.value,
                    "keywords": tool.schema.keywords
                })
        
        return tools_info
    
    def find_tools_by_keywords(self, keywords: List[str]) -> List[str]:
        """Find tools that match given keywords"""
        matching_tools = []
        
        for tool_name, tool in self.tools.items():
            tool_keywords = [kw.lower() for kw in tool.schema.keywords]
            if any(keyword.lower() in tool_keywords for keyword in keywords):
                matching_tools.append(tool_name)
        
        return matching_tools
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        stats = {
            "total_executions": len(self.execution_history),
            "successful_executions": sum(1 for h in self.execution_history if h["result_status"] == "success"),
            "failed_executions": sum(1 for h in self.execution_history if h["result_status"] == "error"),
            "average_execution_time": sum(h.get("execution_time", 0) for h in self.execution_history) / len(self.execution_history)
        }
        
        # Most used tools
        tool_usage = {}
        for h in self.execution_history:
            tool_name = h["tool_name"]
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        stats["most_used_tools"] = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return stats

# Integration with Unified Memory
def create_tool_aware_memory_integration(memory_instance, registry_instance):
    """Create integration between tool registry and unified memory"""
    
    def enhanced_tool_execution(tool_name: str, parameters: Dict[str, Any], 
                              context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute tool and automatically store results in memory"""
        # Execute tool
        result = registry_instance.execute_tool(tool_name, parameters, context)
        
        # Store result in memory
        if result.status == ToolExecutionStatus.SUCCESS:
            from memory.unified_memory import MemoryType
            memory_instance.store_tool_result(
                tool_name=tool_name,
                result=json.dumps(result.result),
                user_id=context.get("user_id", "system") if context else "system",
                metadata={
                    "parameters": json.dumps(parameters),
                    "execution_time": result.execution_time,
                    "status": result.status.value
                }
            )
        
        return result
    
    # Replace the registry's execute_tool method
    registry_instance.execute_tool_with_memory = enhanced_tool_execution
    
    return registry_instance

# Usage example and factory functions
def create_default_tool_registry(llm: Any = None) -> ToolRegistry:
    """Create a tool registry with all built-in tools"""
    return ToolRegistry(llm=llm)

def create_minimal_tool_registry(llm: Any = None) -> ToolRegistry:
    """Create a minimal tool registry with only essential tools"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry.tools = {}
    registry.execution_history = []
    registry.llm = llm
    
    # Register only essential tools
    registry.register_tool(FileOperationTool())
    registry.register_tool(SystemInfoTool())
    
    return registry

if __name__ == "__main__":
    # Example usage
    from memory.unified_memory import UnifiedMemory, MemoryType
    
    # Mock LLM for example usage
    class MockLLM:
        def generate_with_plan(self, prompt, system_instruction=None, chunk_size=512, step_size=256):
            print(f"MockLLM generating for prompt: {prompt[:50]}...")
            # Simulate a simple JSON response for planning/implementation
            if "plan" in prompt.lower():
                return json.dumps({"tasks": [{"task": "Mock Plan Task", "description": "Mock Description"}], "files": []})
            else:
                return json.dumps({"files": [{"file_path": "mock_file.txt", "action": "created"}]})

    mock_llm = MockLLM()
    
    # Create a UnifiedMemory instance
    memory = UnifiedMemory()
    
    # Create registry
    registry = create_default_tool_registry(llm=mock_llm)
    
    # Integrate with UnifiedMemory
    registry = create_tool_aware_memory_integration(memory, registry)
    
    # List available tools
    print("Available tools:")
    for tool_info in registry.list_tools():
        print(f"  - {tool_info['name']}: {tool_info['description']}")
    
    # Execute web search
    search_result = registry.execute_tool_with_memory("web_search", {"query": "Python FastAPI tutorial", "max_results": 3}, context={"user_id": "user123"})
    print(f"\nWeb search result: {search_result.status.value}")
    if search_result.status == ToolExecutionStatus.SUCCESS:
        print(f"Found {len(search_result.result['results'])} results")
    
    # Execute file operation
    file_result = registry.execute_tool_with_memory("file_operation", {"operation": "list", "path": "."}, context={"user_id": "user123"})
    print(f"\nFile operation result: {file_result.status.value}")
    
    # Execute stepwise planner tool
    planner_result = registry.execute_tool_with_memory("stepwise_planner", {"refined_prompt": "Develop a new feature for the e-commerce site"}, context={"user_id": "user123"})
    print(f"\nStepwise Planner result: {planner_result.status.value}")
    if planner_result.status == ToolExecutionStatus.SUCCESS:
        print(f"Planner output: {planner_result.result}")
    
    # Execute stepwise implementation tool
    implementation_tasks = [
        {"task": "Implement user authentication", "description": "Create login and registration endpoints."}, 
        {"task": "Develop product catalog", "description": "Add product listing and detail views."}
    ]
    implementation_result = registry.execute_tool_with_memory("stepwise_implementation", {"tasks": implementation_tasks}, context={"user_id": "user123"})
    print(f"\nStepwise Implementation result: {implementation_result.status.value}")
    if implementation_result.status == ToolExecutionStatus.SUCCESS:
        print(f"Implementation output: {implementation_result.result}")
    
    # Get execution statistics
    stats = registry.get_execution_stats()
    print(f"\nExecution stats: {stats}")
    
    # Query the UnifiedMemory to see if the tool results were stored
    print("\nQuerying UnifiedMemory for tool results...")
    query_results = memory.query("web_search", memory_types=[MemoryType.TOOL_RESULT], user_id="user123")
    print(f"Number of query results: {len(query_results)}")
    for i, res in enumerate(query_results):
        print(f"Result {i+1}:")
        print(f"  Content: {res['content']}")
        print(f"  Metadata: {res['metadata']}")
        print(f"  Similarity: {res['similarity']}")
