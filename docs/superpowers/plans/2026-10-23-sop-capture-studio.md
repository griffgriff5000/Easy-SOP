# SOP Capture Studio Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task. Steps use checkbox syntax for tracking.

**Goal:** Deliver the approved local Windows SOP recorder and PDF editor.

**Architecture:** Domain dataclasses and atomic project storage feed a Qt editor and ReportLab exporter. A native Windows adapter owns window rendering, mouse hooks and hotkeys; an asynchronous capture controller validates targets and serializes capture work.

**Tech Stack:** Python 3.12+, PySide6, Pillow, ReportLab, pytest, PyInstaller.

**Spec:** docs/superpowers/specs/2026-10-23-sop-capture-studio-design.md

## Global Constraints

- Local-only processing; explicitly selected window only; no desktop fallback.
- Preserve original PNGs and stable step IDs; write project state atomically.
- Never record typed input or clipboard contents.
- Do Not Disturb must use manual guidance unless a supported integration is verified.
- Default after-click delay 400 ms; pre-click mode uses a recent cached frame.

## Review Focus

- Focus changes during delay must discard the frame (Task 3 fake-adapter test).
- Malicious/missing image paths must not escape the project (Task 1 validation test).
- Very long instructions must paginate without layout exceptions (Task 2 PDF test).
- Image replacement and reordering must retain stable associations (Task 1 round-trip test).
- Stop and pause must release or invalidate pending work (Task 3 lifecycle test).

## Task 1: Domain, storage and coordinates

Files: pyproject.toml, requirements.txt, sop_capture/models.py, storage.py, geometry.py, tests/test_storage.py, tests/test_geometry.py.
Interfaces: Project, Step and Annotation dataclasses; ProjectStore(root).save/load/add_image; screen_to_image(point, bounds, size).

- [ ] Write and run failing round-trip, recovery, traversal, locking and coordinate tests.
- [ ] Implement UUID image storage, schema validation, atomic JSON with backup and project locks; physical coordinate transforms.
- [ ] Run pytest tests/test_storage.py tests/test_geometry.py; expect all pass. Commit.

## Task 2: Image rendering and PDF

Files: sop_capture/imaging.py, pdf_export.py, tests/test_output.py.
Interfaces: render_step(root, step, number, style) -> Pillow Image; export_pdf(project, root, output, orientation) -> Path.

- [ ] Write and run failing marker, redaction, long-text PDF, Unicode and landscape tests.
- [ ] Implement flattened annotation rendering and corporate A4 PDF with cover, metadata, sections, steps, revision history and pagination.
- [ ] Run full pytest; expect all pass. Commit.

## Task 3: Native Windows capture and lifecycle

Files: sop_capture/windows.py, capture.py, tests/test_capture.py, tests/test_windows.py.
Interfaces: WindowInfo, WindowsBackend.list_windows/validate/capture; NativeInput.start/stop; CaptureSession.start/pause/resume/stop/manual/trigger.

- [ ] Write and run failing fake-backend focus, delay, pause, stop, bounded-queue and pre-click tests; Windows enumeration smoke test.
- [ ] Implement documented native APIs, DPI setup, target identity validation, window-only PrintWindow rendering and hook/hotkey message loop with explicit cleanup.
- [ ] Implement worker scheduling and frame cache; no native work in hook callbacks.
- [ ] Run full pytest; expect all pass. Commit.

## Task 4: Desktop interface and settings

Files: sop_capture/app.py, ui/main_window.py, ui/canvas.py, ui/settings.py, ui/theme.py, tests/test_ui.py.
Interfaces: MainWindow with Capture, Editor, Document, Settings pages; annotation canvas in image coordinates; QSettings preferences.

- [ ] Write and run failing offscreen UI workflow tests for project creation, editing, reorder, undo and PDF export.
- [ ] Implement target preview/selection, toolbar, capture status, asynchronous preview, editor, annotation tools, metadata, autosave, replacement/retake, themes and PDF preview.
- [ ] Run full pytest and launch application smoke test; expect all pass. Commit.

## Task 5: Distribution, demonstration and verification

Files: SOPCaptureStudio.spec, scripts/create_demo.py, scripts/smoke_windows.py, README.md, docs/VALIDATION.md, demo/.

- [ ] Generate a synthetic demonstration project and export it; verify PDF page rendering.
- [ ] Add packaging and setup instructions; build the executable and smoke launch it.
- [ ] Exercise a real Windows target, hooks and hotkeys where the environment permits; record actual results and unverified cases.
- [ ] Run full pytest and git diff --check; get independent whole-branch review and fix important findings with regression tests.
- [ ] Record final verification and deliver runnable source/executable with limitations stated.
