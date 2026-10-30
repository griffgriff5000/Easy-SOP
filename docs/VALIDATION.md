# Verification — 26 October 2026

## Confirmed automatic updates — 30 October 2026

- Public v0.2.0 was published from commit 9148f5b. The 86,241,321-byte ZIP was downloaded back and matched its SHA-256; anonymous update-feed/checksum requests succeeded.
- Full automated suite: **242 passed**, exit 0. Tests cover stable versions/assets, allowed update hosts, checksum cancellation, hostile archive paths, app/version manifests, replacement/backup, rollback, running unacknowledged processes, confirmed-close cancellation, startup acknowledgement binding and GUI check/download/install separation.
- The standalone frozen updater self-test passed. The Windows build includes SOPCaptureUpdater.exe alongside the main EXE; the release ZIP contains matching RELEASE.json metadata.
- `scripts/smoke_updater.py` exercised actual frozen executable copies in isolated temporary folders: replacement and startup acknowledgement passed; a deliberately invalid new executable caused rollback and reopening of the previous app. The harness was corrected to wait for the restarted window before closing it. Only synthetic test processes/files were cleaned.
- Existing packaged SOP/template DOCX/PDF exports, native Word editing, revision transfer and authored-document exports passed. Update dialog available/verified states were visually inspected in both themes with fake release metadata; no update was installed by visual QA.
- Independent review found an unnecessary duplicate restart when the parent remained running. A failing-then-passing regression and parent-exit guard resolved it; no important issue remained. Helper installation rechecks app ownership and the pinned archive hash before replacement.
- Checks are manual and public, without credentials or document data. Version 0.1.0 needs a one-time manual installation of 0.2.0. Source checkouts do not self-replace; no elevation, process killing or Windows policy bypass is used.

## Windows download release — 30 October 2026

- Published private GitHub release v0.1.0 from main commit c178552. ZIP and SHA-256 assets are available to invited collaborators; repository visibility remains private.
- Windows build, startup, packaged SOP/template exports, native Word editing and revised-document checks passed. Seven packaging/template tests passed. The application source had previously passed all 226 tests; this release adds packaging and the missing installation dependency declaration.
- ZIP CRC checks passed. An authenticated download of the 78,333,011-byte asset matched the local SHA-256. Personal project/history/profile files are rejected by the packaging script; only the built-in Standard SOP is present in a fresh library.
- At the user's request, two saved company-template catalogue entries were cleared from the local library after creating a verified local backup. Existing project copies and retained library assets were preserved. No template backup or personal app data was uploaded.

## UI performance — 29 October 2026

- Full automated suite: **226 passed**, exit 0. Eight new regression tests cover decoded/rendered image reuse and invalidation, redaction/source immutability, library refresh and temporary-read recovery, unchanged layout writes, deferred revision previews and final Word-save timer cleanup.
- `scripts/profile_studio.py` recorded before/after profiles with isolated synthetic data. Warm shared-image 80-step project load decreased from 0.653 to 0.245 seconds; 20 selections from 0.341 to 0.098 seconds; 12 screen visits from 0.515 to 0.206 seconds. Typing/resize improvement was not established. Details and limitations are in [PERFORMANCE.md](PERFORMANCE.md).
- Source workspace and revision visual scripts completed successfully in both themes after the shared stylesheet change. Independent cache/lifecycle review found no important remaining defect.
- One earlier full run hit a temporary Windows access-denied error replacing an isolated recent-history file; its targeted rerun and the final full suite passed. No project persistence guarantees were weakened to bypass it.
- PyInstaller and packaged startup completed with exit 0. Packaged SOP/template DOCX/PDF exports, native Word edits, revision PDF import, approved transfers, floating-editor navigation and authored document export passed.

## Personal workspaces — 29 October 2026

