# Resumed Monday, 26 October 2026

Historical pause record below. The user resumed on Monday, 26 October. The desktop application has since been implemented; see `IMPLEMENTATION.md` and `VALIDATION.md` for current status. The remaining text records the state at Friday's pause, not today's deliverable.

## Current work

- Branch: `feat/sop-capture-studio`.
- Approved design: `docs/superpowers/specs/2026-10-23-sop-capture-studio-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-10-23-sop-capture-studio.md`.
- Python 3.12 virtual environment at `.venv`; editable install with development dependencies was started and pytest runs successfully from it.
- Committed domain models, atomic JSON persistence with backup/lock handling, immutable PNG storage and coordinate transforms.
- Committed shared annotation/redaction renderer and ReportLab PDF exporter.
- Committed native Win32 window inventory/rendering, mouse hooks/global hotkey, and asynchronous capture lifecycle.
- Latest full test run before UI work: **19 passed**. A subsequent native-window/hotkey test file ran: **2 passed**. These results do not verify the unfinished UI.

## Uncommitted work at pause

- `sop_capture/ui/__init__.py`, `theme.py`, `settings.py`, `canvas.py`.
- `tests/test_ui.py`: test-first editor persistence, undo/redo, reorder/export and canvas redaction cases. These currently fail collection because `sop_capture/ui/main_window.py` does not exist yet.
- This handoff document.

## Resume here

1. Inspect `git status` and read the approved design and plan; retain existing work.
2. Finish Task 4: create `sop_capture/ui/main_window.py` and `sop_capture/app.py` to connect Capture, Editor, Document and Settings pages. UI tests specify `MainWindow.set_project`, `add_step`, `flush_save`, `undo`, `redo`, `reorder_steps`, `export_to`, `step_title`, `step_description`, and `canvas`.
3. Main window still needs target list/preview, recording controls/floating toolbar, bridge for background-worker signals, project creation/opening/recovery, autosave, image replacement/retake, annotation tools, metadata form and Qt PDF preview.
4. Run tests, diagnose failures, then implement distribution/demo/docs and perform actual Windows capture smoke tests and visual UI/PDF inspection.
5. Independent final code review, fix important findings with regression tests, executable packaging and final evidence are still outstanding.

## Important limits and review points

- Application is **not runnable yet**; no app entry point or main window exists.
- Live capture APIs have not yet been exercised end to end on a real external target. Unit tests primarily cover orchestration with a fake backend; window enumeration test ran on Windows.
- `WindowsBackend.capture` uses a persistent spawned rendering process and a four-second timeout; frozen packaging must call `multiprocessing.freeze_support()` before Qt startup.
- PrintWindow is the only capture source; no desktop fallback is permitted. GPU, protected/minimized and popup behavior requires honest testing/documentation.
- Capture before click uses a recent in-memory frame, not an exact synchronous pre-click image.
- Do Not Disturb uses manual guidance unless a supported implementation is verified; no integration has been implemented.
- Review schema validation, project-lock recovery, worker shutdown/callback ordering, focus transitions and stale pre-click frames before calling the app reliable.
- PDFs use ReportLab's bundled Vera fonts; packaging must include fonts and relevant licensing.
- Use `.\.venv\Scripts\python -m pytest` for verification. Whole suite currently includes intentionally unfinished UI tests.

No reminder or scheduled restart has been created. Resume when the user returns.
