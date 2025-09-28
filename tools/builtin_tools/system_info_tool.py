# tools/builtin_tools/system_info_tool.py
"""
System information tool implementation - Enhanced with comprehensive system monitoring
"""

import time
import platform
import os
import logging
import subprocess
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

logger = logging.getLogger(__name__)

class SystemInfoTool(BaseTool):
    """Comprehensive system information and monitoring with cross-platform support"""
    
    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="system_info",
            description="Get comprehensive system information, resource usage, and environment details",
            parameters={
                "info_type": {
                    "type": "string", 
                    "enum": ["cpu", "memory", "disk", "network", "processes", "environment", "hardware", "all"], 
                    "default": "all"
                },
                "include_processes": {"type": "boolean", "description": "Include running processes", "default": False},
                "process_limit": {"type": "integer", "description": "Limit number of processes to return", "default": 20},
                "disk_usage_paths": {"type": "array", "items": {"type": "string"}, "description": "Paths to check disk usage for"},
                "detailed": {"type": "boolean", "description": "Include detailed system information", "default": True}
            },
            required=[],
            tool_type=ToolType.SYSTEM_INFO,
            keywords=["system", "cpu", "memory", "disk", "resources", "monitor", "hardware", "processes"],
            examples=[
                {"info_type": "cpu", "detailed": True},
                {"info_type": "all", "include_processes": True, "process_limit": 10},
                {"info_type": "disk", "disk_usage_paths": ["/", "/home", "/var"]}
            ]
        )
    
    def _get_cpu_info(self, detailed: bool = True) -> Dict[str, Any]:
        """Get CPU information and usage"""
        cpu_info = {
            "architecture": platform.machine(),
            "processor": platform.processor() or "Unknown",
            "cores": os.cpu_count(),
        }
        
        try:
            import psutil
            cpu_info.update({
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1),
                "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
                "frequency": {
                    "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                    "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                    "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
                },
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
            })
            
            if detailed:
                cpu_stats = psutil.cpu_stats()
                cpu_info["detailed_stats"] = {
                    "context_switches": cpu_stats.ctx_switches,
                    "interrupts": cpu_stats.interrupts,
                    "soft_interrupts": cpu_stats.soft_interrupts,
                    "syscalls": getattr(cpu_stats, 'syscalls', None)
                }
        except ImportError:
            cpu_info["usage_percent"] = "unavailable (psutil not installed)"
        
        # Try to get CPU model from /proc/cpuinfo on Linux
        if platform.system() == "Linux" and detailed:
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    for line in cpuinfo.split('\n'):
                        if line.startswith("model name"):
                            cpu_info["model_name"] = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass
        
        return cpu_info
    
    def _get_memory_info(self, detailed: bool = True) -> Dict[str, Any]:
        """Get memory information and usage"""
        memory_info = {}
        
        try:
            import psutil
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            memory_info = {
                "virtual": {
                    "total": virtual_mem.total,
                    "available": virtual_mem.available,
                    "used": virtual_mem.used,
                    "free": virtual_mem.free,
                    "percent": virtual_mem.percent,
                    "total_gb": round(virtual_mem.total / (1024**3), 2),
                    "available_gb": round(virtual_mem.available / (1024**3), 2),
                    "used_gb": round(virtual_mem.used / (1024**3), 2)
                },
                "swap": {
                    "total": swap_mem.total,
                    "used": swap_mem.used,
                    "free": swap_mem.free,
                    "percent": swap_mem.percent,
                    "total_gb": round(swap_mem.total / (1024**3), 2) if swap_mem.total else 0,
                    "used_gb": round(swap_mem.used / (1024**3), 2) if swap_mem.used else 0
                }
            }
            
            if detailed and hasattr(virtual_mem, 'buffers'):
                memory_info["virtual"].update({
                    "buffers": virtual_mem.buffers,
                    "cached": virtual_mem.cached,
                    "shared": getattr(virtual_mem, 'shared', None)
                })
                
        except ImportError:
            memory_info = {"status": "unavailable (psutil not installed)"}
        
        return memory_info
    
    def _get_disk_info(self, paths: Optional[List[str]] = None, detailed: bool = True) -> Dict[str, Any]:
        """Get disk usage information"""
        disk_info = {"usage": {}, "partitions": []}
        
        # Default paths to check
        if not paths:
            if platform.system() == "Windows":
                paths = ["C:\\"]
            else:
                paths = ["/"]
        
        try:
            import psutil
            
            # Disk usage for specified paths
            for path in paths:
                try:
                    usage = psutil.disk_usage(path)
                    disk_info["usage"][path] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": round((usage.used / usage.total) * 100, 2),
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2)
                    }
                except Exception as e:
                    disk_info["usage"][path] = {"error": str(e)}
            
            # Partition information
            if detailed:
                for partition in psutil.disk_partitions():
                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts
                    }
                    
                    # Try to get usage for each partition
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        partition_info["usage"] = {
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent": round((usage.used / usage.total) * 100, 2)
                        }
                    except Exception:
                        partition_info["usage"] = {"error": "Unable to access"}
                    
                    disk_info["partitions"].append(partition_info)
                
                # Disk I/O statistics
                try:
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        disk_info["io_stats"] = {
                            "read_count": disk_io.read_count,
                            "write_count": disk_io.write_count,
                            "read_bytes": disk_io.read_bytes,
                            "write_bytes": disk_io.write_bytes,
                            "read_time": disk_io.read_time,
                            "write_time": disk_io.write_time
                        }
                except Exception:
                    pass
                    
        except ImportError:
            disk_info = {"status": "unavailable (psutil not installed)"}
        
        return disk_info
    
    def _get_network_info(self, detailed: bool = True) -> Dict[str, Any]:
        """Get network interface information"""
        network_info = {"interfaces": {}, "connections": []}
        
        try:
            import psutil
            
            # Network interfaces
            for interface, addresses in psutil.net_if_addrs().items():
                interface_info = {
                    "addresses": [],
                    "stats": {}
                }
                
                for addr in addresses:
                    interface_info["addresses"].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                        "ptp": addr.ptp
                    })
                
                # Interface statistics
                try:
                    stats = psutil.net_if_stats()[interface]
                    interface_info["stats"] = {
                        "isup": stats.isup,
                        "duplex": stats.duplex,
                        "speed": stats.speed,
                        "mtu": stats.mtu
                    }
                except KeyError:
                    pass
                
                network_info["interfaces"][interface] = interface_info
            
            # Network I/O statistics
            if detailed:
                try:
                    net_io = psutil.net_io_counters()
                    network_info["io_stats"] = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errin": net_io.errin,
                        "errout": net_io.errout,
                        "dropin": net_io.dropin,
                        "dropout": net_io.dropout
                    }
                except Exception:
                    pass
                
                # Active connections (limit to prevent overwhelming output)
                try:
                    connections = psutil.net_connections()[:20]  # Limit to first 20
                    for conn in connections:
                        network_info["connections"].append({
                            "fd": conn.fd,
                            "family": str(conn.family),
                            "type": str(conn.type),
                            "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                            "remote_addr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                            "status": conn.status,
                            "pid": conn.pid
                        })
                except Exception:
                    pass
                    
        except ImportError:
            network_info = {"status": "unavailable (psutil not installed)"}
        
        return network_info
    
    def _get_process_info(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get information about running processes"""
        processes = []
        
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
                try:
                    proc_info = proc.info.copy()
                    proc_info['memory_mb'] = round(proc.memory_info().rss / (1024 * 1024), 2)
                    proc_info['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                           time.localtime(proc_info['create_time']))
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage and limit results
            processes.sort(key=lambda x: x.get('memory_mb', 0), reverse=True)
            processes = processes[:limit]
            
        except ImportError:
            processes = [{"error": "psutil not installed"}]
        
        return processes
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment and runtime information"""
        env_info = {
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "executable": os.path.abspath(os.path.executable)
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "node": platform.node()
            },
            "paths": {
                "current_directory": str(Path.cwd()),
                "home_directory": str(Path.home()),
                "temp_directory": os.path.normpath(os.path.tempdir) if hasattr(os, 'tempdir') else str(Path.home() / "tmp")
            },
            "user": {
                "username": os.getenv('USER') or os.getenv('USERNAME'),
                "uid": os.getuid() if hasattr(os, 'getuid') else None,
                "gid": os.getgid() if hasattr(os, 'getgid') else None
            }
        }
        
        # Environment variables (filtered for security)
        safe_env_vars = ['PATH', 'HOME', 'SHELL', 'LANG', 'TERM', 'PWD', 'PYTHONPATH']
        env_info["environment_variables"] = {
            var: os.getenv(var) for var in safe_env_vars if os.getenv(var)
        }
        
        return env_info
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information"""
        hardware_info = {
            "cpu": {
                "architecture": platform.machine(),
                "processor": platform.processor()
            },
            "platform": platform.platform(),
            "uname": platform.uname()._asdict()
        }
        
        # Try to get additional hardware info on Linux
        if platform.system() == "Linux":
            try:
                # Memory info from /proc/meminfo
                with open("/proc/meminfo", "r") as f:
                    meminfo = {}
                    for line in f:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            meminfo[key.strip()] = value.strip()
                    hardware_info["detailed_memory"] = meminfo
            except Exception:
                pass
            
            try:
                # CPU info from /proc/cpuinfo
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    hardware_info["detailed_cpu"] = cpuinfo[:1000]  # Limit output
            except Exception:
                pass
        
        # Try to get GPU info
        try:
            # NVIDIA GPU info
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                gpus = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [part.strip() for part in line.split(',')]
                        if len(parts) >= 3:
                            gpus.append({
                                "name": parts[0],
                                "memory_mb": parts[1],
                                "driver_version": parts[2]
                            })
                hardware_info["gpus"] = gpus
        except Exception:
            pass
        
        return hardware_info

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            info_type = parameters.get("info_type", "all")
            include_processes = parameters.get("include_processes", False)
            process_limit = parameters.get("process_limit", 20)
            disk_usage_paths = parameters.get("disk_usage_paths")
            detailed = parameters.get("detailed", True)
            
            system_info = {
                "timestamp": time.time(),
                "hostname": platform.node(),
                "uptime_seconds": None
            }
            
            # Try to get system uptime
            try:
                if platform.system() == "Linux":
                    with open("/proc/uptime", "r") as f:
                        system_info["uptime_seconds"] = float(f.read().split()[0])
                elif platform.system() == "Windows":
                    # Windows uptime via WMI (if available)
                    pass
            except Exception:
                pass
            
            # Collect requested information
            if info_type in ["cpu", "all"]:
                system_info["cpu"] = self._get_cpu_info(detailed)
            
            if info_type in ["memory", "all"]:
                system_info["memory"] = self._get_memory_info(detailed)
            
            if info_type in ["disk", "all"]:
                system_info["disk"] = self._get_disk_info(disk_usage_paths, detailed)
            
            if info_type in ["network", "all"]:
                system_info["network"] = self._get_network_info(detailed)
            
            if info_type in ["environment", "all"]:
                system_info["environment"] = self._get_environment_info()
            
            if info_type in ["hardware", "all"]:
                system_info["hardware"] = self._get_hardware_info()
            
            if include_processes or info_type == "processes":
                system_info["processes"] = self._get_process_info(process_limit)
            
            # Add summary information
            if info_type == "all":
                summary = {
                    "system": f"{platform.system()} {platform.release()}",
                    "python_version": platform.python_version(),
                    "architecture": platform.machine()
                }
                
                # Add resource usage summary if available
                if "cpu" in system_info and isinstance(system_info["cpu"], dict):
                    summary["cpu_usage"] = system_info["cpu"].get("usage_percent", "unknown")
                
                if "memory" in system_info and isinstance(system_info["memory"], dict):
                    virtual_mem = system_info["memory"].get("virtual", {})
                    summary["memory_usage"] = f"{virtual_mem.get('percent', 'unknown')}%"
                    summary["memory_available"] = f"{virtual_mem.get('available_gb', 'unknown')} GB"
                
                system_info["summary"] = summary
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=system_info,
                metadata={
                    "info_type": info_type,
                    "detailed": detailed,
                    "include_processes": include_processes
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"System info collection failed: {str(e)}",
                execution_time=time.time() - start_time
            )
