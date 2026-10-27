# SOP Capture Studio

A local Windows desktop application for recording a selected application's mouse interactions, editing illustrated procedure steps and exporting an A4 SOP PDF. Python 3.12+, PySide6, Pillow and ReportLab. No cloud service, API key or account is required.

## Run on Windows

Use a **short virtual-environment path**. Qt's installation includes long filenames that can exceed Windows' path limit when the environment is inside a deeply nested OneDrive checkout.

```powershell
python -m venv "$env:USERPROFILE\.venvs\easy-sop"
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m pip install -e '.[dev]'
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" run_studio.py
```

For normal use, `pip install -e .` installs just runtime dependencies. The `dev` extra adds pytest, pypdf and PyInstaller. No administrator privileges are required. Use Windows 10 version 2004 or later, or Windows 11. Other operating systems can run domain/PDF tests but cannot perform live Windows capture.

The generated application is `dist\SOPCaptureStudio\SOPCaptureStudio.exe`. Distribute the **whole SOPCaptureStudio folder**, including `_internal`; the executable is not a standalone single file. Build and verification status are recorded in [docs/VALIDATION.md](docs/VALIDATION.md).

## Workflow

Open **Help → User guide** or press **F1** in the application for the built-in, offline guide. Topics cover the full workflow, annotations, saving/recovery, settings and troubleshooting. **Help → Keyboard shortcuts** lists shortcuts including your currently configured manual-capture key. The Help menu also provides Open logs and About.

1. Select **New SOP**, enter a title and choose a project parent directory; or open an existing `project.json`.
2. Refresh the application list, select the target window and use **Preview selection** to confirm its capture support.
3. Enable Windows Do Not Disturb manually if required. The application links to notification settings and does not change them.
4. Select **Start capture**, perform actions in the selected window and use the floating **Pause / Resume / Stop** controls. Default: left-click release followed by a 400 ms delay. **Ctrl+Shift+F8** takes a manual screenshot while the selected target is foreground. Shortcut conflicts are reported; change the shortcut in Settings.
5. Stop, edit step titles/descriptions/notes, drag steps to reorder and add manual steps as needed. Select annotation tools and drag on the screenshot. Click or drag with the marker tool to move its marker. Undo/redo also covers edits, deletion and image replacement.
6. Complete the Document page, preview the PDF and export. File dialogs confirm replacement of existing exports. Changes autosave locally; Ctrl+S flushes immediately.

To reuse a screenshot for another instruction, select its step and choose **Duplicate step**. The copy is inserted immediately afterward, with independent titles, markers and annotations. It shares the preserved original image, so editing either copy does not change the other.

To adjust an existing arrow, circle, highlight or redaction, choose **Edit annotations** from the tool list. Drag the shape's body to move it, or drag a square handle to resize it/change an arrow endpoint. Choose **Delete selected** to remove the selected shape. Moves, resizing, deletion and duplication all support Undo/Redo and autosave. Moving a redaction can reveal previously covered content; review the result before exporting.

**Live preview and styling:** choose a tool, set its colour and stroke thickness, then drag on the screenshot. You see the actual annotation before releasing to place it; press **Esc** to cancel. Select an existing annotation with **Edit annotations** to change its settings. With nothing selected, settings apply to new shapes. Stroke and text sizes are measured in original screenshot pixels; resize handles change the shape's overall dimensions.

New tools include **Straight line**, **Translucent highlight** with adjustable opacity, and **Text label**. For labels, enter the text, choose a font size and drag a box; text wraps within that box. Enlarge the box or reduce the font size if the label is clipped. Controls are enabled for the tools they affect. Numbered click-marker styling remains on Document; solid redactions always stay opaque black.

With **Arrow** selected, the **Arrow style** dropdown shows visual examples of solid, open-head and double-headed arrows. Choose an example before drawing, or select an existing arrow under Edit annotations to change its style.

Choose a window on Capture before using **Retake selected window** in the editor. Retaking captures one image and clears that step's old marker/annotations; Undo restores them. **Replace screenshot** imports an image and also clears prior annotations. Original image files are preserved in both cases.

Settings control delay, before/after-click timing, mouse buttons, global shortcut, optional initial frame, lossless PNG compression, annotation defaults, company/author/logo defaults, save location, orientation and theme. New-project defaults do not rewrite existing projects; the Document page changes an existing project's marker style and metadata.

## Privacy and capture limitations

