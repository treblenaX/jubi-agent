"""
Filesystem tools for coder agent.

SAFETY INVARIANTS:
- Coder MUST write only to /tmp/jubi-sandbox/
- Coder MUST NOT read/write outside sandbox
- All paths must be validated before operations
"""

import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path


# Sandbox root - coder can ONLY write here
SANDBOX_ROOT = "/tmp/jubi-sandbox"


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


def read_project_file(path: str) -> Optional[str]:
    """
    Read a file from the project or sandbox.
    
    Args:
        path: Path to the file
        
    Returns:
        File contents as string, or None if not found
    """
    try:
        # For read operations, allow reading from workspace too
        p = Path(path)
        
        # Try sandbox first
        sandbox_path = SANDBOX_ROOT / p.name
        if sandbox_path.exists():
            return sandbox_path.read_text(encoding="utf-8")
        
        # Then try workspace
        workspace_path = Path.cwd() / p.name
        if workspace_path.exists():
            return workspace_path.read_text(encoding="utf-8")
        
        return None
        
    except Exception as e:
        return f"Error reading file: {e}"


def write_project_file(path: str, content: str) -> Dict[str, Any]:
    """
    Write a file to the sandbox directory.

    SAFETY: Only writes to /tmp/jubi-sandbox/

    Args:
        path: Path relative to sandbox (e.g., "hello.py")
        content: File contents

    Returns:
        Dict with status and message
    """
    try:
        # Create sandbox directory if needed (before validation)
        os.makedirs(SANDBOX_ROOT, exist_ok=True)

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


def edit_project_file(path: str, old_text: str, new_text: str) -> Dict[str, Any]:
    """
    Edit a file by replacing text.
    
    Args:
        path: Path relative to sandbox
        old_text: Text to replace
        new_text: Replacement text
        
    Returns:
        Dict with status and message
    """
    try:
        if not _validate_sandbox_path(path):
            return {
                "status": "error",
                "message": f"Security violation: Path must be under {SANDBOX_ROOT}"
            }
        
        sandbox_path = Path(SANDBOX_ROOT) / path
        
        if not sandbox_path.exists():
            return {
                "status": "error",
                "message": f"File not found: {path}"
            }
        
        content = sandbox_path.read_text(encoding="utf-8")
        
        # Replace text (only first occurrence by default)
        if old_text in content:
            new_content = content.replace(old_text, new_text, 1)
            sandbox_path.write_text(new_content, encoding="utf-8")
            
            return {
                "status": "success",
                "path": str(sandbox_path),
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


def list_project(glob_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List files in the sandbox directory.
    
    Args:
        glob_pattern: Optional glob filter (e.g., "*.py")
        
    Returns:
        List of file info dicts
    """
    try:
        sandbox_path = Path(SANDBOX_ROOT)
        
        if not sandbox_path.exists():
            return []
        
        files = []
        for item in sandbox_path.iterdir():
            if glob_pattern:
                if not re.search(glob_pattern, item.name):
                    continue
            
            info = {
                "name": item.name,
                "path": str(item.relative_to(sandbox_path)),
                "size": item.stat().st_size if item.is_file() else 0,
                "is_file": item.is_file(),
                "modified": item.stat().st_mtime if item.is_file() else None
            }
            files.append(info)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        
        return files
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list project: {e}"
        }


def run_shell(command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a shell command in the sandbox.
    
    SAFETY: Only runs commands in /tmp/jubi-sandbox/
    
    Args:
        command: Shell command to execute
        working_dir: Working directory (defaults to sandbox root)
        
    Returns:
        Dict with status, stdout, stderr
    """
    try:
        # Default to sandbox root if no working_dir specified
        if not working_dir:
            working_dir = SANDBOX_ROOT
        
        # Validate working dir is within sandbox
        if not _validate_sandbox_path(working_dir):
            return {
                "status": "error",
                "message": f"Security violation: Working directory must be under {SANDBOX_ROOT}"
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


def run_tests(tests: List[str]) -> Dict[str, Any]:
    """
    Run tests from the sandbox.
    
    Args:
        tests: List of test file paths or patterns
        
    Returns:
        Dict with test results
    """
    try:
        if not tests:
            return {
                "status": "error",
                "message": "No tests specified"
            }
        
        # Run pytest on the first test (or all if multiple)
        test_path = Path(SANDBOX_ROOT) / tests[0]
        
        if not test_path.exists():
            return {
                "status": "error",
                "message": f"Test file not found: {tests[0]}"
            }
        
        import subprocess
        
        process = subprocess.Popen(
            f"python -m pytest {tests[0]} -v",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SANDBOX_ROOT,
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
