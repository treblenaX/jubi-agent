"""
Workspace jail tests — project workspace_path restricts tool actions.

Covers:
- WorkspaceSandboxMiddleware injects configurable.workspace_path into
  project filesystem tool calls (and leaves other tools alone).
- filesystem tools honor workspace_path: read/write/list/shell stay inside
  the workspace; paths outside are rejected.
- Projects API roundtrip: workspace_path stored, returned, validated (422
  on nonexistent dir), clearable.
"""

import tempfile
import time
import uuid
from pathlib import Path

import pytest

from app.graph.project_context import WorkspaceSandboxMiddleware
from app.graph.tools.filesystem_tool import (
    list_project,
    read_project_file,
    run_shell,
    write_project_file,
)


@pytest.fixture
def workspace(tmp_path):
    """A real temp directory with one file in it."""
    (tmp_path / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    return str(tmp_path)


def _capture_handler(captured):
    def handler(request):
        captured.append(request)
        return "ok"

    return handler


def _tool_request(name: str, args: dict):
    from langchain.tools.tool_node import ToolCallRequest

    return ToolCallRequest(
        tool_call={"name": name, "args": args, "id": "call-1", "type": "tool_call"},
        tool=None,
        state={},
        runtime=None,
    )


class TestMiddlewareInjection:
    def test_injects_workspace_into_project_tools(self, workspace):
        mw = WorkspaceSandboxMiddleware()
        mw._workspace = lambda: workspace  # simulate configurable.workspace_path
        captured = []
        result = mw.wrap_tool_call(
            _tool_request("write_project_file", {"path": "x.py", "content": "hi"}),
            _capture_handler(captured),
        )
        assert result == "ok"
        injected = captured[0].tool_call["args"]
        assert injected["workspace_path"] == workspace
        assert injected["path"] == "x.py"  # original args preserved

    def test_overrides_model_supplied_workspace(self, workspace):
        """Model cannot widen the jail by passing its own workspace_path."""
        mw = WorkspaceSandboxMiddleware()
        mw._workspace = lambda: workspace
        captured = []
        mw.wrap_tool_call(
            _tool_request(
                "run_shell",
                {"command": "ls", "workspace_path": "/etc"},
            ),
            _capture_handler(captured),
        )
        assert captured[0].tool_call["args"]["workspace_path"] == workspace

    def test_no_injection_without_workspace(self):
        mw = WorkspaceSandboxMiddleware()
        mw._workspace = lambda: None
        captured = []
        mw.wrap_tool_call(
            _tool_request("write_project_file", {"path": "x.py"}),
            _capture_handler(captured),
        )
        assert "workspace_path" not in captured[0].tool_call["args"]

    def test_non_project_tools_untouched(self, workspace):
        mw = WorkspaceSandboxMiddleware()
        mw._workspace = lambda: workspace
        captured = []
        mw.wrap_tool_call(
            _tool_request("web_search", {"query": "hi"}),
            _capture_handler(captured),
        )
        assert "workspace_path" not in captured[0].tool_call["args"]


class TestFilesystemTools:
    def test_write_and_read_relative_path_in_workspace(self, workspace):
        result = write_project_file("src/app.py", "x = 1\n", workspace_path=workspace)
        assert result["status"] == "success"
        assert result["path"] == str(Path(workspace) / "src" / "app.py")
        assert read_project_file("src/app.py", workspace_path=workspace) == "x = 1\n"

    def test_read_rejects_path_outside_workspace(self, workspace):
        assert read_project_file("/etc/passwd", workspace_path=workspace) is None
        assert read_project_file("../../etc/passwd", workspace_path=workspace) is None

    def test_write_rejects_path_outside_workspace(self, workspace):
        result = write_project_file("../../evil.py", "x", workspace_path=workspace)
        assert result["status"] == "error"
        assert "Security violation" in result["message"]
        assert not (Path(workspace).parent / "evil.py").exists()

    def test_list_project_lists_workspace(self, workspace):
        files = list_project(workspace_path=workspace)
        names = [f["name"] for f in files]
        assert "hello.py" in names
        # sandbox files must not leak in
        assert all(f["path"] for f in files)

    def test_run_shell_runs_inside_workspace(self, workspace):
        result = run_shell("pwd", workspace_path=workspace)
        assert result["status"] == "success"
        assert result["stdout"].strip() == workspace

    def test_run_shell_workspace_overrides_working_dir(self, workspace):
        """With a workspace jail, cwd is forced to the workspace — the model
        cannot cd elsewhere via working_dir."""
        result = run_shell("pwd", working_dir="/etc", workspace_path=workspace)
        assert result["status"] == "success"
        assert result["stdout"].strip() == workspace

    def test_run_shell_rejects_outside_dir_without_workspace(self):
        result = run_shell("pwd", working_dir="/etc")
        assert result["status"] == "error"
        assert "Security violation" in result["message"]


class TestProjectsApi:
    def test_workspace_roundtrip_and_validation(self, client, workspace):
        # Create with a valid workspace
        r = client.post(
            "/projects",
            json={"title": f"ws-{uuid.uuid4().hex[:6]}", "workspace_path": workspace},
        )
        assert r.status_code == 200, r.text
        pid = r.json()["project_id"]
        assert r.json()["workspace_path"] == workspace

        # GET returns it
        got = client.get(f"/projects/{pid}").json()["project"]
        assert got["workspace_path"] == workspace

        # List returns it
        listed = [p for p in client.get("/projects").json()["projects"] if p["project_id"] == pid]
        assert listed and listed[0]["workspace_path"] == workspace

        # Update (change) then clear with empty string
        r = client.put(f"/projects/{pid}", json={"workspace_path": ""})
        assert r.status_code == 200
        got = client.get(f"/projects/{pid}").json()["project"]
        assert got["workspace_path"] is None

        # Cleanup
        assert client.delete(f"/projects/{pid}").status_code == 200

    def test_workspace_must_exist(self, client):
        r = client.post(
            "/projects",
            json={"title": f"bad-{int(time.time())}", "workspace_path": "/nonexistent-dir-xyz"},
        )
        assert r.status_code == 422
        assert "existing directory" in r.json()["detail"]


class TestWorkspaceList:
    def test_lists_directories_with_parent(self, client):
        unique = f"ws-list-{uuid.uuid4().hex[:8]}"
        target = Path("/tmp") / unique
        target.mkdir()
        try:
            r = client.get("/workspace/list", params={"path": "/tmp"})
            assert r.status_code == 200
            data = r.json()
            assert data["path"] == "/tmp"
            assert data["parent"] == "/"
            assert {"name": unique, "path": str(target)} in data["entries"]
        finally:
            target.rmdir()

    def test_defaults_to_home(self, client):
        r = client.get("/workspace/list")
        assert r.status_code == 200
        assert r.json()["path"] == str(Path.home().resolve())

    def test_file_path_is_404(self, client):
        r = client.get("/workspace/list", params={"path": "/etc/hostname"})
        assert r.status_code == 404
