"""
FastAPI File Upload/Download Module - Jubi Multi-Agent Harness API

This module handles file operations for DeepAgents sandbox:
- Upload files to thread-isolated sandbox
- Download files from sandbox
- List files in sandbox directory
- Delete files from sandbox
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import os
import shutil
import time
import uuid

router = APIRouter()


def get_sandbox_path(thread_id: str) -> str:
    """
    Get sandbox path for a thread.

    Args:
        thread_id: Thread ID from conversation

    Returns:
        Full path to thread's sandbox directory
    """
    # Sandbox root (configured in settings)
    sandbox_root = "/tmp/jubi-sandbox/"
    
    # Create thread-specific subdirectory
    thread_dir = os.path.join(sandbox_root, str(thread_id))
    
    # Ensure directory exists
    os.makedirs(thread_dir, exist_ok=True)
    
    return thread_dir


@router.post("/upload")
@router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    thread_id: Optional[str] = Form(None)
):
    """
    Upload a file to the thread sandbox.

    Args:
        file: File to upload
        thread_id: Thread ID (creates new if not provided)

    Returns:
        Upload confirmation with file path
    """
    # Create or get thread config
    if thread_id is None:
        thread_id = f"thread-{int(time.time())}"
    
    sandbox_path = get_sandbox_path(thread_id)
    
    # Save uploaded file
    file_path = os.path.join(sandbox_path, file.filename)
    
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write file to sandbox
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        return {
            "status": "uploaded",
            "thread_id": thread_id,
            "filename": file.filename,
            "path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(
    filename: str,
    thread_id: Optional[str] = None
):
    """
    Download a file from the thread sandbox.

    Args:
        filename: Filename to download
        thread_id: Thread ID (uses current if not provided)

    Returns:
        FileResponse with downloaded file
    """
    # Create or get thread config
    if thread_id is None:
        try:
            state = agent.get_state(
                config={"configurable": {"thread_id": "current"}},
                timeout=30
            )
            if state and state.values:
                messages = state.values.get("messages", [])
                # Extract last thread_id from config
                for msg in reversed(messages):
                    if isinstance(msg, dict) and "configurable" in msg:
                        thread_id = msg["configurable"].get("thread_id")
                        break
        except Exception:
            pass
    
    if thread_id is None:
        thread_id = f"thread-{int(time.time())}"
    
    sandbox_path = get_sandbox_path(thread_id)
    file_path = os.path.join(sandbox_path, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found in thread {thread_id}"
        )
    
    return FileResponse(file_path, media_type="application/octet-stream")


@router.get("/list")
async def list_files(
    thread_id: Optional[str] = None
):
    """
    List files in the thread sandbox.

    Args:
        thread_id: Thread ID (uses current if not provided)

    Returns:
        List of files with metadata
    """
    # Create or get thread config
    if thread_id is None:
        try:
            state = agent.get_state(
                config={"configurable": {"thread_id": "current"}},
                timeout=30
            )
            if state and state.values:
                messages = state.values.get("messages", [])
                for msg in reversed(messages):
                    if isinstance(msg, dict) and "configurable" in msg:
                        thread_id = msg["configurable"].get("thread_id")
                        break
        except Exception:
            pass
    
    if thread_id is None:
        thread_id = f"thread-{int(time.time())}"
    
    sandbox_path = get_sandbox_path(thread_id)
    
    try:
        files = []
        for item in os.listdir(sandbox_path):
            item_path = os.path.join(sandbox_path, item)
            stat = os.stat(item_path)
            
            files.append({
                "name": item,
                "size": stat.st_size,
                "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "type": "file" if os.path.isfile(item_path) else "directory"
            })
        
        return {
            "thread_id": thread_id,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{filename}")
async def delete_file(
    filename: str,
    thread_id: Optional[str] = None
):
    """
    Delete a file from the thread sandbox.

    Args:
        filename: Filename to delete
        thread_id: Thread ID (uses current if not provided)

    Returns:
        Deletion confirmation
    """
    # Create or get thread config
    if thread_id is None:
        try:
            state = agent.get_state(
                config={"configurable": {"thread_id": "current"}},
                timeout=30
            )
            if state and state.values:
                messages = state.values.get("messages", [])
                for msg in reversed(messages):
                    if isinstance(msg, dict) and "configurable" in msg:
                        thread_id = msg["configurable"].get("thread_id")
                        break
        except Exception:
            pass
    
    if thread_id is None:
        thread_id = f"thread-{int(time.time())}"
    
    sandbox_path = get_sandbox_path(thread_id)
    file_path = os.path.join(sandbox_path, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found in thread {thread_id}"
        )
    
    try:
        os.remove(file_path)
        
        return {
            "status": "deleted",
            "thread_id": thread_id,
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sandbox/cleanup")
async def cleanup_sandbox(thread_id: Optional[str] = None):
    """
    Clean up old sandbox directories.

    Args:
        thread_id: Thread ID to clean (None for all)

    Returns:
        Cleanup summary
    """
    sandbox_root = "/tmp/jubi-sandbox/"
    
    try:
        if thread_id is None:
            # Clean all threads older than 1 hour
            cutoff_time = time.time() - 3600
            
            cleaned_count = 0
            for item in os.listdir(sandbox_root):
                item_path = os.path.join(sandbox_root, item)
                if os.path.isdir(item_path):
                    stat = os.stat(item_path)
                    if stat.st_mtime < cutoff_time:
                        shutil.rmtree(item_path)
                        cleaned_count += 1
        
        return {
            "status": "cleaned",
            "threads_cleaned": cleaned_count,
            "note": "Old thread sandboxes (>1 hour) removed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