- Full automated suite: **218 passed**, exit 0. New coverage checks independent persistence, named layouts, role-compatible copying, shared unchecked toolbar actions, screen-specific command retention, corrupt preferences/native-state fallback, floating-panel navigation, lock/reset, shortcut rebinding, workspace customisation and navigation when preference writes fail.
- `scripts/verify_workspace.py`, `scripts/verify_revision.py` and `scripts/verify_custom_workspaces.py` generated light/dark workspace and customisation-dialog captures. Screen layouts were inspected at 1000, 1280/1320 and 1440 pixels; narrow review controls scroll while approval controls remain accessible. Floating properties, copying presets, navigation and reset were exercised with isolated preferences.
- Independent review found a shared-toolbar visibility copy issue; available-action catalogues and a failing-then-passing regression resolved it. Per-screen catalogues prevent unrelated SOP commands appearing in document review after copying. Reviewer reported no remaining important issue.
- PyInstaller build and packaged startup: exit 0. Frozen SOP/template DOCX/PDF, native Word editor, revised-document transfer and edited export checks passed. Extended smoke verification embeds Word in the actual dock workspace, floats its properties/editor panel, switches to Home and back, saves and closes successfully.
- Layout preferences are local UI state, separate from documents and projects. Exact native state is used on the originating screen; cross-screen copying uses compatible panel roles/actions, retains destination-only tools and clamps floating windows to an available display.

## Assisted document revision — 29 October 2026

- Full automated suite: **207 passed**, exit 0. Focused revision coverage includes ordered Word imports, tables/artwork, numbered lists, immutable inputs, approvals/undo/reopen, PDF tables/scans/manual transcription, exact authored-file preservation, revision metadata, invalid/local-only model responses, active-field rejection and PDF preview/lock cleanup.
- `scripts/verify_revision.py` generated independent synthetic Rev A/template files, inspected the review and preview screens in light/dark themes at 1000 and 1440 pixels, and converted the resulting Rev B through installed desktop Word. The output page was visually inspected for header/footer, table, list numbering and artwork retention.
- Independent review identified equation omission and dependent note/comment transfer risks. Imports now retain the equation text and mark these elements for manual transfer; regressions pass. A manual-transfer accounting issue was resolved by allowing report-only exclusions after Word editing without changing authored bytes.
- PyInstaller build and packaged startup completed with exit 0. Extended `scripts/smoke_template_bundle.py` verified packaged PDF extraction/rendering dependencies, approved revision transfer, embedded Word edits and authored revision export, alongside the existing SOP/template DOCX/PDF checks.
- `pip check`: no broken requirements. No Ollama service/model is installed/running in this environment; the live model inference path was not exercised. Locality/proposal validation is tested with controlled responses; built-in structural assistance is exercised without a model.
- Scope: DOCX old/new and PDF old; editable whole-table transfer and manual final Word editing. PDF extraction requires review; scans offer artwork/manual transcription, without bundled OCR. Complex Word objects require manual transfer, not automatic reconstruction. Structure previews are approximate; desktop Word supplies authoritative layout.

## Project Home update — 29 October 2026

- Full automated suite: **193 passed** (exit 0).
- Home starts the application with recent project shortcuts and direct access to both reusable libraries.
- New Project combines name, saved template and parent folder, previews the destination and creates independent project copies.
- Tests cover recent history ordering, missing/corrupt entries, cancellation, folder independence, library navigation/duplication/deletion and template previews leaving the active SOP unchanged.
- `scripts/verify_home.py` rendered Home, Templates, Annotation library and New Project in light/dark themes at 1000 and 1320 pixel window widths. The rendered pages were visually inspected.
- A standalone Standard template preview generated a valid PDF without opening a project.
- Independent code review found an optional recent-history value validation issue; normalization and its regression test resolved it. No remaining important issues were reported.
- PyInstaller completed with exit 0. Packaged startup, DOCX/PDF export, edited-document export, embedded Word editing/save and automatic template preparation checks passed.

The earlier checks below describe the original implementation.

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

## Callouts, sections and review (27 October 2026)

Added tests for callout persistence, independent label/target editing and undo, redaction precedence, section range grouping/renaming, backward compatibility, PDF and Word section headings, page-per-step heading placement, checklist completeness, missing assets, navigation and cancellation before export. Synthetic callout/editor and checklist screenshots generated under `.superpowers/visual`. Offscreen Qt rendered UI fonts as missing glyphs in this environment; the Pillow callout label rendered correctly. Native Windows font appearance needs an interactive check.

Final automated suite: **92 passed**. Independent review findings on section page breaks, callout pointer hit testing and clamped-label dragging were corrected.

## Custom shortcuts (28 October 2026)