- Only explicitly started sessions collect click events. Live screenshots use window-only Win32 rendering; **there is no desktop capture fallback**. Own-process windows are excluded from selection, and a target must retain its HWND and process ID.
- Focus is checked at trigger and screenshot time. Off-target actions are ignored. Captures may be skipped if focus changes, the target moves during rendering, becomes minimized, closes, is protected or does not support rendering. Recording can continue after the target becomes available again.
- No typed text, password events, clipboard contents or accessibility field values are recorded. **Visible information inside screenshots can still be sensitive**, including revealed passwords. Use solid redaction for information that must be unreadable. Blur is a visual aid and is not a secure substitute for opaque redaction.
- Redactions are flattened into exported images/PDFs. Original screenshots and editable projects remain unredacted: share the reviewed PDF rather than the entire project when originals must remain private.
- Before-click mode uses the most recent in-memory frame captured before mouse-down, at most one second old. Exact synchronous pre-click capture is not guaranteed. Frame age is stored in step metadata. Cache memory is discarded on pause/stop.
- Browser GPU content, popups that are separate windows, UAC/secure desktops, DRM/protected content and elevated applications may not capture correctly. Preview first. The app cannot reliably detect every stale or partially rendered screenshot. Do not use it to bypass application protection.
- Do Not Disturb is manual; no registry tweaks or simulated success. No notification setting is changed, so none needs restoration.
- Logging is local. There is no telemetry or automatic upload. If you choose a OneDrive, SharePoint-synced or other synced project directory, **that sync client may upload files** independently of this application. Choose a non-synced local directory where required by your organisation.

## Projects and recovery

```text
SOP - Procedure name/
  project.json
  project.backup.json
  Screenshots/     # immutable PNGs with stable unique filenames
  Annotated/       # optional flattened PNGs generated by the editor
  Exports/         # reviewed PDF documents
```

Step IDs and image paths stay stable across reordering. JSON is versioned and replaced atomically after writing a temporary sibling file; a previous valid JSON is retained as backup. Capture images are saved before the project references them. Missing images leave the remaining project editable and show a warning in exported output.

If opening fails and a backup exists, the app offers recovery. An exclusive `.project.lock` prevents two normal app instances writing simultaneously. After a crash, remove a stale lock only after confirming no other instance is editing that folder; the app offers this explicitly. Do not edit an active project in a second application. Unreferenced original images are retained to avoid accidental loss and may consume additional disk space.

Application settings and rolling logs use the current Windows user profile. Select **Open logs** in the sidebar. Closing during capture initiates Stop; close again after capture has finished. Failed saves keep the window open for recovery.

## Demonstration

Open `demo\Permit Management\project.json`. Its fictional screenshots contain no real user information. Regenerate a missing demo with:

```powershell
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/create_demo.py
```

## Tests and packaging

```powershell
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m pytest -q
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/smoke_windows.py
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/smoke_windows.py --renderer-executable dist/SOPCaptureStudio/SOPCaptureStudio.exe
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/visual_check.py
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m PyInstaller --noconfirm SOPCaptureStudio.spec
.\dist\SOPCaptureStudio\SOPCaptureStudio.exe --smoke-test
```

The native smoke script creates a separate, synthetic target and checks inventory, window rendering, hook/hotkey registration and release. It does not inject input or inspect existing applications. Focus restrictions may prevent its manual-session check; it reports this rather than claiming success. `visual_check.py` saves application screenshots and PDF page renders in `.superpowers/visual` for inspection. The executable is unsigned; corporate deployment/code signing is outside this local build.

`requirements-lock.txt` records the environment used for validation. Add `-c requirements-lock.txt` to the install command to reproduce those dependency versions.

## Source layout

- `models.py`, `storage.py`, `geometry.py`: project schema, persistence and coordinate transforms.
- `windows.py`: Win32 window inventory, isolated rendering process, low-level mouse hook and global hotkey.
- `capture.py`: bounded capture queue, focus checks, delay and session lifecycle.
- `imaging.py`, `pdf_export.py`: shared flattened annotations and PDF layout.
- `ui/`: Qt capture dashboard, step editor, annotation canvas, document fields and settings.
- `app.py`, `run_studio.py`: startup, DPI setup, rotating logs and multiprocessing-safe entry points.

AI/OCR, Word export, SharePoint publishing, approval workflows and shared template libraries are future extensions. See the approved [design](docs/superpowers/specs/2026-10-23-sop-capture-studio-design.md) for the architectural boundaries.

## Third-party licences

The project uses the repository's MIT licence. Dependencies retain their own licences, including PySide6/Qt (LGPL/GPL/commercial terms), Pillow and ReportLab. The bundled PDF font is Bitstream Vera distributed with ReportLab; the packaging configuration includes ReportLab's fonts and associated licence files. Preserve the dependency notices and assess your organisation's distribution obligations before corporate rollout. Nothing in the app requires an OpenAI account or service.
