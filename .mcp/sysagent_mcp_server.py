#!/usr/bin/env python3
"""
SysAgent MCP Server - Official MCP implementation for Linux system administration.
Uses the official Anthropic MCP SDK (FastMCP).
"""

import os
import sys
import asyncio
import subprocess
import psutil
import socket
import stat
import shutil
import platform
import fnmatch
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("SysAgent")


# ============================================================================
# TOOLS - System Administration Operations
# ============================================================================

@mcp.tool()
async def execute_command(command: str) -> dict:
    """Execute any Linux shell command as root.

    Args:
        command: The shell command to execute (runs as root)

    Returns:
        Dictionary with success status, stdout, stderr, and return code
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            stdout = stdout.decode(errors='ignore') if stdout else ""
            stderr = stderr.decode(errors='ignore') if stderr else ""
        except asyncio.TimeoutError:
            try:
                process.kill()
                stdout, stderr = await process.communicate()
                stdout = stdout.decode(errors='ignore') if stdout else ""
                stderr = stderr.decode(errors='ignore') if stderr else ""
                stderr += "\nCommand timed out after 30 seconds and was terminated."
            except Exception as e:
                return {
                    "success": False,
                    "error": "Command timed out after 30 seconds and could not be terminated cleanly.",
                    "stdout": "",
                    "stderr": "",
                    "return_code": -1
                }

        return {
            "success": process.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": process.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": f"Error: {str(e)}",
            "return_code": -1
        }


@mcp.tool()
async def read_file(file_path: str) -> dict:
    """Read any text file from the system as root.

    Args:
        file_path: Absolute path to the file to read

    Returns:
        Dictionary with success status, file content, path, and size
    """
    try:
        if not file_path or not isinstance(file_path, str):
            return {
                "success": False,
                "error": "Missing or invalid file_path parameter.",
                "path": file_path
            }

        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "path": file_path
            }

        if not os.path.isfile(file_path):
            error_msg = f"Is a directory: {file_path}" if os.path.isdir(file_path) else f"Not a file: {file_path}"
            return {
                "success": False,
                "error": error_msg,
                "path": file_path
            }

        file_size = os.path.getsize(file_path)
        max_size = 10 * 1024 * 1024  # 10MB

        if file_size > max_size:
            return {
                "success": False,
                "error": f"File too large to read directly: {_format_bytes(file_size)}. Maximum size: {_format_bytes(max_size)}",
                "path": file_path,
                "size": file_size
            }

        with open(file_path, "r", errors="replace") as f:
            content = f.read()

        return {
            "success": True,
            "content": content,
            "path": file_path,
            "size": file_size
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "File appears to be binary and cannot be displayed as text.",
            "path": file_path,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": file_path
        }


@mcp.tool()
async def edit_file(file_path: str, content: str, append: bool = False) -> dict:
    """Edit any text file on the system as root.

    Args:
        file_path: Absolute path to the file to edit
        content: New content to write to the file
        append: Whether to append to the file instead of overwriting it

    Returns:
        Dictionary with success status, message, path, and size
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        mode = "a" if append else "w"
        with open(file_path, mode) as f:
            f.write(content)

        file_size = os.path.getsize(file_path)

        return {
            "success": True,
            "message": f"File {'appended to' if append else 'written'} successfully. Size: {_format_bytes(file_size)}",
            "path": file_path,
            "size": file_size
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": file_path
        }


