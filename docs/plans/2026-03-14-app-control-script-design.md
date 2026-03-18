# App Control Script Design (2026-03-14)

## Goals
- Provide a single command to start, stop, restart, and check status for both backend and frontend.
- Keep behavior consistent and safe: no auto-elevation, no automatic kills for unknown processes.
- Capture logs and PIDs for easy troubleshooting.

## Entry Points
- `scripts\app.cmd`: user-facing entry point.
- `scripts\app.ps1`: implementation for `start|stop|status|restart`.

## Startup Flow
1. Resolve repo root from `scripts\` directory.
2. Read backend host/port from `backend/.env` when available; default to `127.0.0.1:8001`.
3. Read frontend dev port from `frontend/.env` when available; default to `5173`.
4. If a target port is already listening, exit with a clear message and the PID.
5. Start backend via `.venv\Scripts\python.exe -m uvicorn ...`, write logs and PID.
6. Start frontend via `npm run dev -- --host 127.0.0.1 --port <port>`, write logs and PID.
7. Verify ports are listening; if frontend fails with `spawn EPERM`, instruct user to run in elevated shell or adjust policies.

## Stop / Status
- Stop uses PID files and `taskkill /T /F` for the stored PID only.
- Status checks both PID files and live listening ports for accurate state.

## Outputs
- Backend logs: `backend\logs\backend.out.log`, `backend\logs\backend.err.log`, PID in `backend\logs\backend.pid`.
- Frontend logs: `frontend\logs\frontend.out.log`, `frontend\logs\frontend.err.log`, PID in `frontend\logs\frontend.pid`.
