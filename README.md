# Egocational-purpus-only-AI-

Pentesting — scaffolded minimal runnable layout with a secure sandboxed executor pattern.

This repository provides a small FastAPI backend scaffold intended for educational pentesting exercises. To reduce risk, the project uses a containerised sandbox pattern so scanning tools run inside isolated Docker containers rather than as host subprocesses.

## What's new in this repo

- A production-grade Docker SDK executor (backend/runner/docker_sdk_executor.py) that runs pentesting tools inside isolated containers using the official docker-py SDK and streams logs to the websocket terminal.
- An integration test template (tests/test_sandbox_integration.py) using pytest-asyncio + websockets to validate end-to-end log streaming from sandboxed containers.
- Updated dependency: docker==7.1.0 in requirements.txt to use the latest SDK features.

## Quickstart

Prereqs:
- Docker Engine (for local sandboxing)
- Python 3.11+ recommended

1. Create and activate a virtualenv, install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the backend locally (development):

```bash
uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

3. (Optional) Run with Docker Compose and allow the backend to start sandboxes by mounting the Docker socket:

```bash
# Use the sandbox compose file (example: docker-compose.sandbox.yml)
docker compose -f docker-compose.sandbox.yml up --build
```

When using the sandbox compose, ensure the backend service mounts `/var/run/docker.sock` so it can create child containers and that `pentest-sandbox-net` network exists or is declared in the compose.

## API endpoints (example)

- Health: GET /health
- Scan request (example placeholder): POST /api/v1/scan
  - Example JSON: {"session_id": "<uuid>", "command": "echo hello"}

Your actual endpoints and payload shapes may vary. The integration test template is configurable to point to your real HTTP and WS routes.

## Sandbox executor

We replaced direct host subprocess calls with a Docker SDK executor for two reasons:

1. Security: Running tools in short-lived containers prevents them from accessing the host filesystem or network (when configured) and allows strict resource limits.
2. Reliability: The docker-py SDK exposes lifecycle control and structured errors instead of string-parsing CLI output.

The new executor lives at: `backend/runner/docker_sdk_executor.py` and exposes `run_sandboxed_container_tool(session_id, raw_command)` which:
- Creates a hardened container (capabilities dropped, memory and CPU limits)
- Attaches to stdout/stderr and forwards logs to ActiveSessionManager.broadcast_to_session
- Enforces a global execution timeout (SANDBOX_MAX_EXEC_TIME)

If you prefer the docker CLI pattern, see the older `backend/runner/docker_executor.py` approach (not recommended for production due to escaping and subprocess concerns).

## Integration tests

A pytest-asyncio integration test template is provided at `tests/test_sandbox_integration.py`. It:
- POSTs a scan request to your HTTP scan endpoint with a unique session_id
- Connects to your WebSocket logs endpoint `ws://host/ws/sessions/{session_id}/logs` and collects streamed output
- Asserts that logs are received and the container finished

Install test deps:

```bash
pip install pytest pytest-asyncio httpx websockets
pytest -q tests/test_sandbox_integration.py::test_sandboxed_scan_streams_logs -k sandbox
```

## Security & hardening notes

- Never run untrusted student-provided commands directly on the host. Always route execution through an isolated sandbox.
- Mounting `/var/run/docker.sock` gives the backend powerful control over the Docker host. Restrict who can start the backend or run builds in production. Consider an alternative DinD or remote Docker API with strict access controls in multi-tenant environments.
- Use `pentest-sandbox-net` as an internal, isolated network (no external internet) when running dangerous tools.
- Sanitize and whitelist allowed commands/tools. Do not accept arbitrary shell strings unless you validate or map them to pre-approved tool containers.

## Development notes

- Requirements updated: `docker==7.1.0` (commit bumped)
- To switch to the new executor, update any import references pointing to the old executor:

```py
# old
from backend.runner.docker_executor import run_sandboxed_container_tool

# new
from backend.runner.docker_sdk_executor import run_sandboxed_container_tool
```

- Ensure your `docker-compose` mounts the Docker socket and defines `pentest-sandbox-net`.

## Next steps

If you'd like, I can:
- Commit the `backend/runner/docker_sdk_executor.py` file and also add a unit test that mocks docker.APIClient so CI doesn't require a real Docker daemon.
- Update the integration test paths to the exact routes your backend exposes.
- Add a short HOWTO for building a hardened sandbox image (recommended base: a minimal Kali image or specially-built tool image with only the allowed binaries).

## License

This project uses GNU GPL-3.0 as specified in the repository metadata.

