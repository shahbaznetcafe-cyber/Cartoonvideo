# Workflow Reliability Fix — 2026-07-17

## Root causes

- Electron always spawned Flask without checking for an existing healthy backend.
- Closing Electron killed only the virtual-environment launcher, which could leave its child Python/Flask process orphaned.
- Two Flask instances could therefore listen on port 5050 and return inconsistent in-memory job status.
- Job progress was memory-first and `job.json` writes were non-atomic.
- TTS progress was emitted only after a voice request completed, making provider waits appear stuck in story analysis.
- Provider requests had long timeouts and no per-provider circuit breaker.
- Saved Hindi `(emotion; action)` cues could keep the Hindi emotion inside the action field.

## Repairs

- Electron and Flask single-instance protection; Electron reuses a healthy backend.
- Electron now terminates its owned Python process tree on Windows.
- `/api/health` reports backend identity, PID, uptime and active jobs.
- Atomic durable job state, 3-second heartbeat, stale-job recovery and disk-backed status fallback.
- Honest `interrupted` and `stopped` resumable states.
- Voice queue/progress emitted before provider calls.
- Bounded Google, Edge and ElevenLabs TTS timeouts with five-minute failure circuit and fallback.
- Cancellation checks between voice operations.
- UI polling retries, heartbeat warnings and safe resume message instead of indefinite stale progress.
- Hindi emotion/action normalization for new scripts and old saved projects.

## Verification

- Python: 113 passed, 0 failed.
- Three.js/Node: 26 passed, 0 failed.
- Electron and frontend JavaScript syntax: passed.
- Single-instance test: second Flask attempt rejected; one port-5050 listener remained.
- Real Google Hindi TTS: 2.68 seconds for one short line.
- Real two-line voice workflow: 5.8 seconds with complete pre-request progress events.
- End-to-end fast preview: story → Google TTS → Three.js → MP4 completed in about 21 seconds.
- Output: 854x480, 24 FPS, AAC 48 kHz stereo, 1.792 seconds, no black-frame interval detected.
- Existing 18-line interrupted project loads with 0 combined semicolon action fields; first cue resolves to `surprised` + `stand`.

## Live state

- One healthy backend listener is running at `127.0.0.1:5050`.
- Previously stuck projects are marked interrupted and safe to resume.