Shortcut tests cover key normalization and conflicts (including Windows/Control aliases), supported action sequences and ordering, native capture-key changes, rejected profiles, actual key-triggered step creation, persistence across windows, busy/no-project guards, profile file round trips and staged dialog edits. The editor and sequence dialog were rendered and visually inspected at `.superpowers/visual/custom-shortcuts.png` and `shortcut-sequence.png`. The Windows package rebuilt successfully and its startup smoke test returned exit code 0. Independent review found the alias conflict, now fixed and covered by regression tests.

The original main-branch environment cache changes are preserved in the named git stash `Preserve generated venv cache changes before shortcut work`; application work is on `feat/sop-capture-studio`.

## Annotation Studio (28 October 2026)

Full source suite: **124 passed**. Seventeen studio tests cover document validation, transparent compositing, rotation/opacity, embedded assets and library/pack portability, SVG input checks and local references, schema 4 persistence, redaction precedence, grouping/locking/reorder/undo, live drawing/freehand, resizing, text entry, cancellation, application placement/edit/undo, offscreen clipping, arrowhead padding, existing-callout conversion and PDF/Word image exports. Independent review findings on stale resize state, clipped arrowheads and edge-callout conversion were fixed and verified by the reviewer.

`scripts/verify_annotation_studio.py` generates synthetic studio, screenshot editor and PDF page images under `.superpowers/visual`, plus a PDF and DOCX. The studio, placed design and PDF procedure page were visually inspected. A final spacer that could produce an otherwise empty PDF page was removed and covered by the export test.

Design packs embed normalized PNG assets and ordered editable layers. External SVG references/active content are rejected; supported static SVGs are rasterized at import. Standard Windows font presets have a bundled Vera fallback. Fonts are not embedded in annotation packs. Older SOP projects load with an empty design field; SOPs with custom designs save as schema 4.

Windows build succeeded. Packaged startup returned exit code 0. Frozen DOCX, Word-template PDF and native PDF exports succeeded with vector/text layers and embedded artwork. QtSvg was included in the build.

## Studio theme contrast fix

Reproduced native dark panel backgrounds under the light app theme. Studio panels now use the app background, QDoubleSpinBox follows the input theme, disabled fields have explicit colours, and dropdown lists use app colours. Both light/dark studio property panels were rendered and inspected. Added two regression cases using a forced native dark palette; full suite: **126 passed**.

## Consistent workspace redesign (28 October 2026)

Full automated suite: **131 passed**. Existing capture, persistence, annotation, studio, template, review, shortcut and export checks remain green. New checks verify a screenshot canvas at least 400px high at 1280?800, contextual property rows, document/settings category routing, zoom coordinate mapping, Fit/pan/step-reset behaviour, studio pan without document mutation and menu rebinding/guards.

`scripts/verify_workspace.py` captures all five main pages in both themes at 1000?760, 1280?800 and 1440?900, plus studio Properties/Layers/Library, shortcut and Help dialogs under `.superpowers/workspace`. The editor, capture, document, settings, templates, studio, shortcut and Help screens were visually inspected. Step thumbnails were moved above captions to keep titles readable in narrow layouts. Precise studio geometry moved into a collapsible Position and size section.

Independent review verified that no actions were lost and category routing remained correct. Its Fit/pan findings were corrected and covered by tests. Four successive shortcut-profile rebuilds preserved menu/action bindings and enabled-state guards without runtime warnings. UI changes do not alter project schemas, captures or document export data.

Final UI package build succeeded. Packaged startup returned exit code 0, and frozen DOCX, Word-template PDF and native PDF exports with custom artwork all passed. After the final disabled-button styling adjustment, the 24 workspace/studio regression cases passed again.

## Basic document builder (28 October 2026)

Full suite: **140 passed**, with test-process exit code 0 verified. Nine tests cover rich-text parsing, inline table runs, title/company-information autosave and project undo, schema 5 backward compatibility and monotonic upgrades, simple tables, pasting without external images, long table splitting, company-information-before-steps order in PDF/Word, untouched source template bytes/header/table/end matter, and actual bold/italic font faces in PDF output.

Independent review found inline table text was split across paragraphs on paste; this was fixed with a regression test. Visual QA additionally found regular-only PDF font mapping; all four Vera faces are now registered as a family, and font embedding is tested. The reviewer verified both fixes and all nine new tests.

