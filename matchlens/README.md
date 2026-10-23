# MatchLens

MatchLens is an FTC match-video analysis workspace that runs locally on this computer.

## Current milestone

Functional now:

- Analysis-oriented web shell with navigation and a real uploaded-match library.
- FTCScout team directory with local search across all available teams.
- FastAPI health, upload, playback, annotation, and analysis endpoints.
- Local MP4 upload with metadata, a 500 MB limit, persistence in SQLite/local disk, playback, listing, and deletion.
- Manual timestamped event annotations synchronized with the player, including edit, confirm, reject, and delete actions.
- Per-video manual roster selection from FTCScout, with up to three robot teams per alliance saved alongside the analysis.
- OpenCV analysis that measures duration, FPS, dimensions, decoded frame count, and frames sampled at roughly 1 Hz.
- Optional YOLO+ByteTrack detector adapter that persists model-backed track IDs, normalized image-coordinate trajectories, confidence values, and model provenance when configured with custom robot weights.
- SQLAlchemy models and an initial Alembic migration for teams, memberships, and matches.

Not implemented yet: sign-in, authorization, team membership management, match CRUD, a durable job queue, a trained FTC robot model, calibration, field-coordinate movement metrics, reports, exports, and match comparison. The Teams page fetches the full available FTCScout public directory through the local API and searches the returned team list in the browser. The detector adapter is implemented, but actual robot detections require custom model weights with a configured robot class. Without them the UI explicitly reports detection as unavailable; no robot tracks or events are fabricated.

## Requirements

- Python 3.12 or newer (the current environment has Python 3.14.7).
- Node.js 20.9 or newer and npm 10 or newer for the frontend.
- PostgreSQL/Supabase is not required. The local database uses SQLite.

## Run locally

In PowerShell, from the repository root:

```powershell
cd .\matchlens\backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item ..\.env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

In a second PowerShell terminal:

```powershell
cd .\matchlens\frontend
npm install
npm run dev -- --port 3001
```

Both servers bind only to `127.0.0.1`, so other devices on the network cannot connect through the app's listening address. Open `http://127.0.0.1:3001`. API docs are at `http://127.0.0.1:8001/docs`; health is `http://127.0.0.1:8001/healthz`. Do not change either host to `0.0.0.0` if you want local-computer-only access.

The source targets Python 3.12+, and the API dependencies are pinned in `backend/requirements.txt`. Use `py -3.12` instead if that is the Python runtime you have installed.

## Configuration and security status

Copy `.env.example` to `backend/.env` for local configuration. `APP_MODE=local_only` does not provide authentication. Supabase variables are placeholders; setting them does not enable Supabase authentication, RLS, or storage. Do not expose this service to a network. Private upload handling and tenant authorization are not implemented yet.

Uploaded MP4 files are stored in `backend/local-videos/` and metadata/results in SQLite. The API accepts files up to 500 MB by default. Click **Analizează video** to measure video metadata and sample frames. Robot detection is unavailable, so the result moves to manual review and does not show invented tracks. Keep the API bound to `127.0.0.1`; local filesystem storage has no authentication or per-user access control.

## Optional robot detector

The detector adapter expects a custom-trained Ultralytics model whose class names include one of the configured labels (default `robot,ftc robot`). It never downloads a model automatically. Install the optional dependencies with `python -m pip install -r requirements-vision.txt`, put the trained weights on this computer, set `ROBOT_DETECTOR_MODEL` in `backend/.env` to the local `.pt` path, and restart the API. See [docs/video-processing.md](docs/video-processing.md) for details. A general COCO model is not treated as an FTC robot detector.

Each uploaded video supports manual event annotations at specific timestamps or intervals. An annotation is marked `manual` and starts `unreviewed`; confirming it is a reviewer action, not an automatic CV result. The schema is advanced with `alembic upgrade head` before starting the API.

See [docs/architecture.md](docs/architecture.md), [docs/setup.md](docs/setup.md), and [docs/privacy.md](docs/privacy.md) for decisions and limitations.