@mcp.tool()
async def list_directory(directory: str = "/", show_hidden: bool = False) -> dict:
    """List contents of any directory as root.

    Args:
        directory: Absolute path to the directory to list
        show_hidden: Whether to show hidden files (starting with .)

    Returns:
        Dictionary with success status, path, items list, and count
    """
    try:
        directory = os.path.normpath(directory)

        if not os.path.exists(directory):
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
                "path": directory
            }

        if not os.path.isdir(directory):
            return {
                "success": False,
                "error": f"Not a directory: {directory}",
                "path": directory
            }

        items = []
        with os.scandir(directory) as it:
            for entry in it:
                if not show_hidden and entry.name.startswith('.'):
                    continue

                try:
                    stat_info = entry.stat()
                    item = {
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat_info.st_size if not entry.is_dir() else 0,
                        "modified": stat_info.st_mtime,
                        "permissions": _format_permissions(stat_info.st_mode)
                    }
                    items.append(item)
                except Exception as e:
                    items.append({
                        "name": entry.name,
                        "is_dir": False,
                        "size": 0,
                        "modified": 0,
                        "permissions": "?????????",
                        "error": str(e)
                    })

        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        return {
            "success": True,
            "path": directory,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": directory
        }


@mcp.tool()
async def find_files(pattern: str, directory: str = "/", max_depth: int = 5) -> dict:
    """Find files matching a pattern anywhere on the system as root.

    Args:
        pattern: Pattern to search for (glob syntax, e.g., '*.log')
        directory: Absolute path to the directory to start search in
        max_depth: Maximum directory depth relative to start directory (0 means start directory only, -1 for unlimited)

    Returns:
        Dictionary with success status, matches list, count, and search parameters
    """
    directory = os.path.normpath(directory)

    if not os.path.exists(directory):
        return {
            "success": False,
            "error": f"Start directory not found: {directory}",
            "matches": [],
            "count": 0,
            "pattern": pattern,
            "start_dir": directory,
            "max_depth": max_depth
        }

    if not os.path.isdir(directory):
        return {
            "success": False,
            "error": f"Not a directory: {directory}",
            "matches": [],
            "count": 0,
            "pattern": pattern,
            "start_dir": directory,
            "max_depth": max_depth
        }

    matches = []
    match_count = 0
    max_matches = 500

    try:
        for root, dirs, files in os.walk(directory):
            if max_depth >= 0:
                relative_path = os.path.relpath(root, directory)
                if relative_path != '.' and relative_path.count(os.sep) >= max_depth:
                    dirs.clear()
                    continue

            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    file_path = os.path.join(root, filename)
                    matches.append(file_path)
                    match_count += 1
                    if match_count >= max_matches:
                        return {
                            "success": True,
                            "matches": matches,
                            "count": match_count,
                            "pattern": pattern,
                            "start_dir": directory,
                            "max_depth": max_depth
                        }

        return {
            "success": True,
            "matches": matches,
            "count": match_count,
            "pattern": pattern,
            "start_dir": directory,
            "max_depth": max_depth
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {str(e)}",
            "matches": matches,
            "count": match_count,
            "pattern": pattern,
            "start_dir": directory,
            "max_depth": max_depth
        }


@mcp.tool()
async def service_status(service_name: str = "") -> dict:
    """Check status of system services (uses systemctl or service), as root.

    Args:
        service_name: Optional name of service to check (e.g., 'nginx'), empty for all services

    Returns:
        Dictionary with success status, output, error, return code, service name, and method used
    """
    systemctl_exists = await _command_exists("systemctl")
    service_cmd_exists = await _command_exists("service")

    try:
        # Check for Docker environment
        is_docker = os.path.exists('/.dockerenv')

        if is_docker and systemctl_exists:
            systemctl_test = await asyncio.create_subprocess_shell(
                "systemctl 2>&1 | grep -i 'failed to connect'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await systemctl_test.communicate()
            if stdout:
                systemctl_exists = False

        if service_name:
            if systemctl_exists:
                command = f"systemctl status {service_name}"
            elif service_cmd_exists:
                command = f"service {service_name} status"
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": "Neither systemctl nor service commands are available on this system.",
                    "return_code": 127,
                    "service_name": service_name,
                    "method": "none"
                }
        else:
            if systemctl_exists:
                command = "systemctl list-units --type=service"
            elif service_cmd_exists:
                command = "service --status-all"
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": "Neither systemctl nor service commands are available on this system.",
                    "return_code": 127,
                    "service_name": "all",
                    "method": "none"
                }

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        stdout = stdout.decode(errors='ignore') if stdout else ""
        stderr = stderr.decode(errors='ignore') if stderr else ""

        output = stdout
        if stderr:
            output += f"\nSTDERR:\n{stderr}"

        return {
            "success": proc.returncode == 0,
            "output": output,
            "error": stderr if proc.returncode != 0 else "",
            "return_code": proc.returncode,
            "service_name": service_name if service_name else "all",
            "method": "systemctl" if systemctl_exists else ("service" if service_cmd_exists else "none")
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "return_code": 1,
            "service_name": service_name if service_name else "all",
            "method": "systemctl" if systemctl_exists else ("service" if service_cmd_exists else "none")
        }


