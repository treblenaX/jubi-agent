# Jubi Multi-Agent Development Framework

Jubi is a hybrid multi-agent development framework designed for autonomous software development. It follows an **Orchestrator-Worker** architecture, utilizing specialized agents to decompose, design, implement, test, and debug software projects.

By prioritizing **predictable workflows** and **shared state management**, Jubi minimizes error compounding and ensures high-fidelity implementation of technical specifications.

## 🏗️ Architecture

Jubi operates through a hierarchy of specialized agents, each with a distinct "Soul" (persona) and set of capabilities:

| Agent | Role | Primary Responsibility | Key Output |
| :--- | :--- | :--- | :--- |
| **Orchestrator** | Project Manager | Task decomposition & workflow management | `TASK_LOG.md` |
| **Architect** | System Designer | Technical specification & structural design | `BLUEPRINT.md` |
| **Coder** | Software Engineer | Implementation of the blueprint | Codebase |
| **Tester** | QA Engineer | Verification against requirements | `TEST_REPORT.md` |
| **Debugger** | Problem Solver | Root cause analysis & bug fixing | Fixed Code |
| **Researcher** | Knowledge Engineer | Technical research & uncertainty reduction | Technical Briefs |

## 📂 Project Structure

```text
jubi/
├── orchestrator/    # Central intelligence & task management
├── architect/       # System design & blueprinting
├── coder/           # Implementation & coding
├── tester/          # QA, testing, & verification
├── debugger/        # Error analysis & resolution
├── researcher/      # Technical research & synthesis
├── tester/          # QA, testing, & verification
├── workspace/       # SHARED STATE (The Source of Truth)
│   ├── BLUEPRINT.md # Technical specification
│   ├── TASK_LOG.md  # Progress tracker
│   └── TEST_REPORT.md # Quality gate
└── README.md        # Project documentation
```

## 🔄 The Jubi Workflow

1.  **Intake:** The **Orchestrator** receives a user request.
2.  **Design:** The **Architect** creates a `BLUEPRINT.md` in the `workspace/`.
3.  **Planning:** The **Orchestrator** initializes the `TASK_LOG.md`.
4.  **Execution:** The **Orchestrator** spawns the **Coder** (or **Researcher** if needed) to execute tasks from the log.
5.  **Verification:** The **Tester** runs tests against the implementation and writes a `TEST_REPORT.md`.
6.  **Optimization:** If tests fail, the **Debugger** is spawned to resolve issues.
7.  **Completion:** Once all tasks in `TASK_LOG.md` are marked `[DONE]`, the project is delivered.

## 🛠️ Setup & Running

### Prerequisites

Jubi is designed to run within an environment equipped with the following agentic capabilities:
- `spawn`: To delegate tasks to sub-agents.
- `read_file` / `write_file`: To manage the shared workspace.
- `apply_patch`: For precise code modifications.
- `exec`: To run tests and system commands.
- `web_search` / `web_fetch`: For research capabilities.

### Running a Project

To start a new development cycle, interact with the **Orchestrator**:

1.  **Initialize:** Provide a high-level goal to the Orchestrator.
    *   *Example:* `"Build a FastAPI backend for a task management system with PostgreSQL support."*
2.  **Monitor:** Watch the `jubi/workspace/TASK_LOG.md` to track progress.
3.  **Review:** Inspect `jubi/workspace/BLUEPRINT.md` to ensure the design meets your expectations before the Coder begins.
4.  **Verify:** Review the `jubi/workspace/TEST_REPORT.md` to confirm the quality of the final output.

## 🛡️ Safety & Reliability

- **State-Driven:** Agents do not rely on memory; they rely on the files in `jubi/workspace/`.
- **Discrete Checkpoints:** The Orchestrator validates the `BLUEPRINT.md` before allowing the Coder to proceed.
- **Human-in-the-Loop:** If the Debugger fails to resolve an issue after 3 attempts, the system will pause and request human intervention.

---
*Built for nanobot 🐈*
