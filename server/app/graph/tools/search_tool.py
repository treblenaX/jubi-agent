"""
Search tools for grep operations within project files.

SAFETY INVARIANTS:
- Researcher MUST NOT write to any filesystem
- Only read-only operations allowed
"""

import re
from typing import Optional, List, Dict, Any


def grep_project(pattern: str, path: str = ".", glob: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for patterns in project files.
    
    SAFETY: Read-only operation - never writes to filesystem
    
    Args:
        pattern: Regex or literal text to search for
        path: Search root directory (default: current workspace)
        glob: Optional path filter (e.g., "*.py")
        
    Returns:
        List of matches with context and source locators
    """
    try:
        import os
        
        matches = []
        
        # Walk through files
        for root, dirs, files in os.walk(path):
            # Skip common noise directories
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]
            
            for filename in files:
                # Apply glob filter if specified
                if glob and not re.search(glob, filename):
                    continue
                
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Search for pattern
                    if re.search(pattern, content, re.IGNORECASE):
                        # Find all matches
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            line_num = content[:match.start()].count('\n') + 1
                            
                            matches.append({
                                "file": filepath,
                                "line": line_num,
                                "match": match.group(),
                                "context_before": content[max(0, match.start()-50):match.start()],
                                "context_after": content[match.end():match.end()+50] if match.end() < len(content) else ""
                            })
                            
                except (UnicodeDecodeError, IOError):
                    # Skip binary files or read errors
                    continue
        
        return matches
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Grep failed: {e}"
        }
