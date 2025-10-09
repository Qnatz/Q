"""
Professional QA Module
Combines file validation, plan verification, and comprehensive reporting
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Generator
from dataclasses import dataclass
from enum import Enum

from tools.base_tool_classes import ToolExecutionStatus # Added import

logger = logging.getLogger(__name__)

class QAStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    PARTIAL = "partial"

@dataclass
class QAFileResult:
    """Individual file QA result"""
    file_path: str
    status: str
    feedback: str
    exists: bool
    is_empty: bool
    file_size: int = 0

@dataclass
class QASummary:
    """Overall QA summary"""
    total_files: int
    passed: int
    failed: int
    missing: int
    overall_status: QAStatus
    execution_time: float = 0.0

class QAModule:
    """
    QA Module with comprehensive testing and reporting
    Features:
    - File existence and content validation
    - Plan compliance checking
    - Multiple report formats (JSON, Markdown)
    - Robust error handling
    - Detailed analytics
    """

    def __init__(self, tool_registry, reports_dir: str = "project_state"):
        self.tool_registry = tool_registry
        self.reports_dir = Path(reports_dir)
        self._file_cache = {}  # NEW: Cache for file content
        self._validation_cache = {}  # NEW: Cache validation results
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create necessary directories"""
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_file_paths(self, implemented_files: List[str], project_id: Optional[str] = None) -> List[str]:
        """Resolve file paths to be absolute"""
        absolute_files = []
        for file_path in implemented_files:
            if file_path.startswith('/'):
                # Already absolute
                absolute_files.append(file_path)
            else:
                # Use consistent project directory
                base_dir = f"/root/Q/projects/{project_id.lower()}" if project_id else "/root/Q/projects"
                absolute_path = str(Path(base_dir) / file_path)
                absolute_files.append(absolute_path)
        return absolute_files

    def progressive_test(self, implemented_files: List[str], 
                       project_id: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Progressive QA that validates files as they're implemented"""
        absolute_files = self._resolve_file_paths(implemented_files, project_id)
        
        # Deduplicate files
        unique_files = list(dict.fromkeys(absolute_files))
        
        total_files = len(unique_files)
        validated_count = 0
        
        for file_path in unique_files:
            # Skip if already validated in this session
            if file_path in self._validation_cache:
                result = self._validation_cache[file_path]
                validated_count += 1
                yield {
                    "type": "file_validated",
                    "file": file_path,
                    "status": result.status,
                    "progress": f"{validated_count}/{total_files}",
                    "cached": True
                }
                continue
            
            # Validate individual file
            result = self._validate_file(file_path)
            self._validation_cache[file_path] = result
            
            validated_count += 1
            yield {
                "type": "file_validated", 
                "file": file_path,
                "status": result.status,
                "feedback": result.feedback,
                "progress": f"{validated_count}/{total_files}",
                "cached": False
            }
            
            # Small delay to allow UI updates
            import time
            time.sleep(0.1)
        
        # Final summary
        summary = self._generate_summary(list(self._validation_cache.values()), 0)
        yield {
            "type": "qa_complete",
            "status": summary.overall_status.value,
            "passed": summary.passed,
            "total": summary.total_files
        }

    def _validate_file(self, file_path: str) -> QAFileResult:
        """Enhanced file validation with caching"""
        # Check cache first
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        
        path = Path(file_path)
        
        if not path.exists():
            result = QAFileResult(
                file_path=file_path,
                status="missing",
                feedback="File does not exist",
                exists=False,
                is_empty=True
            )
            self._file_cache[file_path] = result
            return result
        
        try:
            file_size = path.stat().st_size
            is_empty = file_size == 0
            
            # For non-empty files, do quick content validation
            feedback = "File exists and is non-empty"
            status = "passed"
            
            if not is_empty:
                # Quick syntax check for common file types
                syntax_ok = self._quick_syntax_check(file_path)
                if not syntax_ok:
                    status = "failed"
                    feedback = "File exists but has syntax issues"
            
            result = QAFileResult(
                file_path=file_path,
                status=status,
                feedback=feedback,
                exists=True,
                is_empty=is_empty,
                file_size=file_size
            )
            
            self._file_cache[file_path] = result
            return result
            
        except Exception as e:
            result = QAFileResult(
                file_path=file_path,
                status="error",
                feedback=f"Error checking file: {str(e)}",
                exists=False,
                is_empty=True
            )
            self._file_cache[file_path] = result
            return result

    def _quick_syntax_check(self, file_path: str) -> bool:
        """Quick syntax validation for common file types"""
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    json.load(f)
                return True
            elif file_path.endswith('.py'):
                # Basic Python syntax check
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                return True
            elif file_path.endswith(('.yaml', '.yml')):
                import yaml
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
                return True
        except:
            return False
        
        return True  # For other file types, assume valid

    def _check_plan_compliance(self, implemented_files: List[str], 
                             plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check if implemented files match planned files"""
        if not plan:
            return {"compliance_check": False, "message": "No plan provided for compliance check"}
        
        # Extract only the file paths from the planned files (which are dictionaries)
        planned_file_paths = [f.get("path") for f in plan.get("files", []) if isinstance(f, dict) and "path" in f]
        
        implemented_set = set(implemented_files)
        planned_set = set(planned_file_paths)
        
        missing_files = planned_set - implemented_set
        extra_files = implemented_set - planned_set
        
        return {
            "compliance_check": len(missing_files) == 0,
            "missing_files": list(missing_files),
            "extra_files": list(extra_files),
            "planned_file_count": len(planned_set),
            "implemented_file_count": len(implemented_set)
        }

    def _generate_summary(self, file_results: List[QAFileResult], 
                        execution_time: float) -> QASummary:
        """Generate QA summary statistics"""
        total = len(file_results)
        passed = len([r for r in file_results if r.status == "passed"])
        failed = len([r for r in file_results if r.status == "failed"])
        missing = len([r for r in file_results if r.status == "missing"])
        
        if passed == total:
            overall_status = QAStatus.SUCCESS
        elif failed == 0 and missing == 0:
            overall_status = QAStatus.SUCCESS
        elif passed > 0 and (failed > 0 or missing > 0):
            overall_status = QAStatus.PARTIAL
        else:
            overall_status = QAStatus.FAILED
            
        return QASummary(
            total_files=total,
            passed=passed,
            failed=failed,
            missing=missing,
            overall_status=overall_status,
            execution_time=execution_time
        )

    def _create_markdown_report(self, file_results: List[QAFileResult], 
                              summary: QASummary,
                              compliance: Dict[str, Any],
                              timestamp: str) -> str:
        """Generate comprehensive Markdown report"""
        report = [
            f"# QA Test Report",
            f"**Generated:** {timestamp}",
            f"**Overall Status:** `{summary.overall_status.value}`",
            f"**Execution Time:** {summary.execution_time:.2f}s",
            "",
            "## Summary",
            f"- **Total Files:** {summary.total_files}",
            f"- **✅ Passed:** {summary.passed}",
            f"- **❌ Failed:** {summary.failed}",
            f"- **📁 Missing:** {summary.missing}",
            "",
            "## Plan Compliance",
            f"- **Compliance Check:** {'✅ Passed' if compliance.get('compliance_check') else '❌ Failed'}",
            f"- **Missing Files:** {len(compliance.get('missing_files', []))}",
            f"- **Extra Files:** {len(compliance.get('extra_files', []))}",
            "",
            "## File Details",
            "| File | Status | Size | Feedback |",
            "|------|--------|------|----------|"
        ]
        
        status_emojis = {"passed": "✅", "failed": "❌", "missing": "📁", "error": "⚠️"}
        
        for result in file_results:
            emoji = status_emojis.get(result.status, "❓")
            size_str = f"{result.file_size} bytes" if result.exists else "N/A"
            report.append(f"| {result.file_path} | {emoji} {result.status} | {size_str} | {result.feedback} |")
        
        return "\n".join(report)

    def _create_json_report(self, file_results: List[QAFileResult],
                          summary: QASummary,
                          compliance: Dict[str, Any],
                          timestamp: str) -> Dict[str, Any]:
        """Generate comprehensive JSON report"""
        return {
            "metadata": {
                "timestamp": timestamp,
                "report_version": "1.0",
                "module": "QAModule"
            },
            "summary": {
                "total_files": summary.total_files,
                "passed": summary.passed,
                "failed": summary.failed,
                "missing": summary.missing,
                "overall_status": summary.overall_status.value,
                "execution_time": summary.execution_time
            },
            "compliance": compliance,
            "file_details": [
                {
                    "file_path": result.file_path,
                    "status": result.status,
                    "feedback": result.feedback,
                    "exists": result.exists,
                    "is_empty": result.is_empty,
                    "file_size": result.file_size
                }
                for result in file_results
            ]
        }

    def test(self, implemented_files: List[str], 
             plan: Optional[Dict[str, Any]] = None,
             project_id: Optional[str] = None) -> Dict[str, str]:
        start_time = datetime.now()
        timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Starting professional QA testing on {len(implemented_files)} files")
        
        # FIX: Better path resolution
        absolute_files = []
        for file_path in implemented_files:
            if file_path.startswith('/'):
                # Already absolute
                absolute_files.append(file_path)
            else:
                # Use consistent project directory
                base_dir = f"/root/Q/projects/{project_id.lower()}" if project_id else "/root/Q/projects"
                absolute_path = str(Path(base_dir) / file_path)
                absolute_files.append(absolute_path)
        
        implemented_files = absolute_files
        logger.info(f"Resolved file paths: {implemented_files}")

        report_paths = {}
        
        try:
            # Step 1: Basic file validation
            file_results = []
            for file_path in implemented_files:
                result = self._validate_file(file_path)
                file_results.append(result)
                logger.debug(f"File validation: {file_path} - {result.status}")

            # Step 2: Plan compliance checking
            compliance = self._check_plan_compliance(implemented_files, plan)
            
            # Step 3: Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Step 4: Generate summary
            summary = self._generate_summary(file_results, execution_time)
            
            # Step 5: Generate reports
            markdown_report = self._create_markdown_report(
                file_results, summary, compliance, timestamp
            )
            
            json_report = self._create_json_report(
                file_results, summary, compliance, timestamp
            )
            
            # Step 6: Save reports
            md_path = self.reports_dir / "qa_test_report.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_report)
            report_paths["markdown"] = str(md_path)
            
            json_path = self.reports_dir / "qa_test_report.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_report, f, indent=2, ensure_ascii=False)
            report_paths["json"] = str(json_path)
            
            # Step 7: Advanced QA with tool if available
            if self.tool_registry:
                try:
                    tool_result = self.tool_registry.execute_tool(
                        "stepwise_qa",
                        {
                            "implemented_files": implemented_files,
                            "plan": plan or {}
                        }
                    )
                    
                    if tool_result and hasattr(tool_result, 'status'):
                        tool_report_path = self.reports_dir / "advanced_qa_report.json"
                        with open(tool_report_path, "w", encoding="utf-8") as f:
                            json.dump({
                                "tool_status": getattr(tool_result, 'status', 'unknown').value if hasattr(tool_result, 'status') and isinstance(getattr(tool_result, 'status'), ToolExecutionStatus) else getattr(tool_result, 'status', 'unknown'),
                                "tool_result": getattr(tool_result, 'result', {}),
                                "error_message": getattr(tool_result, 'error_message', None),
                                "execution_time": getattr(tool_result, 'execution_time', 0),
                                "metadata": getattr(tool_result, 'metadata', {})
                            }, f, indent=2)
                        report_paths["advanced"] = str(tool_report_path)
                        
                except Exception as tool_error:
                    logger.warning(f"Advanced QA tool failed: {tool_error}")
            
            # Step 8: Log results
            status_emoji = "✅" if summary.overall_status == QAStatus.SUCCESS else "❌"
            logger.info(
                f"{status_emoji} QA testing completed: "
                f"{summary.passed}/{summary.total_files} files passed "
                f"(Status: {summary.overall_status.value})"
            )
            
            return report_paths
            
        except Exception as e:
            logger.error(f"QA testing failed: {e}")
            
            # Create error reports
            error_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_report = self._create_error_reports(str(e), implemented_files, error_timestamp)
            
            return error_report

    def _create_error_reports(self, error: str, implemented_files: List[str], 
                            timestamp: str) -> Dict[str, str]:
        """Create error reports when QA fails"""
        error_data = {
            "error": error,
            "timestamp": timestamp,
            "files_attempted": implemented_files,
            "status": "error"
        }
        
        # JSON error report
        json_path = self.reports_dir / "qa_error_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(error_data, f, indent=2)
        
        # Markdown error report
        md_content = [
            "# QA Error Report",
            f"**Timestamp:** {timestamp}",
            f"**Error:** {error}",
            "",
            "## Files Attempted",
            *[f"- {file}" for file in implemented_files]
        ]
        
        md_path = self.reports_dir / "qa_error_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
        
        return {"markdown": str(md_path), "json": str(json_path), "error": str(json_path)}

    def get_quick_status(self, implemented_files: List[str]) -> Dict[str, Any]:
        """
        Quick status check without full reporting
        Useful for progress monitoring
        """
        file_results = [self._validate_file(f) for f in implemented_files]
        summary = self._generate_summary(file_results, 0)
        
        return {
            "overall_status": summary.overall_status.value,
            "passed_files": summary.passed,
            "total_files": summary.total_files,
            "progress_percentage": (summary.passed / summary.total_files * 100) if summary.total_files > 0 else 0
        }
