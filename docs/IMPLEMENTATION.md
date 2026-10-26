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