@mcp.tool()
async def delete_path(path: str, recursive: bool = False) -> dict:
    """Delete a file or directory as root (optionally recursive for directories).

    Args:
        path: Absolute path to the file or directory to delete
        recursive: Whether to delete directories recursively

    Returns:
        Dictionary with success status, message/error, and path
    """
    try:
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"Path not found: {path}",
                "path": path
            }

        if os.path.isfile(path):
            os.remove(path)
            return {
                "success": True,
                "message": f"File deleted: {path}",
                "path": path
            }
        elif os.path.isdir(path):
            if recursive:
                shutil.rmtree(path)
                return {
                    "success": True,
                    "message": f"Directory deleted recursively: {path}",
                    "path": path
                }
            else:
                if not os.listdir(path):
                    os.rmdir(path)
                    return {
                        "success": True,
                        "message": f"Empty directory deleted: {path}",
                        "path": path
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Directory not empty: {path}. Use recursive=true to delete recursively.",
                        "path": path
                    }
        else:
            return {
                "success": False,
                "error": f"Not a file or directory: {path}",
                "path": path
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": path
        }


# ============================================================================
# RESOURCES - System Information
# ============================================================================

@mcp.resource("system://overview")
def get_system_overview() -> str:
    """Get basic system information including hostname, OS, CPU, memory, and disk."""
    info = []
    info.append(f"Hostname: {socket.gethostname()}")
    info.append(f"Kernel: {os.uname().release}")
    info.append(f"OS: {os.uname().sysname} {os.uname().version}")

    # CPU info
    cpu_info = []
    cpu_info.append(f"CPU Cores: {psutil.cpu_count(logical=False)}")
    cpu_info.append(f"Logical CPUs: {psutil.cpu_count(logical=True)}")
    cpu_info.append(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")

    # Memory info
    mem = psutil.virtual_memory()
    mem_info = []
    mem_info.append(f"Total Memory: {_format_bytes(mem.total)}")
    mem_info.append(f"Available Memory: {_format_bytes(mem.available)}")
    mem_info.append(f"Used Memory: {_format_bytes(mem.used)} ({mem.percent}%)")

    return "\n".join(info) + "\n\nCPU Information:\n" + "\n".join(cpu_info) + "\n\nMemory Information:\n" + "\n".join(mem_info)


@mcp.resource("system://processes")
def get_processes() -> str:
    """Get information about currently running processes."""
    processes = []
    processes.append(f"{'PID':<7} {'USER':<10} {'CPU%':<6} {'MEM%':<6} {'CMD':<30}")
    processes.append("-" * 60)

    for proc in sorted(psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']),
                      key=lambda p: p.info['cpu_percent'],
                      reverse=True)[:20]:
        try:
            processes.append(f"{proc.info['pid']:<7} {proc.info['username'][:9]:<10} {proc.info['cpu_percent']:<6.1f} {proc.info['memory_percent']:<6.1f} {proc.info['name'][:30]:<30}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return "\n".join(processes)


@mcp.resource("system://network")
def get_network() -> str:
    """Get current network interfaces and connections."""
    info = []

    # Network interfaces
    info.append("Network Interfaces:")
    for iface, addrs in psutil.net_if_addrs().items():
        info.append(f"\n{iface}:")
        for addr in addrs:
            if addr.family == socket.AF_INET:
                info.append(f"  IPv4: {addr.address} (netmask: {addr.netmask})")
            elif addr.family == socket.AF_INET6:
                info.append(f"  IPv6: {addr.address}")
            elif hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:
                info.append(f"  MAC: {addr.address}")

    # Network connections
    info.append("\nActive Connections:")
    info.append(f"{'Proto':<6} {'Local Address':<25} {'Remote Address':<25} {'Status':<12}")
    info.append("-" * 70)

    for conn in psutil.net_connections(kind='inet')[:15]:
        if conn.laddr and len(conn.laddr) >= 2:
            laddr = f"{conn.laddr[0]}:{conn.laddr[1]}"
        else:
            laddr = "-"

        if conn.raddr and len(conn.raddr) >= 2:
            raddr = f"{conn.raddr[0]}:{conn.raddr[1]}"
        else:
            raddr = "-"

        info.append(f"{'TCP' if conn.type == socket.SOCK_STREAM else 'UDP':<6} {laddr:<25} {raddr:<25} {conn.status:<12}")

    return "\n".join(info)


@mcp.resource("system://disk")
def get_disk_usage() -> str:
    """Get current disk usage and mount points."""
    info = []
    info.append(f"{'Device':<15} {'Mountpoint':<20} {'Total':<10} {'Used':<10} {'Free':<10} {'Use%':<6} {'Type':<8}")
    info.append("-" * 80)

    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)
            info.append(f"{part.device[-14:]:<15} {part.mountpoint:<20} {_format_bytes(usage.total):<10} "
                      f"{_format_bytes(usage.used):<10} {_format_bytes(usage.free):<10} "
                      f"{usage.percent:<6.1f} {part.fstype:<8}")
        except Exception:
            pass

    return "\n".join(info)


@mcp.resource("system://distro")
def get_distro_info() -> str:
    """Get distribution-specific information for commands, paths, and conventions."""
    distro_name = _get_distro_name()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    info_file_path = os.path.join(base_dir, "distro_specific_info", f"{distro_name}.md")

    if os.path.exists(info_file_path):
        try:
            with open(info_file_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading information file for {distro_name}: {str(e)}"
    else:
        return f"No specific information file found for distribution: {distro_name}."


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}PB"


def _format_permissions(mode: int) -> str:
    """Format file permissions as a string."""
    perms = ""

    if stat.S_ISDIR(mode):
        perms += "d"
    elif stat.S_ISLNK(mode):
        perms += "l"
    elif stat.S_ISREG(mode):
        perms += "-"
    else:
        perms += "?"

    perms += "r" if mode & 0o400 else "-"
    perms += "w" if mode & 0o200 else "-"
    perms += "x" if mode & 0o100 else "-"
    perms += "r" if mode & 0o040 else "-"
    perms += "w" if mode & 0o020 else "-"
    perms += "x" if mode & 0o010 else "-"
    perms += "r" if mode & 0o004 else "-"
    perms += "w" if mode & 0o002 else "-"
    perms += "x" if mode & 0o001 else "-"

    return perms


def _get_distro_name() -> str:
    """Attempt to identify the Linux distribution name."""
    try:
        dist = platform.system().lower()
        if dist == 'linux':
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release') as f:
                    for line in f:
                        if line.startswith('ID='):
                            return line.strip().split('=')[1].strip('"').lower()

            if os.path.exists('/etc/debian_version'):
                return 'debian'
            if os.path.exists('/etc/alpine-release'):
                return 'alpine'

        return dist
    except Exception:
        return "unknown"


async def _command_exists(command: str) -> bool:
    """Check if a command exists on the system."""
    try:
        process = await asyncio.create_subprocess_shell(
            f"command -v {command}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception:
        return False


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
