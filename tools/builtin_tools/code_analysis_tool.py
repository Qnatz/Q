# tools/builtin_tools/code_analysis_tool.py
"""
Code analysis tool implementation - Enhanced version
"""

import ast
import time
import logging
import re
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class CodeAnalysisTool(BaseTool):
    """Enhanced code analysis with multiple language support and detailed metrics"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="code_analysis",
            description="Comprehensive code analysis including syntax, style, complexity, and security checks",
            parameters={
                "code": {"type": "string", "description": "Code to analyze"},
                "language": {
                    "type": "string", 
                    "description": "Programming language", 
                    "enum": ["python", "javascript", "typescript", "java", "cpp", "c", "go", "rust", "auto"],
                    "default": "auto"
                },
                "analysis_type": {
                    "type": "string", 
                    "enum": ["syntax", "style", "complexity", "security", "all"], 
                    "default": "all"
                },
                "file_path": {"type": "string", "description": "Optional file path for context"},
                "include_fixes": {"type": "boolean", "description": "Include suggested fixes", "default": False}
            },
            required=["code"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["code", "analyze", "syntax", "style", "lint", "complexity", "security"],
            examples=[
                {"code": "def hello():\n    print('Hello')", "language": "python"},
                {"code": "function test() { return true; }", "language": "javascript", "analysis_type": "syntax"},
                {"code": "def vulnerable(user_input):\n    eval(user_input)", "language": "python", "analysis_type": "security"}
            ]
        )
    
    def _detect_language(self, code: str, file_path: Optional[str] = None) -> str:
        """Detect programming language from code and file extension"""
        if file_path:
            path = Path(file_path)
            ext_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust'
            }
            if path.suffix in ext_map:
                return ext_map[path.suffix]
        
        # Language detection heuristics
        if re.search(r'\bdef\s+\w+\s*\(', code) or 'import ' in code or 'from ' in code:
            return 'python'
        elif re.search(r'\bfunction\s+\w+\s*\(', code) or 'const ' in code or 'let ' in code:
            return 'javascript'
        elif re.search(r'\bpublic\s+class\s+\w+', code) or 'System.out.println' in code:
            return 'java'
        elif '#include' in code and ('int main(' in code or 'void main(' in code):
            return 'c' if '.h"' in code else 'cpp'
        
        return 'python'  # Default fallback
    
    def _analyze_python_syntax(self, code: str) -> Dict[str, Any]:
        """Analyze Python syntax using AST"""
        issues = []
        metrics = {}
        
        try:
            tree = ast.parse(code)
            
            # Count different node types
            node_counts = {}
            for node in ast.walk(tree):
                node_type = type(node).__name__
                node_counts[node_type] = node_counts.get(node_type, 0) + 1
            
            metrics.update({
                "functions": node_counts.get('FunctionDef', 0),
                "classes": node_counts.get('ClassDef', 0),
                "imports": node_counts.get('Import', 0) + node_counts.get('ImportFrom', 0),
                "loops": node_counts.get('For', 0) + node_counts.get('While', 0),
                "conditionals": node_counts.get('If', 0),
                "try_blocks": node_counts.get('Try', 0)
            })
            
            return {"syntax_valid": True, "issues": issues, "metrics": metrics}
            
        except SyntaxError as e:
            issues.append({
                "type": "syntax_error",
                "message": str(e),
                "line": getattr(e, 'lineno', None),
                "offset": getattr(e, 'offset', None),
                "severity": "error"
            })
            return {"syntax_valid": False, "issues": issues, "metrics": metrics}
    
    def _analyze_style_issues(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Analyze code style issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Common style issues
            if len(line) > 100:
                issues.append({
                    "type": "style_warning",
                    "message": f"Line too long ({len(line)} characters)",
                    "line": i,
                    "severity": "warning"
                })
            
            if line.rstrip() != line:
                issues.append({
                    "type": "style_warning", 
                    "message": "Trailing whitespace",
                    "line": i,
                    "severity": "info"
                })
            
            # Language-specific style checks
            if language == 'python':
                if re.search(r'\t', line):
                    issues.append({
                        "type": "style_warning",
                        "message": "Use spaces instead of tabs",
                        "line": i,
                        "severity": "warning"
                    })
                
                # Check for PEP 8 naming conventions
                if re.search(r'\bdef [A-Z]', line):
                    issues.append({
                        "type": "style_warning",
                        "message": "Function names should be lowercase with underscores",
                        "line": i,
                        "severity": "info"
                    })
        
        return issues
    
    def _calculate_complexity(self, code: str, language: str) -> Dict[str, Any]:
        """Calculate cyclomatic complexity and other metrics"""
        complexity_metrics = {
            "cyclomatic_complexity": 1,  # Base complexity
            "cognitive_complexity": 0,
            "nesting_depth": 0,
            "maintainability_index": 100
        }
        
        if language == 'python':
            try:
                tree = ast.parse(code)
                
                class ComplexityVisitor(ast.NodeVisitor):
                    def __init__(self):
                        self.complexity = 1
                        self.cognitive = 0
                        self.max_depth = 0
                        self.current_depth = 0
                    
                    def visit_If(self, node):
                        self.complexity += 1
                        self.cognitive += 1
                        self.current_depth += 1
                        self.max_depth = max(self.max_depth, self.current_depth)
                        self.generic_visit(node)
                        self.current_depth -= 1
                    
                    def visit_For(self, node):
                        self.complexity += 1
                        self.cognitive += 1
                        self.current_depth += 1
                        self.max_depth = max(self.max_depth, self.current_depth)
                        self.generic_visit(node)
                        self.current_depth -= 1
                    
                    def visit_While(self, node):
                        self.complexity += 1
                        self.cognitive += 1
                        self.current_depth += 1
                        self.max_depth = max(self.max_depth, self.current_depth)
                        self.generic_visit(node)
                        self.current_depth -= 1
                    
                    def visit_Try(self, node):
                        self.complexity += len(node.handlers)
                        self.cognitive += 1
                        self.generic_visit(node)
                
                visitor = ComplexityVisitor()
                visitor.visit(tree)
                
                complexity_metrics.update({
                    "cyclomatic_complexity": visitor.complexity,
                    "cognitive_complexity": visitor.cognitive,
                    "nesting_depth": visitor.max_depth
                })
                
            except SyntaxError:
                pass
        else:
            # Simple heuristic for other languages
            control_patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bcatch\b', r'\bcase\b']
            for pattern in control_patterns:
                complexity_metrics["cyclomatic_complexity"] += len(re.findall(pattern, code, re.IGNORECASE))
        
        # Calculate maintainability index (simplified)
        lines_of_code = len([line for line in code.split('\n') if line.strip()])
        complexity_metrics["maintainability_index"] = max(0, 100 - complexity_metrics["cyclomatic_complexity"] * 5 - lines_of_code * 0.1)
        
        return complexity_metrics
    
    def _check_security_issues(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Check for common security vulnerabilities"""
        issues = []
        lines = code.split('\n')
        
        security_patterns = {
            'python': [
                (r'\beval\s*\(', "Use of eval() can be dangerous"),
                (r'\bexec\s*\(', "Use of exec() can be dangerous"),
                (r'subprocess\.(call|run|Popen).*shell=True', "Shell injection vulnerability"),
                (r'pickle\.loads?\(', "Pickle deserialization can be unsafe"),
                (r'__import__\s*\(', "Dynamic imports can be dangerous"),
                (r'open\s*\([^)]*[\'"][rw][+]*[\'"]', "File operations without proper validation")
            ],
            'javascript': [
                (r'\beval\s*\(', "Use of eval() can be dangerous"),
                (r'innerHTML\s*=', "Potential XSS vulnerability"),
                (r'document\.write\s*\(', "Use of document.write can be dangerous"),
                (r'setTimeout\s*\([\'"].*[\'"]', "String-based setTimeout can be dangerous")
            ]
        }
        
        patterns = security_patterns.get(language, [])
        
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "security_warning",
                        "message": message,
                        "line": i,
                        "code_snippet": line.strip(),
                        "severity": "high"
                    })
        
        return issues
    
    def _suggest_fixes(self, issues: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
        """Suggest fixes for identified issues"""
        fixes = []
        
        for issue in issues:
            fix_suggestion = None
            
            if "eval()" in issue.get("message", ""):
                fix_suggestion = "Consider using ast.literal_eval() for safe evaluation of literals"
            elif "Line too long" in issue.get("message", ""):
                fix_suggestion = "Break long lines using parentheses or backslash continuation"
            elif "Trailing whitespace" in issue.get("message", ""):
                fix_suggestion = "Remove trailing whitespace characters"
            elif "shell=True" in issue.get("message", ""):
                fix_suggestion = "Use shell=False and pass arguments as a list instead"
            
            if fix_suggestion:
                fixes.append({
                    "line": issue.get("line"),
                    "issue_type": issue.get("type"),
                    "suggestion": fix_suggestion
                })
        
        return fixes

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            code = parameters["code"]
            language = parameters.get("language", "auto")
            analysis_type = parameters.get("analysis_type", "all")
            file_path = parameters.get("file_path")
            include_fixes = parameters.get("include_fixes", False)
            
            # Auto-detect language if needed
            if language == "auto":
                language = self._detect_language(code, file_path)
            
            # Initialize result structure
            analysis_result = {
                "language": language,
                "file_path": file_path,
                "lines_of_code": len([line for line in code.split('\n') if line.strip()]),
                "total_lines": len(code.split('\n')),
                "character_count": len(code),
                "issues": [],
                "metrics": {},
                "summary": {}
            }
            
            # Syntax analysis
            if analysis_type in ["syntax", "all"]:
                if language == "python":
                    syntax_result = self._analyze_python_syntax(code)
                    analysis_result["syntax_valid"] = syntax_result["syntax_valid"]
                    analysis_result["issues"].extend(syntax_result["issues"])
                    analysis_result["metrics"].update(syntax_result["metrics"])
                else:
                    # Basic syntax check for other languages (placeholder)
                    analysis_result["syntax_valid"] = True
            
            # Style analysis
            if analysis_type in ["style", "all"]:
                style_issues = self._analyze_style_issues(code, language)
                analysis_result["issues"].extend(style_issues)
            
            # Complexity analysis
            if analysis_type in ["complexity", "all"]:
                complexity_metrics = self._calculate_complexity(code, language)
                analysis_result["metrics"].update(complexity_metrics)
            
            # Security analysis
            if analysis_type in ["security", "all"]:
                security_issues = self._check_security_issues(code, language)
                analysis_result["issues"].extend(security_issues)
            
            # Generate summary
            issue_counts = {}
            for issue in analysis_result["issues"]:
                severity = issue.get("severity", "info")
                issue_counts[severity] = issue_counts.get(severity, 0) + 1
            
            analysis_result["summary"] = {
                "total_issues": len(analysis_result["issues"]),
                "issue_breakdown": issue_counts,
                "complexity_rating": self._get_complexity_rating(analysis_result["metrics"].get("cyclomatic_complexity", 1)),
                "maintainability_rating": self._get_maintainability_rating(analysis_result["metrics"].get("maintainability_index", 100))
            }
            
            # Include fix suggestions if requested
            if include_fixes:
                analysis_result["suggested_fixes"] = self._suggest_fixes(analysis_result["issues"], code)
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=analysis_result,
                metadata={
                    "language": language, 
                    "analysis_type": analysis_type,
                    "total_issues": analysis_result["summary"]["total_issues"]
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Code analysis failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _get_complexity_rating(self, complexity: int) -> str:
        """Get human-readable complexity rating"""
        if complexity <= 5:
            return "Low"
        elif complexity <= 10:
            return "Moderate"
        elif complexity <= 20:
            return "High"
        else:
            return "Very High"
    
    def _get_maintainability_rating(self, index: float) -> str:
        """Get human-readable maintainability rating"""
        if index >= 85:
            return "Excellent"
        elif index >= 70:
            return "Good"
        elif index >= 50:
            return "Fair"
        else:
            return "Poor"
