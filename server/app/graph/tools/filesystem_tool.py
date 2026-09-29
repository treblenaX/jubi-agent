"""
Filesystem tools for coder agent.

SAFETY INVARIANTS:
- Coder MUST write only to the configured sandbox root (settings.SANDBOX_ROOT)
- Coder MUST NOT read/write outside sandbox or the active project workspace
- All paths must be validated before operations
"""

import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.core.config import settings


# Sandbox root - coder can ONLY write here. Bound to settings.SANDBOX_ROOT
# (single source of truth; was hardcoded "/tmp/jubi-sandbox"). Kept as a Path
# so `SANDBOX_ROOT / name` joins correctly.
SANDBOX_ROOT = Path(settings.SANDBOX_ROOT)


def _validate_sandbox_path(path: str) -> bool:
    """
    Validate that a path is within the sandbox directory.

    Args:
        path: The path to validate (can be relative or absolute)

    Returns:
        True if path is within sandbox, False otherwise
    """
    try:
        # Normalize paths - keep sandbox resolved, but handle relative paths
        sandbox = Path(SANDBOX_ROOT).resolve()

        # If path is relative and doesn't contain path separators, treat as sandbox-relative
        # This allows simple filenames like "test.py" to be written to sandbox
        if not Path(path).is_absolute():
            # Check if it's a simple filename (no path separators)
            if '/' not in path and '\\' not in path:
                return True  # Accept simple filenames as sandbox-relative

            # Otherwise, resolve relative to cwd and check
            target = (Path.cwd() / path).resolve()
        else:
            target = Path(path).resolve()

        # Check if target is under sandbox
        return str(target).startswith(str(sandbox))
    except Exception:
        return False


def read_project_file(path: str, workspace_path: Optional[str] = None) -> Optional[str]:
    """
    Read a file from the project or sandbox.
    
    Args:
        path: Path to the file
        workspace_path: Optional workspace path to restrict tool actions
        
    Returns:
        File contents as string, or None if not found
    """
    try:
        # For read operations, allow reading from workspace too
        p = Path(path)
        
        # If workspace_path is specified, resolve it and use that as the base
        if workspace_path:
            base_path = Path(workspace_path).resolve()
            # Relative paths resolve against the workspace; absolute paths must
            # already be inside it (path jail).
            candidate = p if p.is_absolute() else base_path / p
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(base_path)):
                return None  # Not in workspace
            if resolved.is_file():
                return resolved.read_text(encoding="utf-8")
            return None  # Not found in workspace
        else:
            # Default behavior: try sandbox then workspace
            sandbox_path = SANDBOX_ROOT / p.name
            if sandbox_path.exists():
                return sandbox_path.read_text(encoding="utf-8")
            
            # Then try workspace
            workspace_path_default = Path.cwd() / p.name
            if workspace_path_default.exists():
                return workspace_path_default.read_text(encoding="utf-8")
        
        return None
        
    except Exception as e:
        return f"Error reading file: {e}"


