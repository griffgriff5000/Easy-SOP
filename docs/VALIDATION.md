# Verification — 26 October 2026

Environment: Windows, Python 3.12.10, PySide6 6.12.0, Pillow 12.3.0, ReportLab 4.5.1. Dependencies are installed in `%USERPROFILE%\.venvs\easy-sop`; the checkout-local `.venv` has an incomplete Qt installation due to Windows' path-length limit and should not be used.

## Executed checks

| Check | Result |
| --- | --- |
| Full automated suite | 82 passed, including template library, Word generation, named custom layouts, offline help and editor workflows |
| Domain and storage | Round-trip, immutable replacement images, reorder associations, recovery backup, path confinement, locking and schema validation passed |
| Coordinates | Negative monitor origin, image scaling, outside clicks and invalid dimensions passed |
| Output | Flattened redactions preserve originals, missing images, Unicode Latin text, long titles/descriptions and landscape PDF passed |
| Capture orchestration | Delayed focus rejection, stop draining, pause invalidation, pre-click frames, cache acquisition crossing pause/resume, stale/foreign input and newer-than-event frame rejection passed |
| Qt editor | Field persistence, undo/redo, reorder/export, canvas redaction and horizontal arrow behavior passed |
| Annotation editing / duplication | Independent duplicate steps, saved annotation movement, corner/arrow endpoint resizing, selected deletion, scaled Qt mouse drags, and reverse-drawn shape movement passed |
| Live preview and new tools | Every tool's non-mutating drag preview matches its committed renderer; Escape cancellation, selected colour/stroke/font/opacity, text/line/translucent-highlight persistence, and PDF screenshot pixels passed |
| Help menu | F1 opens the offline guide without an open project; topic navigation, dialog reuse and current configured shortcut text passed |
| Template library | Named profiles, duplicate rejection, stable project snapshots after library update/deletion, safe paths, old projects and apply/save rollback passed |
| Company Word | Style detection/mapping, split-run fields, original preservation, inserted/redacted images, header-logo relationships and active-field rejection passed |
| Actual Word conversion | Separate desktop Word instance generated a three-page PDF from a prepared company example; all pages rendered and inspected |
| Packaged company export | Frozen subprocess generated DOCX and PDF using bundled modules and installed desktop Word |
| Custom layout QA | Logo, Helvetica text, green headings, company footer and margins generated a six-page PDF; all pages and Templates screens inspected |
| Real Windows native APIs | Window inventory, isolated synthetic-window rendering (716 × 469 pixels), low-level hook/global hotkey registration and cleanup passed |
| Packaged rendering child | Synthetic target rendered successfully through the bundled executable's multiprocessing protocol |
| Source application | Launch and timed close completed with exit code 0 |
| PyInstaller | Folder distribution built successfully; no administrator manifest requirement |
| Packaged application | Launch and timed close completed with exit code 0 |
| Visual inspection | Capture/editor/document/settings UI and all five demonstration PDF pages rendered and inspected; PDF headers, markers, redaction, pagination and instructions were legible |
| Dependency consistency | `pip check`: no broken requirements |

The independent source reviewer found four important issues; all were reproduced by new failing tests, fixed, and followed by a passing full suite. Details are in [IMPLEMENTATION.md](IMPLEMENTATION.md).

The subsequent annotation-editing feature received an independent review. One movement issue affecting reverse-drawn shapes was reproduced for circles, highlights, solid redactions and blur regions, then fixed. The editor's selection handles and updated toolbar were visually inspected. Source and executable were rebuilt after the feature changes.

On 27 October, live previews and per-annotation styling received another independent source review with no important findings. The updated toolbar and an active blue-arrow preview alongside a text label and translucent highlight were visually inspected. A local synthetic 3840 × 2160 renderer check averaged 71 ms/frame for a text label, arrow and translucent highlight; that measures image rendering, not complete UI frame rate. Pixel previews and exports use the same renderer. Existing annotation records receive defaults for the newly added style fields; projects saved by the updated app should be opened with this version rather than an older executable.

## Limits of this verification

- Word-template PDF export was verified against installed desktop Microsoft Word on this machine. It requires a usable local Word installation and appropriate company fonts; arbitrary corporate templates/forms or Office activation/restriction environments were not supplied/tested. Imports use the documented placeholder contract or disclosed append behavior.

- Windows denied foreground activation to the unattended native smoke script. The script therefore reports its foreground manual-session check as **not verified**. It did not test actual user mouse-click events or invoke the registered hotkey while the target had focus.
- Chrome/Edge GPU content, separate popup windows, elevated targets, protected/secure content, physical multi-monitor arrangements and changed Windows DPI settings were not exercised. Unit coordinate tests are not a substitute for those checks.
- A successful PrintWindow result does not prove every target supports correct or current rendering. Use selection preview and inspect actual screenshots.
- PDF previews use Qt PDF. The PDF QA renderer also used Qt PDF because Poppler was not available on PATH. Page transparency was composited onto white for image inspection.
- The bundle is a local, unsigned build. It has not been tested on a second PC without Python, or through corporate deployment/security controls.
- No automatic Do Not Disturb integration is implemented or claimed. The app provides manual guidance and changes no notification settings.

## Manual acceptance checklist

Before regular corporate use, run these checks on the intended Windows machine and applications:

- [ ] Create a project in a non-synced local folder. Select a native application, preview, start capture and confirm the floating recording indicator is visible.
- [ ] Click in the target and confirm a screenshot/marker is created after the configured delay. Click in another app and confirm no step is added.
- [ ] Use Ctrl+Shift+F8 with the target focused; confirm a marker-free step. Reassign to another shortcut and test a registration conflict.
- [ ] Pause, perform clicks and confirm no capture. Resume and confirm fresh images. Stop with a pending screenshot and confirm it finishes before editing.
- [ ] Move and resize the target, use monitors with negative origins and different scaling, and confirm markers track the clicked position.
- [ ] Check Chrome and Edge page transitions, menus, dialogs, tabs and GPU content. Identify unsupported windows instead of assuming every popup is included.
- [ ] Minimize or close the target while recording and confirm graceful skipped captures. Verify no unrelated app is recorded.
- [ ] Drag/reorder/delete steps, undo/redo, change annotations, retake/replace a screenshot, and reopen the project to verify saved state.
- [ ] Apply solid redaction over sensitive content and inspect the PDF. Confirm originals remain in Screenshots and should not be shared.
- [ ] Preview/export portrait and landscape PDFs with a logo and long instructions. Confirm overwrite prompts and header/footer/page-break layout.
- [ ] End an app process unexpectedly, reopen the stale-locked project and verify explicit recovery. Test an unwritable destination and confirm edits remain available in memory.
- [ ] Copy the entire folder distribution to a second intended Windows PC and repeat launch, preview, click/manual capture and PDF export.

## Reference contracts

Native hook lifetime follows [Microsoft's SetWindowsHookEx documentation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowshookexw). Toolbar exclusion is best effort using [SetWindowDisplayAffinity](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity). Frozen child startup calls `multiprocessing.freeze_support()` as required by [PyInstaller's multiprocessing guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing). These API contracts do not replace the application-specific checks listed above.
