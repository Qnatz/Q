# tools/builtin_tools/shell_tool.py
"""
Shell command tool implementation - Enhanced with security and better error handling
"""

import subprocess
import time
import logging
import shlex
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class ShellTool(BaseTool):
    """Enhanced shell command execution with security controls and better output handling"""
    
    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = {
        'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs',
        'dd', 'shutdown', 'reboot', 'halt', 'init', 'passwd',
        'su', 'sudo', 'chmod 777', 'chown', 'killall'
    }
    
    # Safe commands that are explicitly allowed
    SAFE_COMMANDS = {
        'ls', 'dir', 'pwd', 'whoami', 'id', 'date', 'echo',
        'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort',
        'ps', 'top', 'df', 'free', 'uname', 'which', 'whereis',
        'git', 'python', 'pip', 'npm', 'node', 'java', 'javac',
        'gcc', 'make', 'cmake', 'curl', 'wget', 'ping'
    }
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="shell_command",
            description="Execute shell commands safely with security controls and comprehensive output",
            parameters={
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "working_dir": {"type": "string", "description": "Working directory", "default": "."},
                "env_vars": {"type": "object", "description": "Additional environment variables"},
                "capture_output": {"type": "boolean", "description": "Capture stdout/stderr", "default": True},
                "shell_type": {"type": "string", "enum": ["bash", "sh", "cmd", "powershell"], "default": "bash"},
                "allow_dangerous": {"type": "boolean", "description": "Allow potentially dangerous commands", "default": False},
                "max_output_size": {"type": "integer", "description": "Maximum output size in bytes", "default": 1048576}
            },
            required=["command"],
            tool_type=ToolType.SYSTEM_INFO,
            keywords=["shell", "command", "terminal", "execute", "bash", "cmd", "system"],
            examples=[
                {"command": "ls -la", "working_dir": "./project"},
                {"command": "python --version"},
                {"command": "git status", "timeout": 10}
            ]
        )
    
    def _validate_command_safety(self, command: str, allow_dangerous: bool = False) -> tuple[bool, str]:
        """Validate if command is safe to execute"""
        command_parts = shlex.split(command.lower()) if command else []
        
        if not command_parts:
            return False, "Empty command"
        
        main_command = command_parts[0].split('/')[-1]  # Get command name without path
        
        # Check for dangerous commands
        for dangerous_cmd in self.DANGEROUS_COMMANDS:
            if dangerous_cmd in command.lower():
                if not allow_dangerous:
                    return False, f"Dangerous command detected: {dangerous_cmd}"
                else:
                    logger.warning(f"Allowing dangerous command: {dangerous_cmd}")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'>\s*/dev/',  # Redirecting to device files
            r'&\s*$',      # Background execution
            r';\s*(rm|del)', # Command chaining with deletion
            r'\|\s*sh',    # Piping to shell
            r'`[^`]+`',    # Command substitution
            r'\$\([^)]+\)' # Command substitution
        ]
        
        import re
        for pattern in suspicious_patterns:
            if re.search(pattern, command):
                if not allow_dangerous:
                    return False, f"Suspicious pattern detected: {pattern}"
        
        return True, "Command appears safe"
    
    def _sanitize_environment(self, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Create a sanitized environment for command execution"""
        # Start with a minimal safe environment
        safe_env = {
            'PATH': os.environ.get('PATH', ''),
            'HOME': os.environ.get('HOME', ''),
            'USER': os.environ.get('USER', ''),
            'LANG': os.environ.get('LANG', 'en_US.UTF-8'),
            'TERM': os.environ.get('TERM', 'xterm-256color')
        }
        
        # Add custom environment variables if provided
        if env_vars:
            for key, value in env_vars.items():
                # Validate environment variable names and values
                if key.isidentifier() and isinstance(value, str):
                    safe_env[key] = value
                else:
                    logger.warning(f"Skipping invalid environment variable: {key}")
        
        return safe_env
    
    def _parse_command_output(self, stdout: str, stderr: str, return_code: int) -> Dict[str, Any]:
        """Parse and structure command output"""
        # Detect output type
        output_type = "text"
        if stdout:
            # Check for common structured formats
            if stdout.strip().startswith('{') and stdout.strip().endswith('}'):
                output_type = "json"
            elif '\t' in stdout or stdout.count('|') > 3:
                output_type = "tabular"
            elif stdout.count('\n') > 10 and '  ' in stdout:
                output_type = "structured"
        
        # Parse structured output for common commands
        parsed_info = {}
        
        # Git status parsing
        if 'git status' in stdout.lower() or any(indicator in stdout for indicator in ['modified:', 'new file:', 'deleted:']):
            parsed_info["git_status"] = self._parse_git_status(stdout)
        
        # Process listing parsing
        elif 'PID' in stdout and 'CMD' in stdout:
            parsed_info["process_list"] = self._parse_process_list(stdout)
        
        # File listing parsing
        elif re.search(r'-rw-r--r--|drwxr-xr-x', stdout):
            parsed_info["file_list"] = self._parse_file_list(stdout)
        
        return {
            "raw_stdout": stdout,
            "raw_stderr": stderr,
            "output_type": output_type,
            "line_count": len(stdout.split('\n')) if stdout else 0,
            "char_count": len(stdout) if stdout else 0,
            "parsed_info": parsed_info,
            "return_code": return_code
        }
    
    def _parse_git_status(self, output: str) -> Dict[str, Any]:
        """Parse git status output"""
        status_info = {
            "branch": None,
            "staged_files": [],
            "modified_files": [],
            "untracked_files": []
        }
        
        lines = output.split('\n')
        for line in lines:
            if line.startswith('On branch '):
                status_info["branch"] = line.replace('On branch ', '').strip()
            elif line.startswith('\tnew file:'):
                status_info["staged_files"].append(line.replace('\tnew file:', '').strip())
            elif line.startswith('\tmodified:'):
                status_info["modified_files"].append(line.replace('\tmodified:', '').strip())
            elif line.strip() and not line.startswith(('\t', ' ', 'Changes', 'Untracked')):
                if '/' in line or '.' in line:
                    status_info["untracked_files"].append(line.strip())
        
        return status_info
    
    def _parse_process_list(self, output: str) -> List[Dict[str, str]]:
        """Parse process list output (ps command)"""
        processes = []
        lines = output.strip().split('\n')
        
        if len(lines) < 2:
            return processes
        
        # Parse header to determine column positions
        header = lines[0]
        columns = header.split()
        
        for line in lines[1:]:
            if line.strip():
                parts = line.split(None, len(columns) - 1)
                if len(parts) >= len(columns):
                    process = {columns[i]: parts[i] for i in range(len(columns))}
                    processes.append(process)
        
        return processes[:50]  # Limit to first 50 processes
    
    def _parse_file_list(self, output: str) -> List[Dict[str, str]]:
        """Parse file listing output (ls -l command)"""
        files = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line and not line.startswith('total'):
                parts = line.split()
                if len(parts) >= 8:
                    files.append({
                        "permissions": parts[0],
                        "size": parts[4],
                        "date": f"{parts[5]} {parts[6]} {parts[7]}",
                        "name": ' '.join(parts[8:])
                    })
        
        return files

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            command = parameters["command"]
            timeout = parameters.get("timeout", 30)
            working_dir = parameters.get("working_dir", ".")
            env_vars = parameters.get("env_vars", {})
            capture_output = parameters.get("capture_output", True)
            shell_type = parameters.get("shell_type", "bash")
            allow_dangerous = parameters.get("allow_dangerous", False)
            max_output_size = parameters.get("max_output_size", 1048576)
            
            # Validate command safety
            is_safe, safety_message = self._validate_command_safety(command, allow_dangerous)
            if not is_safe:
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"Command rejected for security: {safety_message}"
                )
            
            # Validate working directory
            work_path = Path(working_dir)
            if not work_path.exists():
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"Working directory does not exist: {working_dir}"
                )
            
            # Prepare environment
            env = self._sanitize_environment(env_vars)
            
            # Configure shell
            shell_config = {
                'bash': ['/bin/bash', '-c'],
                'sh': ['/bin/sh', '-c'],
                'cmd': ['cmd', '/c'],
                'powershell': ['powershell', '-Command']
            }
            
            shell_cmd = shell_config.get(shell_type, ['/bin/bash', '-c'])
            full_command = shell_cmd + [command]
            
            # Execute command - FIXED VERSION
            try:
                # Use simple subprocess.run for better reliability
                process = subprocess.run(
                    full_command,
                    cwd=str(work_path),
                    env=env,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    shell=False  # Don't use shell=True for security
                )
                
                stdout = process.stdout if capture_output else ""
                stderr = process.stderr if capture_output else ""
                return_code = process.returncode
                timed_out = False
                
            except subprocess.TimeoutExpired:
                return_code = -1
                timed_out = True
                stdout, stderr = "", "Command timed out"
            
            execution_time = time.time() - start_time
            
            # Parse output
            output_info = self._parse_command_output(stdout or "", stderr or "", return_code)
            
            result = {
                "return_code": return_code,
                "stdout": stdout or "",
                "stderr": stderr or "",
                "timed_out": timed_out,
                "execution_time_seconds": execution_time,
                "working_directory": str(work_path),
                "shell_type": shell_type,
                "output_info": output_info,
                "command_safe": is_safe
            }
            
            # Determine status based on return code
            if return_code == 0 and not timed_out:
                status = ToolExecutionStatus.SUCCESS
            elif timed_out:
                status = ToolExecutionStatus.ERROR
                result["error_message"] = f"Command timed out after {timeout} seconds"
            else:
                status = ToolExecutionStatus.ERROR
                result["error_message"] = f"Command failed with return code {return_code}"
            
            return ToolResult(
                status=status,
                result=result,
                metadata={
                    "command": command[:100],  # Truncate long commands
                    "working_dir": working_dir,
                    "return_code": return_code
                },
                execution_time=execution_time,
                error_message=result.get("error_message")
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Shell execution failed: {str(e)}",
                execution_time=time.time() - start_time
            )