`scripts/verify_company_builder.py` renders the basic editor at 1000/1280 widths in light/dark, plus source PDF/DOCX and PDF page images in `.superpowers/company-builder`. The Builder screens and exported company-information page were visually inspected. Original Word templates are not round-tripped through the rich-text editor; only the new editable section is reconstructed as native Word paragraphs/tables. Existing imported templates still use Word for PDF export.

The final Windows package rebuilt successfully. Packaged startup returned exit code 0. Frozen DOCX, Word-template PDF and native PDF exports passed with company-information headings, bold/italic text and a table before the captured procedure.

## Template-aware Builder (28 October 2026)

The Builder now renders the applied template and generated SOP together in-window. A right inspector exposes document-field mirrors, extra company information and original Word paragraph/table-cell text. Source-hashed per-project patches preserve unaffected run/paragraph/table structure; complex run content and dynamic markers are protected. Word export cannot overwrite its own source template. Incompatible template edits clear on applying a new source, with project Undo restoring them.

`scripts/verify_template_builder.py` used a real imported Word template, changed an owner table cell through the new controls, and rendered a three-page document containing captured SOP screenshots. The actual Word-generated pages were visually inspected in both light/dark views. Page navigation, title/reference metadata, source immutability, run formatting, source mismatch, stale results, complex references and close-during-recording behavior have regression coverage.

Preview generation uses an immutable background snapshot and temporary output; page images are rendered on the GUI thread from a parent-owned memory PDF. Results from older edits or a different project/template are discarded. Close waits for preview generation after stopping active capture. Qt tests now retain a session application and explicitly service deferred deletion between cases, mirroring the real event loop and preventing PDF resource teardown crashes in tests.

Project schema 6 stores template text patches. The preview is read-only: fields and text controls alongside it perform edits. Source Word previews/PDFs require installed desktop Microsoft Word; the original imported/library source is never written by this workflow.

Final verification: **149 tests passed**, with test-process exit code 0. Windows packaging succeeded; packaged startup returned exit code 0. Frozen DOCX, Word-template PDF and native PDF exports passed with source-template text patches, company information, captured screenshots and custom artwork.


## Direct centre Word editor (28 October 2026)

Document > Builder now defaults to Edit document, hosting installed desktop Word in a native Qt container. The source template is copied and the captured SOP generated once, then a separate editable DOCX becomes authoritative. Schema 7 stores immutable document snapshots and a source fingerprint. Later source/step changes require an explicit confirmed Rebuild; original company templates remain unchanged. Source / preview retains the previous metadata, paragraph and company-information controls.

Final full suite: **159 passed**, test process exit **0**. Coverage includes authoritative exports, immutable snapshots, schema/path validation, explicit rebuild generation, source fingerprints, save failure/retry, project snapshot rollback, switching-project save guards, native Save As paths, and refusing to adopt or quit existing Word processes. Independent review identified the Save As path issue; it was corrected and covered by a regression test.

`scripts/verify_direct_editor.py` passed against real installed Word: embedded window parent verified, native selection typing, table editing, deletion of template instructions, project save/reopen, unchanged original template, DOCX/PDF output content, native Save As, and native document close immediately after Save As. The native Word close event tracks the saved pathname before the COM document disconnects. Actual centre rendering and caret were visually inspected in `.superpowers/direct-editor/editable-centre.png`. Word provides its own ribbon, context menus, zoom and document formatting; its theme follows the installed Word settings.

Windows package build succeeded, packaged startup returned exit **0**, and `scripts/smoke_template_bundle.py` passed frozen template DOCX, Word PDF, Standard PDF, edited-document DOCX/PDF, and the actual packaged native Word editor (embedding, native text insertion and project snapshot save). The packaged editor check runs in an isolated frozen child and closes only its synthetic document. Source tests and packaged checks do not attach the editor to users' existing Word documents.

Desktop Microsoft Word is required for direct editing and for PDFs of directly edited documents. DOCX export preserves the saved authored document without Word automation. Rebuild replaces manual document edits only after confirmation; the previous immutable version remains available through project Undo.


## Automatic company template preparation (28 October 2026)

New Word uploads now automatically inspect company paragraph styles and clear the entire main body, including template instructions, sample images, tables and body section breaks. The retained first-section page setup, header/footer parts, branding, styles and numbering define the reusable SOP layout. Source files are not modified. Prepared profiles and project snapshots record the workflow; existing structured templates and authored documents keep their previous behaviour until a new template is applied/rebuilt.

