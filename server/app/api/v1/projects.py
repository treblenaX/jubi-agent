"""
Project metadata API — Jubi Multi-Agent Harness

Projects are lightweight containers that group chat threads and carry a
title + description. The description is injected into the agents' system
prompts (via ProjectContextMiddleware) so every agent understands what the
work is for without the user re-explaining it each chat.
"""

import sqlite3
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.v1.chat import _meta_conn

router = APIRouter()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


class ProjectCreate(BaseModel):
    title: str
    description: str = ""


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


def _row_to_project(row) -> dict:
    return {
        "project_id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def get_project(project_id: str) -> Optional[dict]:
    """Fetch one project (shared with chat.py for context injection)."""
    try:
        with _meta_conn() as conn:
            row = conn.execute(
                "SELECT project_id, title, description, created_at, updated_at"
                " FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return _row_to_project(row) if row else None
    except Exception:
        return None


def get_project_for_thread(thread_id: str) -> Optional[dict]:
    """Resolve the project a thread belongs to (None if unlinked/missing)."""
    try:
        with _meta_conn() as conn:
            row = conn.execute(
                """SELECT p.project_id, p.title, p.description, p.created_at, p.updated_at
                   FROM threads t JOIN projects p ON t.project_id = p.project_id
                   WHERE t.thread_id = ?""",
                (thread_id,),
            ).fetchone()
        return _row_to_project(row) if row else None
    except Exception:
        return None


@router.get("/projects")
async def list_projects():
    """List all projects (most recently updated first) with thread counts."""
    try:
        with _meta_conn() as conn:
            rows = conn.execute(
                """SELECT p.project_id, p.title, p.description, p.created_at, p.updated_at,
                          COUNT(t.thread_id) AS thread_count
                   FROM projects p
                   LEFT JOIN threads t ON t.project_id = p.project_id
                   GROUP BY p.project_id
                   ORDER BY p.updated_at DESC"""
            ).fetchall()
        return {
            "projects": [
                {**_row_to_project(r), "thread_count": r[5]}
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects")
async def create_project(body: ProjectCreate):
    """Create a project (title + description used as agent context)."""
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="title is required")
    project_id = f"proj-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    try:
        with _meta_conn() as conn:
            conn.execute(
                "INSERT INTO projects (project_id, title, description, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (project_id, body.title.strip(), body.description.strip(), _now(), _now()),
            )
        return {"project_id": project_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def read_project(project_id: str):
    """Get one project + its threads (most recently updated first)."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        with _meta_conn() as conn:
            rows = conn.execute(
                """SELECT thread_id, title, created_at, updated_at FROM threads
                   WHERE project_id = ? ORDER BY updated_at DESC""",
                (project_id,),
            ).fetchall()
        return {
            "project": project,
            "threads": [
                {"thread_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
                for r in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate):
    """Update project metadata (title and/or description)."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    fields, values = [], []
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=422, detail="title cannot be empty")
        fields.append("title = ?")
        values.append(body.title.strip())
    if body.description is not None:
        fields.append("description = ?")
        values.append(body.description.strip())
    if not fields:
        return {"project_id": project_id, "status": "unchanged"}
    fields.append("updated_at = ?")
    values.append(_now())
    values.append(project_id)
    try:
        with _meta_conn() as conn:
            conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE project_id = ?", values)
        return {"project_id": project_id, "status": "updated"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project; its threads survive (project link cleared)."""
    try:
        with _meta_conn() as conn:
            conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            conn.execute(
                "UPDATE threads SET project_id = NULL WHERE project_id = ?", (project_id,)
            )
        return {"project_id": project_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
