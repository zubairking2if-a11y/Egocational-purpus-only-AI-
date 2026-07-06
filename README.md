# Egocational-purpus-only-AI-

Pentesting — scaffolded minimal runnable layout with a secure sandboxed executor pattern.

This README now includes a clear, step-by-step installation and run guide so you (or contributors) can get the project running quickly and safely.

-----

## One-line installer (copy & paste)

Use this single command to bootstrap the project (build the headless Kali image, create the sandbox network, install Python deps, and start the backend). Make sure Docker Engine is running and you have permission to access `/var/run/docker.sock`.

- Using curl:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/zubairking2if-a11y/Egocational-purpus-only-AI-/main/scripts/install_and_run.sh)"
```

- Using wget:

```bash
bash -c "$(wget -qO- https://raw.githubusercontent.com/zubairking2if-a11y/Egocational-purpus-only-AI-/main/scripts/install_and_run.sh)"
```

Run with no Docker Compose (starts uvicorn locally):

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/zubairking2if-a11y/Egocational-purpus-only-AI-/main/scripts/install_and_run.sh)" --no-compose
```

-----

## Quick Step-by-step Install & Run

Prerequisites
- Git
- Python 3.11+ (recommended)
- pip (comes with Python)
- Docker Engine (for sandboxed container execution)
- Docker Compose v2+ (if you plan to run the sandbox compose)

1) Clone the repository

```bash
git clone https://github.com/zubairking2if-a11y/Egocational-purpus-only-AI-.git
cd Egocational-purpus-only-AI-
```

2) Create and activate a Python virtual environment

- macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

- Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3) Install Python dependencies

```bash
pip install -r requirements.txt
```

(Requirements include: fastapi, uvicorn, python-dotenv, docker==7.1.0, pyjwt)

4) Create a `.env` file (recommended)

Create a `.env` at the repo root with the values below (use secure values in production):

```dotenv
JWT_SECRET_KEY=change-this-to-a-secure-random-string
SANDBOX_MAX_EXEC_TIME=300
SANDBOX_IMAGE=kali-linux-headless:latest
```

5) Run the backend locally for development

```bash
uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

Verify the server is running:

```bash
curl http://localhost:8000/health
```

6) Run in sandboxed Docker Compose mode (backend can spawn containers)

This mode mounts the host Docker socket into the backend so that the backend can manage sandbox containers. Only run this in a trusted environment.

```bash
# example file: docker-compose.sandbox.yml
docker compose -f docker-compose.sandbox.yml up --build
```

Important notes when using the sandbox compose:
- The backend service must mount `/var/run/docker.sock:/var/run/docker.sock` so it can create child containers.
- The `pentest-sandbox-net` network should be created in the compose (internal network recommended to prevent external internet access from containers).
- Mounting the Docker socket is powerful — restrict access to this host and do not run this in multi-tenant production without additional hardening.

7) Trigger a sample scan (HTTP endpoint)

This repo contains a safe placeholder scan endpoint (`/api/v1/scan`). Adjust to your API routing if different.

Example POST using `curl`:

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","command":"echo hello-from-sandbox && sleep 1 && echo finished"}'
```

Replace `<uuid>` with a generated UUID or let your client create one.

8) View streamed logs via WebSocket

Connect to the WebSocket logs path used by the project (example):

ws://localhost:8000/ws/sessions/<session_id>/logs

Use the integration test or a WebSocket client to view live streamed output.

9) Run the pytest-asyncio integration test

Install test extras and run the test that validates end-to-end streaming:

```bash
pip install pytest pytest-asyncio httpx websockets
pytest -q tests/test_sandbox_integration.py::test_sandboxed_scan_streams_logs -k sandbox --maxfail=1
```

10) CI-friendly unit testing (mocking Docker)

To run unit tests without a Docker daemon, mock `docker.APIClient` and `ActiveSessionManager.broadcast_to_session`.
I can add an example test that uses `unittest.mock.patch` if you'd like.

-----

## Prepare a Headless Kali Sandbox Image (auto-install + run)

This project uses short-lived container sandboxes to run pentesting tools. The repo contains a `Dockerfile.kali` and scripts to build a minimal headless Kali image (`kali-linux-headless:latest`). The `scripts/install_and_run.sh` automates building the image and starting the backend. Use the one-line installer above to run everything automatically.

### Manual quick build (if you prefer):

```bash
# build the included Dockerfile.kali
./scripts/build_kali.sh kali-linux-headless:latest
# create internal network
docker network create --internal --driver bridge pentest-sandbox-net || true
# run a constrained test
docker run --rm --name sandbox-demo --network pentest-sandbox-net --cap-drop ALL --memory 512m --cpus 1.0 -e TERM=xterm-256color kali-linux-headless:latest echo hello-from-sandbox
```

-----

## Security & hardening reminders

- Never execute untrusted user-supplied commands directly on the host.
- Prefer a dedicated sandbox host or a remote, credentialed Docker API in multi-tenant environments.
- Whitelist allowed tools and arguments. Map user requests to pre-approved tool invocations rather than executing raw shell strings.
- Use an internal-only Docker network with no external routing for scans that must not access the internet.

-----

## Next actions I can take for you

If you want, I can:
- Add `backend/runner/docker_sdk_executor.py` and update imports to use it (already added in the repo).
- Add a mocked unit test for the executor so CI doesn't need Docker.
- Commit the pytest integration test into tests/ and update its endpoints to match the deployed API (already added).

Tell me which of these to commit next, or say "none" to keep changes manual.