Five new regression tests cover upload preparation and save persistence, corporate title/body/step styles, source immutability, header/footer/logo/margin preservation, style numbering, split-run title prompts with artwork in the same run, first-section retention across example landscape sections, and body usage/inherited outline levels for unfamiliar style names. Title prompts are replaced in text nodes without clearing drawings. Independent review found no important defects.

`scripts/verify_prepared_template.py` processed the actual supplied `HPC-MEHALL-XX-000-TEM-900015 (1).docx`: detected MEH_Heading 1, MEH_Heading 2 and MEH_Body Text; generated a one-page SOP with purpose, steps, screenshot and revision history; removed guidance/examples; retained the MEH logo, protection markings, controlled footer and page numbering; filled the header title. Word-generated PDF page was visually inspected in `.superpowers/prepared-template/page-1.png`; original source bytes were unchanged. Those files are internal QA artifacts, not a replacement company template.

Final full suite: **164 passed, process exit 0**. A shutdown crash isolated to the new standalone template-page test came from closed editors' Python signal cycles surviving until Qt platform teardown; test fixtures now collect cycles while QApplication is alive and then service deferred deletion. No failed test-process run is counted as a successful suite.

Windows package rebuilt successfully. Packaged startup returned exit **0**. Frozen checks passed original template DOCX/Word PDF/Standard PDF, edited-document DOCX/PDF, actual embedded native Word editing and project saving, plus automatic template upload preparation and SOP generation inside the frozen application.


## Structured company templates and assisted fields (28 October 2026)

This supersedes the previous blanket body-clear importer. New uploads retain covers, company tables, all section layouts and style definitions, headers/footers, content controls and custom XML bindings. Recognised guidance and style demonstrations are removed; Lorem ipsum prose is cleared per paragraph without erasing other company table cells. Unknown company sections/content are retained. Existing explicit steps markers are retained; otherwise SOP placement uses the removed guidance location or appends. Structured documents receive a Procedure heading without duplicating an existing one.

Document > Fill template fields opens labelled retained values, with navigation to the next blank/placeholder. Recognised title/reference/revision/prepared/checked/approved-by values route to canonical Document details; company-specific values use existing source-hashed template patches. Protected/complex controls open direct editing. Changes in the two template editing views share the same patch state. Source values apply when generating/rebuilding; authored documents remain authoritative until explicit rebuild.

Linked field handling preserves controls, writes their backing custom XML/core properties and synchronises repeated display controls, including inline controls. Existing company protective markings and approval/status-code choices remain for the user. Cached TOC entries referring to removed examples are cleared; field instructions remain, with Word updating contents/figures/tables on opening for direct editing or PDF conversion. DOCX marks fields for refresh in Word.

Actual supplied templates: the simple MEH template generated a one-page SOP using MEH styles and branded page furniture. The structured HK template generated seven pages retaining the cover, six company/reference tables, two sections, contents and a new Procedure section; title/reference/revision and an edited Teamcenter ID repeated correctly across cover and metadata table. Cover, details/approval/revision tables, regenerated contents and procedure were visually inspected. Source bytes stayed unchanged. Internal verification output is under `.superpowers/prepared-template/simple` and `structured`.

Final complete suite: **173 passed, process exit 0**. Nine structured tests cover covers/tables/sections, unknown company requirements, metadata, field assistance, vertical forms, inherited outline levels, inline and repeated binding updates, explicit marker retention, duplicate-heading prevention and single-cell sample cleanup. Independent review found inherited-heading, inline-control and vertical-form issues; fixes and regressions were rechecked with no remaining important findings. Qt test cleanup explicitly disposes closed top-level widgets while QApplication remains alive; unsuccessful shutdown runs were not counted as passing.

Windows package build and startup passed (startup exit 0). Frozen verification passed template DOCX, Word PDF, Standard PDF, edited-document DOCX/PDF, embedded Word editing/project save and automatic template preparation. Old cleared library assets are not silently migrated: the original file must be re-uploaded and applied to recover a cover or tables removed by the previous workflow.


## Right-panel annotation quick selection

Step editor's right-hand Annotation panel now includes a built-in tool selector synchronised with the toolbar and a saved-design dropdown with preview icons. Choosing a saved design arms placement without mutating existing annotations. The library refreshes on dropdown open and on returning from the studio, including when a design was saved but the studio was closed without applying it. Deleted designs disappear from the list; selecting a saved design uses a copied snapshot.