def write_project_file(path: str, content: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Write a file to the sandbox directory.

    SAFETY: Only writes to the sandbox root or specified workspace_path

    Args:
        path: Path relative to sandbox (e.g., "hello.py")
        content: File contents
        workspace_path: Optional workspace path to restrict tool actions

    Returns:
        Dict with status and message
    """
    try:
        # Create sandbox directory if needed (before validation)
        os.makedirs(SANDBOX_ROOT, exist_ok=True)

        # If workspace_path is specified, use that as the base
        if workspace_path:
            base_path = Path(workspace_path).resolve()

            # Relative paths resolve against the workspace; absolute paths must
            # already be inside it (path jail).
            p = Path(path)
            candidate = p if p.is_absolute() else base_path / p
            target = candidate.resolve()
            if not str(target).startswith(str(base_path)):
                return {
                    "status": "error",
                    "message": f"Security violation: Path must be under {workspace_path}"
                }
            
            # Write to workspace
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            
            return {
                "status": "success",
                "path": str(target),
                "bytes_written": len(content.encode("utf-8"))
            }
        else:
            # Default behavior: only write to sandbox
            # Validate path is within sandbox
            if not _validate_sandbox_path(path):
                return {
                    "status": "error",
                    "message": f"Security violation: Path must be under {SANDBOX_ROOT}"
                }

            # Write to sandbox
            sandbox_path = Path(SANDBOX_ROOT) / path
            sandbox_path.parent.mkdir(parents=True, exist_ok=True)
            sandbox_path.write_text(content, encoding="utf-8")

            return {
                "status": "success",
                "path": str(sandbox_path),
                "bytes_written": len(content.encode("utf-8"))
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write file: {e}"
        }


def edit_project_file(path: str, old_text: str, new_text: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Edit a file by replacing text.
    
    Args:
        path: Path relative to sandbox
        old_text: Text to replace
        new_text: Replacement text
        workspace_path: Optional workspace path to restrict tool actions
        
    Returns:
        Dict with status and message
    """
    try:
        # Determine the actual file path (relative paths resolve against the
        # workspace or sandbox; absolute paths must already be inside it — path jail)
        if workspace_path:
            base_path = Path(workspace_path).resolve()
            p = Path(path)
            candidate = p if p.is_absolute() else base_path / p
            target = candidate.resolve()
            if not str(target).startswith(str(base_path)):
                return {
                    "status": "error",
                    "message": f"Security violation: Path must be under {workspace_path}"
                }
        else:
            # Default behavior: validate sandbox path
            if not _validate_sandbox_path(path):
                return {
                    "status": "error",
                    "message": f"Security violation: Path must be under {SANDBOX_ROOT}"
                }
            target = (Path(SANDBOX_ROOT) / path).resolve()
        
        if not target.exists():
            return {
                "status": "error",
                "message": f"File not found: {path}"
            }
        
        content = target.read_text(encoding="utf-8")
        
        # Replace text (only first occurrence by default)
        if old_text in content:
            new_content = content.replace(old_text, new_text, 1)
            target.write_text(new_content, encoding="utf-8")
            
            return {
                "status": "success",
                "path": str(target),
                "replacements": 1
            }
        else:
            return {
                "status": "error",
                "message": f"Text not found in file: {old_text}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to edit file: {e}"
        }


def list_project(glob_pattern: Optional[str] = None, workspace_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List files in the project workspace (or the sandbox when no workspace).
    
    Args:
        glob_pattern: Optional glob filter (e.g., "*.py")
        workspace_path: Optional workspace path to restrict tool actions
        
    Returns:
        List of file info dicts
    """
    try:
        root = Path(workspace_path).resolve() if workspace_path else Path(SANDBOX_ROOT)
        
        if not root.exists():
            return []
        
        files = []
        for item in root.iterdir():
            if glob_pattern:
                if not re.search(glob_pattern, item.name):
                    continue
            
            info = {
                "name": item.name,
                "path": str(item.relative_to(root)),
                "size": item.stat().st_size if item.is_file() else 0,
                "is_file": item.is_file(),
                "modified": item.stat().st_mtime if item.is_file() else None
            }
            files.append(info)
        
        # Sort by modification time (newest first); dirs have no mtime -> 0
        files.sort(key=lambda x: x.get("modified") or 0, reverse=True)
        
        return files
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list project: {e}"
        }


def run_shell(command: str, working_dir: Optional[str] = None, workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a shell command in the sandbox.
    
    SAFETY: Only runs commands in the sandbox root or specified workspace_path
    
    Args:
        command: Shell command to execute
        working_dir: Working directory (defaults to sandbox root)
        workspace_path: Optional workspace path to restrict tool actions
        
    Returns:
        Dict with status, stdout, stderr
    """
    try:
        # Default to sandbox root if no working_dir specified
        if not working_dir:
            working_dir = SANDBOX_ROOT
        
        # If workspace_path is specified, use that as the base
        if workspace_path:
            working_dir = workspace_path
        
        # Validate working dir is within the sandbox or the active workspace
        sandbox = Path(SANDBOX_ROOT).resolve()
        wd = Path(working_dir).resolve()
        in_sandbox = str(wd).startswith(str(sandbox))
        in_workspace = bool(workspace_path) and str(wd).startswith(str(Path(workspace_path).resolve()))
        if not (in_sandbox or in_workspace):
            return {
                "status": "error",
                "message": f"Security violation: Working directory must be under {SANDBOX_ROOT} or the project workspace"
            }
        
        import subprocess
        
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode == 0:
            return {
                "status": "success",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }
        else:
            return {
                "status": "error",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Shell command failed: {e}"
        }


def run_tests(tests: List[str], workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run tests from the sandbox.
    
    Args:
        tests: List of test file paths or patterns
        workspace_path: Optional workspace path to restrict tool actions
        
    Returns:
        Dict with test results
    """
    try:
        if not tests:
            return {
                "status": "error",
                "message": "No tests specified"
            }
        
        # If workspace_path is specified, use that as the base
        if workspace_path:
            test_path = Path(workspace_path) / tests[0]
        else:
            test_path = Path(SANDBOX_ROOT) / tests[0]
        
        if not test_path.exists():
            return {
                "status": "error",
                "message": f"Test file not found: {tests[0]}"
            }
        
        import subprocess
        
        # Use workspace_path as cwd if specified, otherwise sandbox root
        cwd = workspace_path if workspace_path else SANDBOX_ROOT
        
        process = subprocess.Popen(
            f"python -m pytest {tests[0]} -v",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=60)
        
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Test execution failed: {e}"
        }
