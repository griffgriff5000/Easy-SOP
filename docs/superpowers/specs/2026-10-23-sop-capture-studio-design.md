# SOP Capture Studio — design for approval

Date: 23 October 2026  
Status: Proposed; implementation has not started.

## Intent

Build a practical Windows desktop tool that turns an explicitly recorded process into an editable, illustrated Standard Operating Procedure. The application runs locally, requires no account or API key, and produces portable project folders and professional PDFs.

The supplied project prompt is the requirements baseline. The repository currently contains only its licence and Git configuration; Python 3.12.10 is available. No existing application needs migration.

## Goals and boundaries

Deliver window selection, click-triggered capture, pause/resume/stop, manual capture, editable and reorderable steps, persistent projects, annotation/redaction, PDF preview/export, settings, a demonstration project, tests and Windows packaging instructions.

The first implementation milestone is a usable capture → edit → save/reopen → PDF workflow. Complete the remaining initial-version editing and settings requirements after that milestone; the milestone does not redefine the final scope.

Future AI, OCR, Word export, SharePoint integration, shared libraries and approval workflows remain extension points, not initial-version dependencies. Never silently substitute full-desktop capture, simulate notification suppression, upload content, or require administrator access.

## Approaches

1. **Recommended: build successive working vertical slices.** Establish the project model and storage, connect native capture to the editor and PDF export, then complete annotations, settings and packaging. This exposes Windows capture limitations early and keeps the core workflow usable throughout development.
2. **Build all screens and settings first.** This makes the full navigation visible earlier but postpones validation of the highest-risk capture behavior.

The user requested a written design review before implementation. The proposed implementation approach is option 1, subject to approval of this document. The specified Python/PySide6 stack remains unchanged.

## Architecture

Use a Python package with separated modules for domain models, project persistence, Windows integration, capture orchestration, image rendering, PDF generation and Qt UI. Keep coordinate transforms, serialization and PDF layout independent of native hooks so they can be tested deterministically.

Use Python 3.12+, PySide6, Pillow, ReportLab and PyInstaller. Prefer documented Windows APIs through ctypes for window enumeration, event hooks, hotkeys and capture; introduce a Windows helper dependency only if it materially improves correctness. These dependency details are implementation decisions.

Qt owns the UI thread. A dedicated Windows message-loop thread owns the low-level mouse hook and registered global hotkey. Capture and disk work run outside hook callbacks and outside the UI thread, using a bounded queue. Signals carry results and errors to the UI. Stop disables new triggers, drains accepted work and releases hooks/hotkeys before opening editing. Pause cancels scheduled triggers that have not begun; stop finishes accepted operations. A session generation identifier prevents stale callbacks from modifying a later session.

## Windows selection and capture

Enumerate visible top-level application windows, showing executable/application name and title. Exclude this process, tool windows and unsuitable targets. Store the selected HWND and process identity for the active session; revalidate both before every capture to avoid reused window handles. A reopened project requires a fresh target selection.

The selection screen offers refresh and a preview when available. Track the target's current bounds and DPI rather than caching its starting position. Configure per-monitor DPI awareness before creating Qt windows. Store physical-pixel capture geometry with each image and use one explicit screen-to-image coordinate transform, including negative monitor coordinates and window-frame offsets.

For mouse triggers, require that the click belongs to the selected top-level window and that it is foreground. Ignore clicks in other applications. The manual hotkey also requires the selected window to be foreground. At delayed capture time, recheck focus, identity, availability and geometry; discard a trigger with a visible status message if these conditions fail. If geometry changed, transform the recorded click through its window-relative coordinates or omit its marker when it can no longer be placed reliably.

Prefer a window-only native rendering path such as PrintWindow, with explicit handling for unsupported, minimized, protected or blank output. Do not fall back to a desktop crop: it may include overlapping applications. Rendering success and GPU-content support vary by application, so test actual Chrome/Edge and native windows; unsupported targets receive a clear error rather than a misleading screenshot. Detectable blank/error cases are rejected, while the preview allows users to identify rendering failures that cannot be detected reliably.

Default capture occurs approximately 400 ms after mouse button release. Settings expose delay and selected mouse buttons. The requested before-click option uses a recent window-only frame cache while recording; it associates the most recent frame preceding mouse-down with the trigger. The UI labels this as a recent pre-click frame, with its age retained in metadata, because an exact synchronous pre-click capture cannot be guaranteed without interfering with input. Cache frames stay in memory and are discarded on pause/stop. Do not block or suppress normal input to capture them.

Use RegisterHotKey for a configurable manual screenshot shortcut; report conflicts and allow reassignment. This does not record typed input. A manual capture creates a step without a click marker. An optional initial frame behaves similarly.

Show a small always-on-top Pause/Resume/Stop toolbar and recording indicator. Exclude it from capture where supported and keep it outside the selected window; window-only rendering must not include this process's UI. Timer reports active recording time and pauses accordingly.

## Notification settings and privacy