Two new integration tests cover bidirectional tool selection, saved previews/loading, non-mutating selection and library refresh after save/delete. Full suite: **175 passed**, process exit **0**. The actual right panel was rendered and visually inspected in `.superpowers/quick-annotations/right-panel.png`.


## Default/custom annotation icon gallery

The right-hand Annotation pane now uses compact icon tiles: Default annotations at the top, a horizontal divider, then saved Custom annotations. Tooltips and accessible names identify each icon. A shared exclusive selection highlights only the active tool/design and stays synchronised with the toolbar. Selecting the same default tool again clears an existing annotation selection and arms new placement. Custom designs reload on panel show, manual refresh and studio return. The icon grids wrap without forcing horizontal overflow.

Behaviour checks cover built-in/custom selection, thumbnail icons, non-mutating arming, repeat tool clicks and library save/delete refresh. `scripts/verify_annotation_gallery.py` confirmed all icons fit at 1000/1320/1440 widths; the 1320 render was visually inspected in `.superpowers/quick-annotations/gallery-1320.png`.


## Magnifier annotation (29 October 2026)

Added a rectangular Magnifier under Default annotations, the toolbar and customisable shortcut actions. The lens enlarges screenshot pixels centred under its drawn box, with 1.25x?5x zoom (2x default), border colour and stroke. Existing preview, Esc cancellation, selection, move/resize, delete and Undo/Redo paths apply. It does not resize or rewrite the original screenshot, and pixels outside the lens remain unchanged apart from other intentional annotations.

Magnifiers sample a masked copy of the original screenshot, preventing redacted content from being copied into another location; masks still flatten last. Other annotations remain independent and multiple lenses do not recursively sample one another. Generated PNG, DOCX and PDF screenshots use the same renderer. Schema 8 stores magnifier zoom; non-magnifier annotations omit the new field to preserve existing-format compatibility. Older project schemas remain readable.

Seven regression cases cover enlarged pixels, source/outside immutability, both redaction orders, schema/zoom validation, live preview, zoom editing, actual mouse placement, movement/resizing, invalid style rejection, Undo/Redo and extracted DOCX/PDF screenshot pixels. Full suite: **182 passed, process exit 0**. Independent review reported no important findings.

`scripts/verify_magnifier.py` produced synthetic original/magnified images and the actual editor render under `.superpowers/magnifier`; the lens and inspector zoom control were visually inspected. The source screenshot bytes were unchanged. Windows package build succeeded and packaged startup exited 0. Frozen export verification includes a magnifier alongside custom design annotations.

Final frozen checks passed template DOCX, Word PDF, Standard PDF, authored DOCX/PDF, embedded Word editing/project save and template preparation.


## Shared template library and new project folders

New SOP now offers saved application-library templates before selecting a parent directory. The selected template is snapshotted into the newly created project folder; the library remains reusable by other projects. Existing project-specific template/document edits remain independent. Cancelling template selection creates no folder and does not switch projects. Each project folder is reserved with an atomic mkdir; name collisions produce numbered sibling folders rather than reusing an existing directory.

Two new workflow tests create two identically named projects from one saved Word template, verify distinct folders and assets, retain the first project's steps while the second starts empty, confirm editing one project copy does not alter the other or the library, and cover cancellation. Full suite: **184 passed**, process exit **0**.


## Reusable annotations across projects

Custom annotations use the application-level annotation library, shared across project folders. Step editor now offers Save selected to library for supported vector/text/custom annotations; a named reusable copy is saved without changing the selected project annotation. Studio saving also explains app-wide reuse. Default pixel tools (magnifier, blur, redaction) remain available in every project rather than becoming source-independent artwork.

Two new workflow tests save an annotation from project 1, reuse it in project 2, edit the placed copy and verify project 1 and the library are unchanged. Deleting the saved library entry leaves the embedded project-2 copy intact. Cancelling naming creates no library entry or project mutation. Complete suite: **186 passed**, process exit **0**.

During work an external checkout/reset removed the app source from the active checkout. Per the user's instruction, main remains selected; existing application files were restored from feat/sop-capture-studio into the main working folder and the new annotation action reapplied. No merge commit was created.
