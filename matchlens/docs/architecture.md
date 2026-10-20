# Architecture

## Phase 1–2 boundary

The repository separates the Next.js frontend from the FastAPI backend. Backend routes, settings, SQLAlchemy models, migrations, and tests live in distinct modules. The first schema migration establishes teams, memberships, and matches as a foundation for later tenant-aware features.

The API uses explicit `APP_MODE=local_only` by default. The health endpoint reports whether Supabase configuration is present, not whether authentication or storage is operational. No synthetic match records are served by the app.

Local uploads are represented in `video_uploads`; manual timestamped observations are stored in `event_annotations`. Annotations carry `detection_source=manual` and start as `unreviewed`. Confirm/reject actions are reviewer decisions, not automatic computer-vision validation.

## Planned extension points

- Auth and storage adapters will be introduced behind service interfaces before production uploads are enabled.
- Video processing should run through a queue/worker and a replaceable detector/tracker interface, never inside a request handler.
- Current processing uses OpenCV to measure duration, FPS, resolution, decoded frame count, and approximately one sampled frame per second. The detector status is explicitly `unavailable`; no detections are fabricated.
- The optional detector adapter uses custom-configured Ultralytics weights and ByteTrack. Model detections persist into robot tracks and normalized image-coordinate points with model provenance.
- Measured facts, model estimates, manual annotations, and hypotheses will be stored and displayed with distinct provenance.
- Season definitions and field geometry will be configuration data, not application-wide constants.

## Current limitations

There is no authentication or authorization, so the API must remain local-only. The SQLAlchemy schema is a partial baseline, not a complete normalized product schema. Processing currently runs as an in-process background task, not a durable queue. No trained FTC model is bundled. Calibrated movement metrics, reporting, export, and comparison are not implemented.