Do Not Disturb is a best-effort optional integration only where a documented, supported API can be implemented and tested. Otherwise show truthful manual instructions and a button opening relevant Windows notification settings. Do not edit undocumented registry keys. Record and restore only settings the application actually changed, on stop, recoverable failure and normal shutdown.

No keyboard text, clipboard or accessibility field values are collected. Screenshots can inherently contain visible form values and passwords revealed on screen; do not promise automatic sensitive-data exclusion. Provide blur and solid redaction, plus a review reminder before export. No network service or telemetry is required.

## Projects and recovery

Each user-selected project directory contains project.json, Screenshots/, Annotated/ and Exports/. Step image filenames use stable UUIDs rather than order numbers; displayed numbering is derived from the ordered step list. Original PNGs are immutable. Replacement and retake operations write new originals and update the reference rather than modifying old source images.

The versioned JSON includes document metadata, ordered step IDs, titles, descriptions, timestamps, capture geometry, mouse button, click position, marker visibility/position, annotation objects, image references and revision history. Paths are relative and validated to remain within the project root when opening a project. Settings are stored separately using the operating-system user configuration location.

Save images to temporary sibling files, then atomically replace; commit JSON only after referenced images exist. Save edits with a short debounce, flush on navigation/close, and retain a last-known-good JSON backup. On reopening, validate schema and files, offer the recoverable backup where necessary, and report missing images without destroying usable steps. A project lock prevents simultaneous writers and provides explicit stale-lock recovery after a crash.

Annotated images are regenerable derivatives. Export always renders current annotations from the original; it never relies on stale cached previews. Logs contain operational errors and IDs, avoiding screenshot content, typed values and unnecessary window-title disclosure. Provide a way to open the local log directory.

## User interface and editor

A Windows-style main window uses a sidebar for Capture, Editor, Document and Settings, with light/dark themes. The Capture page shows New/Open SOP, target selection/preview, large Start button, elapsed time, status and screenshot count. Disabled controls explain prerequisites. Project creation requests title and destination, with collision-safe folder naming.

The Editor shows draggable thumbnails on the left and selected-step details on the right: title, multiline description, notes/warnings and a large screenshot canvas. Actions add/delete/reorder steps, replace or retake an image, move/hide/remove click markers and add arrows, circles and highlight boxes. Redaction supports blur and opaque rectangles. Canvas annotations use image coordinates so resizing the preview does not alter output. Undo/redo covers editing actions. Deletion and replacement remain recoverable through undo during the session.

Retake is an explicit single capture of a freshly validated selected window, with the editor hidden/minimized and focus returned to the target. It does not silently start background recording. Manual steps can contain instructions without an image; users may attach one later. Renumber automatically after all list changes.

The Document page edits company/logo, title/reference/version, author, created/updated dates, Draft/Approved status, reviewer/approver, purpose, scope, prerequisites and revision history. Approved is a document label, not an authentication or approval-workflow claim. Settings cover capture, annotations, document defaults, save location, orientation and theme; privacy commitments are presented plainly rather than as switches that can disable safeguards. PNG quality is expressed as lossless compression, since PNG has no JPEG-style quality setting.

## PDF output

ReportLab produces A4 portrait by default with optional landscape. Include cover, document information, purpose, scope, optional prerequisites, ordered procedures and revision history. Use consistent headers/footers, page numbers and aspect-preserving screenshot scaling. Render markers with current display numbers.

Keep each screenshot and its short instructions together where they fit. Split long text naturally, cap image height to usable page space, and permit continued content instead of overflowing a page. Escape user text and support Unicode through a bundled redistributable font with licence attribution. Exported images are flattened with redactions applied; originals and project JSON are never embedded in the PDF.

Preview generates a temporary PDF displayed through Qt PDF facilities. Export selects an output path and explicitly confirms replacement of an existing file. Write the final PDF atomically and open the containing folder on request.

## Validation and delivery

Automated tests cover JSON round trips and recovery, stable image associations after reordering, path validation, coordinate conversion across scaled/negative monitor geometry, annotation transforms, redacted output and PDF generation including long text, portrait/landscape and missing images. Test capture orchestration with fake Windows adapters for focus changes, pause/stop, invalid targets and hotkey failure.

On this Windows environment, exercise target enumeration and real captures against suitable available applications, including move/resize and cross-application focus changes. Record what is actually tested; multiple physical monitors, protected content and GPU applications require explicit manual coverage when equipment/apps are available. Visually inspect representative PDF pages and UI screens before calling them verified.

Deliver complete modular source, dependency configuration, README, setup/run instructions, PyInstaller spec, logging/error handling, a synthetic demonstration project with no personal data, automated tests and a documented Windows manual-test checklist. Attempt an executable build and smoke test when available tooling permits; identify any unverified packaging or platform behavior directly.

## Builder decisions and approval

The builder may choose module names, internal dataclasses, worker implementations, font, icon assets, exact colors, shortcut default and sensible retry/queue limits. Those choices must preserve the privacy and capture constraints above. Native-capture limitations must be reported rather than hidden by broader capture.

Approval of this design authorizes implementation using the recommended successive-slice approach. No product code or dependency installation has been performed as part of this design review.
