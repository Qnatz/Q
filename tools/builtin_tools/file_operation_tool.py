# tools/builtin_tools/file_operation_tool.py
"""
File operation tool implementation - Improved version
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import shutil
import mimetypes
import hashlib
import stat

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class FileOperationTool(BaseTool):
    """Enhanced file system operations with better error handling and features"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="file_operation",
            description="Perform comprehensive file system operations with safety checks",
            parameters={
                "operation": {
                    "type": "string", 
                    "enum": ["read", "write", "list", "exists", "delete", "copy", "move", "mkdir", "stat", "search"]
                },
                "path": {"type": "string", "description": "File or directory path"},
                "content": {"type": "string", "description": "Content to write (for write operation)"},
                "target_path": {"type": "string", "description": "Target path for copy/move operations"},
                "encoding": {"type": "string", "default": "utf-8"},
                "create_parents": {"type": "boolean", "default": True, "description": "Create parent directories if they don't exist"},
                "overwrite": {"type": "boolean", "default": False, "description": "Allow overwriting existing files"},
                "pattern": {"type": "string", "description": "Search pattern for file search"},
                "recursive": {"type": "boolean", "default": False, "description": "Recursive operation for list/search"},
                "max_size": {"type": "integer", "default": 10485760, "description": "Maximum file size to read (10MB default)"}
            },
            required=["operation", "path"],
            tool_type=ToolType.FILE_OPERATION,
            keywords=["file", "read", "write", "directory", "folder", "filesystem", "copy", "move"],
            examples=[
                {"operation": "read", "path": "config.json"},
                {"operation": "write", "path": "output.txt", "content": "Hello World", "create_parents": True},
                {"operation": "list", "path": "./projects", "recursive": True},
                {"operation": "search", "path": ".", "pattern": "*.py", "recursive": True}
            ]
        )
    
    def _is_safe_path(self, path: Path, base_path: Path = None) -> bool:
        """Check if path is safe (no directory traversal attacks)"""
        try:
            if base_path is None:
                base_path = Path.cwd()
            
            resolved_path = path.resolve()
            resolved_base = base_path.resolve()
            
            # Allow paths in /tmp
            if str(resolved_path).startswith('/tmp'):
                return True

            # Check if the resolved path is within the base path
            return str(resolved_path).startswith(str(resolved_base))
        except Exception:
            return False
    
    def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            stat_info = path.stat()
            return {
                "name": path.name,
                "path": str(path),
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "created": stat_info.st_ctime,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "is_symlink": path.is_symlink(),
                "permissions": oct(stat_info.st_mode)[-3:],
                "mime_type": mimetypes.guess_type(str(path))[0] if path.is_file() else None
            }
        except Exception as e:
            return {"name": path.name, "path": str(path), "error": str(e)}
    
    def _resolve_project_path(self, path: str, context: Optional[Dict[str, Any]] = None) -> Path:
        """Resolve project-relative paths safely"""
        # If it's already an absolute path, use as-is
        if path.startswith('/'):
            return Path(path)
        
        # Try to resolve relative to project directory
        if context and 'project_id' in context:
            project_dir = f"/root/Q/projects/{context['project_id']}"
            return Path(project_dir) / path
        
        # Fallback to current working directory
        return Path.cwd() / path
    
    def _safe_read_file(self, path: Path, encoding: str, max_size: int) -> str:
        """Safely read file with size limits"""
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        file_size = path.stat().st_size
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
        
        # Check for binary files
        try:
            with open(path, 'rb') as f:
                sample = f.read(1024)
                if b'\x00' in sample:
                    raise ValueError("File appears to be binary")
        except Exception:
            pass
        
        return path.read_text(encoding=encoding)
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        logger.info(f"FileOperationTool received parameters: {parameters}")
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            operation = parameters["operation"]
            raw_path = parameters["path"]
            
            # Use safe path resolution
            path = self._resolve_project_path(raw_path, context)
            encoding = parameters.get("encoding", "utf-8")
            create_parents = parameters.get("create_parents", True)
            overwrite = parameters.get("overwrite", False)
            max_size = parameters.get("max_size", 10485760)
            recursive = parameters.get("recursive", False)
            
            # Safety check
            if not self._is_safe_path(path):
                raise ValueError(f"Unsafe path detected: {path}")
            
            result = {}
            
            if operation == "read":
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                
                content = self._safe_read_file(path, encoding, max_size)
                result = {
                    "content": content, 
                    "size": len(content),
                    "encoding": encoding,
                    "file_info": self._get_file_info(path)
                }
                
            elif operation == "write":
                content = parameters.get("content", "")
                
                if path.exists() and not overwrite:
                    raise FileExistsError(f"File exists and overwrite=False: {path}")
                
                if create_parents:
                    path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create backup if file exists
                backup_path = None
                if path.exists():
                    backup_path = path.with_suffix(path.suffix + '.bak')
                    shutil.copy2(path, backup_path)
                
                path.write_text(content, encoding=encoding)
                
                result = {
                    "bytes_written": len(content.encode(encoding)),
                    "path": str(path),
                    "backup_created": str(backup_path) if backup_path else None,
                    "file_info": self._get_file_info(path)
                }
                
            elif operation == "list":
                if not path.exists():
                    raise FileNotFoundError(f"Directory not found: {path}")
                
                if not path.is_dir():
                    raise NotADirectoryError(f"Path is not a directory: {path}")
                
                items = []
                iterator = path.rglob("*") if recursive else path.iterdir()
                
                for item in iterator:
                    items.append(self._get_file_info(item))
                
                result = {"items": items, "total": len(items), "path": str(path)}
                
            elif operation == "exists":
                result = {
                    "exists": path.exists(),
                    "is_file": path.is_file() if path.exists() else False,
                    "is_dir": path.is_dir() if path.exists() else False,
                    "path": str(path)
                }
                
            elif operation == "delete":
                if not path.exists():
                    result = {"deleted": False, "reason": "File not found", "path": str(path)}
                else:
                    # Create backup before deletion
                    backup_info = None
                    if path.is_file():
                        backup_path = path.with_suffix(path.suffix + '.deleted')
                        shutil.copy2(path, backup_path)
                        backup_info = str(backup_path)
                        path.unlink()
                    else:
                        # For directories, create a tar backup
                        backup_path = path.parent / f"{path.name}.deleted.tar"
                        shutil.make_archive(str(backup_path).replace('.tar', ''), 'tar', path)
                        backup_info = str(backup_path)
                        shutil.rmtree(path)
                    
                    result = {"deleted": True, "path": str(path), "backup": backup_info}
            
            elif operation == "copy":
                target_path = Path(parameters.get("target_path", ""))
                if not target_path:
                    raise ValueError("target_path required for copy operation")
                
                if not self._is_safe_path(target_path):
                    raise ValueError(f"Unsafe target path: {target_path}")
                
                if not path.exists():
                    raise FileNotFoundError(f"Source not found: {path}")
                
                if create_parents:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if path.is_file():
                    shutil.copy2(path, target_path)
                else:
                    shutil.copytree(path, target_path, dirs_exist_ok=overwrite)
                
                result = {
                    "copied": True,
                    "source": str(path),
                    "target": str(target_path),
                    "target_info": self._get_file_info(target_path)
                }
            
            elif operation == "move":
                target_path = Path(parameters.get("target_path", ""))
                if not target_path:
                    raise ValueError("target_path required for move operation")
                
                if not self._is_safe_path(target_path):
                    raise ValueError(f"Unsafe target path: {target_path}")
                
                if not path.exists():
                    raise FileNotFoundError(f"Source not found: {path}")
                
                if create_parents:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(path), str(target_path))
                
                result = {
                    "moved": True,
                    "source": str(path),
                    "target": str(target_path),
                    "target_info": self._get_file_info(target_path)
                }
            
            elif operation == "mkdir":
                path.mkdir(parents=create_parents, exist_ok=overwrite)
                result = {
                    "created": True,
                    "path": str(path),
                    "parents_created": create_parents
                }
            
            elif operation == "stat":
                if not path.exists():
                    raise FileNotFoundError(f"Path not found: {path}")
                
                result = self._get_file_info(path)
            
            elif operation == "search":
                pattern = parameters.get("pattern", "*")
                if not path.exists():
                    raise FileNotFoundError(f"Search path not found: {path}")
                
                matches = []
                search_path = path.rglob(pattern) if recursive else path.glob(pattern)
                
                for match in search_path:
                    matches.append(self._get_file_info(match))
                
                result = {
                    "matches": matches,
                    "pattern": pattern,
                    "search_path": str(path),
                    "total_matches": len(matches)
                }
            
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
                error_message=f"File operation '{operation}' failed: {str(e)}",
                execution_time=time.time() - start_time
            )
