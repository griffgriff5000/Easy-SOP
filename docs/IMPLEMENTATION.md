# Implementation record

Approved design: `superpowers/specs/2026-10-23-sop-capture-studio-design.md`.
Plan: `superpowers/plans/2026-10-23-sop-capture-studio.md`.

## Progress

- Tasks 1–3: committed project persistence, geometry, shared annotations/PDF rendering and native capture orchestration.
- Task 4: desktop workflow implemented and committed; subsequent review fixes are covered by regression tests.
- Task 5: synthetic demonstration, setup documentation and packaging configuration added. Native rendering and executable startup have been verified; exact coverage and remaining manual checks are in `VALIDATION.md`.

## Decisions

- Work stays on `feat/sop-capture-studio` in the existing checkout. No remote publish or merge is performed.
- A short virtual environment under the current user's `.venvs/easy-sop` replaces the incomplete checkout-local environment. Windows' long-path limit prevented a complete Qt install in the deeply nested repository; no machine policy was changed.
- Qt PDF renders pages for visual QA because Poppler was not available on PATH. Transparent page backgrounds are composited onto white in QA images.
- Win32 rendering is isolated in a persistent spawned subprocess. Unsupported or timed-out rendering is rejected; no desktop fallback is introduced.
- Native smoke tests use only an isolated synthetic fixture. The unattended environment denied foreground activation; real user clicks and GPU/physical multi-monitor behavior require the documented manual checks.

## Independent source review

Reviewer checked source against the design and plan and identified four important findings. Each has a failing regression observed before its fix and a passing suite afterward:

1. In-flight cached frame crossing pause/resume: publish only if the recording generation is unchanged.
2. Queued mouse events losing event-time context: retain event timestamp, foreground/point ownership and generation; reject stale/foreign events and frames newer than the click.
3. Initial-frame timer crossing sessions: bind the callback to its originating session.
4. Horizontal/vertical arrows rejected: use gesture distance for arrows rather than rectangle-area thresholds.

After those fixes: **33 tests passed**. No minor findings were deferred by the reviewer. The reviewer did not assess physical multi-monitor/GPU behavior or executable packaging; those remain explicit verification responsibilities rather than assumed successes.

Additional final checks cover bounded-queue overload (accepted work is drained; excess triggers are reported) and loading/closing the actual Qt PDF preview. The latter reproduced a Windows file-lock failure: closing a PDF document did not immediately release its renderer's source file handle. Preview now loads from a parent-owned memory buffer, and project locks are released only after successful shutdown cleanup. Final suite: **35 passed**.

The packaged rendering check uses the same frozen child command protocol and module path as a packaged parent. An early source-parent simulation incorrectly passed Microsoft Store Python paths to the frozen child, causing an access-denied DLL import; correcting that test harness made both console and windowed packaged renderer checks pass. No Windows security policy or DLL permissions were changed.

## Annotation placement and duplicate screenshots — 26 October

Added Edit annotations: drag existing shapes to reposition them, drag handles to resize areas or change arrow endpoints, and delete the selected annotation. Image-coordinate transforms keep behavior consistent at scaled preview sizes; selection overlays are UI-only. Added Duplicate step, which deep-copies metadata and annotations under a fresh ID while sharing its immutable original PNG. Both features use existing undo/redo and autosave paths.

An independent review identified signed-dimension checks rejecting movement of reverse-drawn area shapes. Four failing parameterized tests reproduced it; absolute dimension checks fixed it. Final feature suite: 42 passed, including an actual Qt mouse-drag test. Visual QA now uses temporary copies of the demo and memory-backed PDF input, leaving the distributed example unchanged.

## Live preview, styles and new tools — 27 October

Added actual rendered previews during drag for all tools and existing-shape edits, with Escape cancellation. A shared in-memory renderer supplies preview, editor and export, and QImage conversion avoids PNG compression on every pointer movement. Drawing uses current colour/stroke/font/opacity/text settings; selected annotations can be restyled through the toolbar with undo/autosave.

Added straight lines, wrapped text labels and translucent rectangular highlights. Legacy annotation data loads with validated defaults for new fields. Redactions remain opaque and are composited last. Numbered marker style stays on Document. Independent review found no important bugs; visual review and a 4K rendering responsiveness sample were completed. Feature suite: 64 passing tests, including preview/commit equivalence for every tool and actual PDF screenshot pixels.

## Named templates and company Word documents — 27 October

Added the Templates page, local library, named custom PDF parameters, Word imports and detected paragraph-style mapping. Standard remains available. Applying creates a portable asset/settings snapshot inside the SOP; library updates/deletion do not change earlier projects. Custom layout settings include logo/company defaults, font presets/sizes/colours, margins/orientation, cover, screenshot width and step page breaks.

Word rendering replaces fixed metadata placeholders without evaluating template code, retains existing content/styles, and inserts generated annotated steps at a standalone body {{steps}} anchor. Import discloses append behavior when no anchor exists. DOCX export does not require Word; company-template PDF uses a separate installed desktop Word automation instance. Current redactions are used in both formats. A generated example is available from the Templates page.

Task tests and review fixes: snapshots and name validation, legacy projects, confined asset paths, custom PDF layout, split-run metadata/style preservation, redacted embedded images, missing anchor disclosure, apply/save rollback and unsaved template protection. Independent review found split active-field validation, header-image relationship ownership and small-margin separator collisions; each was reproduced and fixed. User .vscode configuration was preserved while returning to the implementation branch.

Final source suite: 82 passing tests. Actual Word-to-PDF conversion succeeded; all pages of a six-page custom PDF and three-page company Word PDF were rendered and inspected along with both template editor modes. The prepared example has explicit fonts and clean title styling; actual uploaded templates retain their own styling. No real company template was supplied, so arbitrary company forms are not claimed to be automatically understood.

Template-bearing project saves upgrade to schema 2 to prevent older versions silently dropping the selected layout; schema-1 projects remain readable. Packaged DOCX and Word-PDF generation were tested through the executable's frozen worker protocol. The test harness must preserve the frozen child's own runtime paths rather than replace pywin32's paths with those of the source parent. Both packaged exports succeeded after correcting that harness assumption; no machine security settings were changed.
