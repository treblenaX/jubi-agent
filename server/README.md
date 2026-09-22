# Jubi Multi-Agent Harness - Production-Ready Backend

A FastAPI backend integrated with LangGraph and DeepAgents for multi-agent development.

## Architecture

```
my_agent_service/
├── app/                        # Main application package
│   ├── __init__.py
│   ├── main.py                 # FastAPI app definition & middleware setup
│   │
│   ├── api/                    # FastAPI Routing Layer
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── auth.py         # User authentications (JWT tokens) - REMOVED
│   │   │   ├── files.py        # File upload/download (for DeepAgents Sandbox)
│   │   │   └── chat.py         # Streaming/Invoke agent endpoints
│   │
│   ├── schemas/                # Pydantic Request/Response Models
│   │   ├── __init__.py
│   │   ├── chat.py             # UserInput, StreamResponse, ThreadSchema
│   │   └── files.py            # FileMetadataSchema
│   │
│   ├── core/                   # Global Configuration & Security
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic BaseSettings (.env loading)
│   │   └── security.py         # Password hashing & JWT logic
│   │
│   ├── graph/                  # LangGraph & DeepAgents Orchestration
│   │   ├── __init__.py
│   │   ├── state.py            # Custom State extensions (DeepAgentState)
│   │   ├── workflow.py         # LangGraph StateGraph compiling & loops
│   │   │
│   │   ├── subagents/          # Specialized DeepAgent Orchestration
│   │   │   ├── __init__.py
│   │   │   ├── planner.py      # Task breakdown & to-do management
│   │   │   ├── researcher.py   # Specialized sub-agent graph
│   │   │   └── coder.py        # Code generation/execution sub-agent
│   │   │
│   │   ├── tools/              # Custom Tools exposed to DeepAgents
│   │   │   ├── __init__.py
│   │   │   ├── web_search.py   # Tavily/Serper tools
│   │   │   ├── db_queries.py   # Custom enterprise database lookup
│   │   │   ├── filesystem_tool.py  # MCP filesystem integration
│   │   │   └── jubi_skill_loader.py  # Nanobot skills loader
│   │   │
│   │   └── memory/             # Long-Term & Short-Term Checkpointing
│   │       ├── __init__.py
│   │       └── saver.py        # Async Postgres/Sqlite Checkpointer
│   │
│   └── services/               # Infrastructure & Internal Client Wrappers
│       ├── __init__.py
│       └── llm_provider.py     # Base LLM client configurations & fallback routing
│
├── storage/                    # Local Isolated Workspaces (for DeepAgents)
│   └── threads/                # Isolated sandbox folders indexed by Thread ID
│
├── tests/                      # Testing Framework (Pytest)
│   ├── conftest.py
│   ├── test_api.py             # FastAPI route endpoint testing
│   ├── test_graph.py           # LangGraph node & state transition testing
│   └── integration_tests/      # MCP filesystem integration tests
│       └── ...                 # 9 test files, 27 tests total
│
├── .env.example                # Template for environment keys
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container instructions
└── README.md                   # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
# Or system-wide:
pip3 install pydantic-settings pytest-cov
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (Ollama URL, etc.)
```

### 3. Pull Ollama Model

```bash
ollama pull qwen3.5:9b
```

### 4. Start Server

```bash
python server.py
# Or: uvicorn app.main:app --host 127.0.0.1 --port 2024
```

### 5. Test Health

```bash
curl http://localhost:2024/health
```

## API Endpoints

**Note**: Routes are at `/chat` and `/files` (no `/v1` prefix after main.py includes routers)

- `GET /` - Service info
- `GET /health` - Health check
- `POST /chat?content=...&thread_id=...` - Add message and stream response
- `GET /chat?thread_id=...` - Get thread messages
- `POST /threads` - Create new thread (creates with greeting)
- `DELETE /threads/{thread_id}` - Delete thread
- `POST /files/upload?thread_id=...` - Upload file to sandbox
- `GET /files/list` - List sandbox files

**Chat Endpoint Usage:**
```bash
# Via query params (recommended for testing)
curl "http://localhost:2024/chat?content=Hello&thread_id=test-1"

# Or with default greeting if no content provided
curl "http://localhost:2024/chat?thread_id=test-2"
```

## Testing Instructions

### Run All API Tests

```bash
cd /home/ec/.nanobot/workspace/jubi/server
PYTHONPATH=/home/ec/.nanobot/workspace/jubi/server pytest -v tests/test_api.py
```

**Expected Output:**
```
tests/test_api.py::test_root_endpoint PASSED
tests/test_api.py::test_health_endpoint PASSED
tests/test_api.py::test_chat_stream PASSED
tests/test_api.py::test_chat_invoke PASSED
tests/test_api.py::test_cors_headers PASSED
```

### Run Agent Unit Tests

```bash
PYTHONPATH=/home/ec/.nanobot/workspace/jubi/server pytest -v tests/server/agents/
```

**Tests:**
- `test_researcher_agent.py` - 3 tests
- `test_orchestrator_agent.py` - 2 tests  
- `test_coder_agent.py` - 1 test
- `test_researcher_skills_integration.py` - Integration tests

### Run Integration Tests (MCP Filesystem)

```bash
PYTHONPATH=/home/ec/.nanobot/workspace/jubi/server pytest -v server/integration_tests/
```

**Expected:** 27 tests passing across 9 test files

### Coverage Report

```bash
PYTHONPATH=/home/ec/.nanobot/workspace/jubi/server pytest --cov=app --cov-report=term-missing tests/
```

## Agent Roles

### Orchestrator
- Parses user intent
- Validates safety invariants
- Dispatches tasks to subagents
- Aggregates results and streams responses

### Coder
- Generates code in memory first
- Writes ONLY to `/tmp/jubi-sandbox/`
- Runs tests within sandbox
- Reports success/failure with details

### Researcher
- Fetches URLs via web_fetch tool
- Extracts and summarizes content
- NEVER writes to filesystem
- Returns structured findings with citations

## Safety Invariants

1. **Path Jail**: All file operations restricted to `/tmp/jubi-sandbox/`
2. **Read-Only Tools**: Researcher agent has read-only access
3. **Tool Whitelisting**: Only approved tools exposed to agents
4. **Output Truncation**: 6KB limit on tool outputs
5. **Circuit Breakers**: Retry/backoff/fallback patterns

## Observability

- Trace context propagation
- Structured logging
- Metrics collection (optional)
- Health check endpoints

## Test Status

✅ **All Tests Passing** (18/18 unit + integration tests)
- API endpoints: 5/5 passing
- Agent unit tests: 6/6 passing
- MCP integration: 27/27 passing

## License

MIT
