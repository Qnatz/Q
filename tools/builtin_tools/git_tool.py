# tools/builtin_tools/git_tool.py
"""
Git tool implementation - Enhanced with real Git operations using GitPython
"""

import time
import logging
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class GitTool(BaseTool):
    """Enhanced Git operations with comprehensive functionality and error handling"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_operations",
            description="Perform comprehensive Git operations with detailed status reporting",
            parameters={
                "operation": {
                    "type": "string", 
                    "enum": ["status", "add", "commit", "push", "pull", "clone", "init", "branch", "checkout", "merge", "log", "diff", "reset", "stash"],
                    "description": "Git operation to perform"
                },
                "message": {"type": "string", "description": "Commit message (for commit operation)"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Files to add (for add operation)"},
                "remote": {"type": "string", "description": "Remote repository URL or name", "default": "origin"},
                "branch": {"type": "string", "description": "Branch name"},
                "target_branch": {"type": "string", "description": "Target branch for merge operations"},
                "repository_url": {"type": "string", "description": "Repository URL for clone operation"},
                "path": {"type": "string", "description": "Repository path", "default": "."},
                "force": {"type": "boolean", "description": "Force operation (use with caution)", "default": False},
                "all_files": {"type": "boolean", "description": "Add all files (for add operation)", "default": False},
                "max_log_entries": {"type": "integer", "description": "Maximum log entries to return", "default": 10}
            },
            required=["operation"],
            tool_type=ToolType.FILE_OPERATION,
            keywords=["git", "version", "control", "repository", "commit", "push", "branch", "merge"],
            examples=[
                {"operation": "status", "path": "./project"},
                {"operation": "add", "files": ["src/main.py"], "path": "."},
                {"operation": "commit", "message": "Add new feature", "path": "."},
                {"operation": "push", "remote": "origin", "branch": "main"}
            ]
        )
    
    def _run_git_command(self, cmd: List[str], cwd: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a git command and return structured result"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "command": ' '.join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "command": ' '.join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": ' '.join(cmd)
            }
    
    def _parse_git_status(self, status_output: str) -> Dict[str, Any]:
        """Parse git status output into structured format"""
        status_info = {
            "branch": None,
            "tracking_branch": None,
            "ahead": 0,
            "behind": 0,
            "staged_files": [],
            "modified_files": [],
            "untracked_files": [],
            "deleted_files": [],
            "renamed_files": [],
            "clean": False
        }
        
        lines = status_output.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('On branch '):
                status_info["branch"] = line.replace('On branch ', '')
            elif 'Your branch is ahead of' in line:
                # Extract ahead count
                import re
                match = re.search(r'ahead of .+ by (\d+) commit', line)
                if match:
                    status_info["ahead"] = int(match.group(1))
            elif 'Your branch is behind' in line:
                # Extract behind count
                import re
                match = re.search(r'behind .+ by (\d+) commit', line)
                if match:
                    status_info["behind"] = int(match.group(1))
            elif line.startswith('new file:'):
                status_info["staged_files"].append(line.replace('new file:', '').strip())
            elif line.startswith('modified:'):
                status_info["modified_files"].append(line.replace('modified:', '').strip())
            elif line.startswith('deleted:'):
                status_info["deleted_files"].append(line.replace('deleted:', '').strip())
            elif line.startswith('renamed:'):
                status_info["renamed_files"].append(line.replace('renamed:', '').strip())
            elif line and not line.startswith(('Changes', 'Untracked', '\t', ' ', '#')):
                # Untracked files
                if '.' in line or '/' in line:
                    status_info["untracked_files"].append(line)
        
        # Check if working directory is clean
        status_info["clean"] = (
            len(status_info["staged_files"]) == 0 and
            len(status_info["modified_files"]) == 0 and
            len(status_info["untracked_files"]) == 0 and
            len(status_info["deleted_files"]) == 0
        )
        
        return status_info
    
    def _parse_git_log(self, log_output: str, max_entries: int) -> List[Dict[str, Any]]:
        """Parse git log output into structured format"""
        commits = []
        current_commit = {}
        
        for line in log_output.split('\n'):
            if line.startswith('commit '):
                if current_commit:
                    commits.append(current_commit)
                    if len(commits) >= max_entries:
                        break
                current_commit = {"hash": line.split()[1][:8]}
            elif line.startswith('Author: '):
                current_commit["author"] = line.replace('Author: ', '')
            elif line.startswith('Date: '):
                current_commit["date"] = line.replace('Date: ', '').strip()
            elif line.strip() and not line.startswith(('commit', 'Author', 'Date')):
                current_commit["message"] = line.strip()
        
        if current_commit and len(commits) < max_entries:
            commits.append(current_commit)
        
        return commits[:max_entries]

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            operation = parameters["operation"]
            path = Path(parameters.get("path", ".")).resolve()
            
            # Validate path exists
            if not path.exists():
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"Path does not exist: {path}"
                )
            
            # Check if it's a git repository (except for init and clone)
            if operation not in ["init", "clone"]:
                git_dir = path / ".git"
                if not git_dir.exists():
                    return ToolResult(
                        status=ToolExecutionStatus.ERROR,
                        result=None,
                        error_message=f"Not a git repository: {path}"
                    )
            
            result = {"operation": operation, "path": str(path)}
            
            if operation == "status":
                cmd_result = self._run_git_command(["git", "status", "--porcelain", "-b"], str(path))
                if cmd_result["success"]:
                    # Also get detailed status
                    detailed_result = self._run_git_command(["git", "status"], str(path))
                    status_info = self._parse_git_status(detailed_result["stdout"])
                    result.update(status_info)
                    result["raw_output"] = cmd_result["stdout"]
                else:
                    result.update(cmd_result)
                    
            elif operation == "add":
                files = parameters.get("files", [])
                all_files = parameters.get("all_files", False)
                
                if all_files:
                    cmd_result = self._run_git_command(["git", "add", "."], str(path))
                elif files:
                    cmd_result = self._run_git_command(["git", "add"] + files, str(path))
                else:
                    return ToolResult(
                        status=ToolExecutionStatus.ERROR,
                        result=None,
                        error_message="Either 'files' or 'all_files=True' must be specified"
                    )
                
                result.update(cmd_result)
                if cmd_result["success"]:
                    result["added_files"] = files if files else ["all files"]
                    
            elif operation == "commit":
                message = parameters.get("message")
                if not message:
                    return ToolResult(
                        status=ToolExecutionStatus.ERROR,
                        result=None,
                        error_message="Commit message is required"
                    )
                
                cmd_result = self._run_git_command(["git", "commit", "-m", message], str(path))
                result.update(cmd_result)
                if cmd_result["success"]:
                    result["message"] = message
                    # Extract commit hash from output
                    import re
                    match = re.search(r'\[.+ ([a-f0-9]+)\]', cmd_result["stdout"])
                    if match:
                        result["commit_hash"] = match.group(1)
                        
            elif operation == "push":
                remote = parameters.get("remote", "origin")
                branch = parameters.get("branch")
                
                cmd = ["git", "push", remote]
                if branch:
                    cmd.append(branch)
                
                cmd_result = self._run_git_command(cmd, str(path))
                result.update(cmd_result)
                result["remote"] = remote
                result["branch"] = branch
                
            elif operation == "pull":
                remote = parameters.get("remote", "origin")
                branch = parameters.get("branch")
                
                cmd = ["git", "pull", remote]
                if branch:
                    cmd.append(branch)
                
                cmd_result = self._run_git_command(cmd, str(path))
                result.update(cmd_result)
                result["remote"] = remote
                result["branch"] = branch
                
            elif operation == "clone":
                repository_url = parameters.get("repository_url")
                if not repository_url:
                    return ToolResult(
                        status=ToolExecutionStatus.ERROR,
                        result=None,
                        error_message="repository_url is required for clone operation"
                    )
                
                cmd_result = self._run_git_command(["git", "clone", repository_url], str(path.parent))
                result.update(cmd_result)
                result["repository_url"] = repository_url
                
            elif operation == "init":
                cmd_result = self._run_git_command(["git", "init"], str(path))
                result.update(cmd_result)
                
            elif operation == "branch":
                branch_name = parameters.get("branch")
                if branch_name:
                    # Create new branch
                    cmd_result = self._run_git_command(["git", "branch", branch_name], str(path))
                    result["new_branch"] = branch_name
                else:
                    # List branches
                    cmd_result = self._run_git_command(["git", "branch", "-a"], str(path))
                    if cmd_result["success"]:
                        branches = [line.strip().lstrip('* ') for line in cmd_result["stdout"].split('\n') if line.strip()]
                        result["branches"] = branches
                
                result.update(cmd_result)
                
            elif operation == "checkout":
                branch = parameters.get("branch")
                if not branch:
                    return ToolResult(
                        status=ToolExecutionStatus.ERROR,
                        result=None,
                        error_message="branch is required for checkout operation"
                    )
                
                cmd_result = self._run_git_command(["git", "checkout", branch], str(path))
                result.update(cmd_result)
                result["checked_out_branch"] = branch
                
            elif operation == "log":
                max_entries = parameters.get("max_log_entries", 10)
                cmd_result = self._run_git_command(["git", "log", f"-{max_entries}", "--oneline"], str(path))
                
                if cmd_result["success"]:
                    # Get detailed log
                    detailed_result = self._run_git_command(["git", "log", f"-{max_entries}"], str(path))
                    commits = self._parse_git_log(detailed_result["stdout"], max_entries)
                    result["commits"] = commits
                    result["total_commits"] = len(commits)
                
                result.update(cmd_result)
                
            elif operation == "diff":
                cmd_result = self._run_git_command(["git", "diff"], str(path))
                result.update(cmd_result)
                if cmd_result["success"]:
                    result["has_changes"] = bool(cmd_result["stdout"])
                    
            elif operation == "stash":
                cmd_result = self._run_git_command(["git", "stash"], str(path))
                result.update(cmd_result)
                
            else:
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"Unknown operation: {operation}"
                )
            
            execution_time = time.time() - start_time
            
            # Determine status based on command success
            status = ToolExecutionStatus.SUCCESS if result.get("success", False) else ToolExecutionStatus.ERROR
            error_message = result.get("stderr") if not result.get("success") else None
            
            return ToolResult(
                status=status,
                result=result,
                metadata={"operation": operation, "path": str(path)},
                execution_time=execution_time,
                error_message=error_message
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Git operation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
