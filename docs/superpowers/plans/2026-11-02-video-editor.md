# Built-in video editor implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Edit local training videos section by section with trims, timed annotations, per-section narration, title and credits cards, preserving source files.
**Architecture:** Extend VideoSession with a backwards-compatible ordered timeline. A dedicated editor dialog uses existing annotation canvas/design library plus Qt video frames. A sequential asynchronous exporter normalizes sections to 1280x720/30fps and joins them into one MP4. Cards and overlays share a Pillow renderer between preview and export. Existing recordings remain unchanged; old sessions become one editable section on entering the editor.
**Tech Stack:** Existing Python/PySide6/Pillow/FFmpeg; no new dependencies.
**Spec:** User approved proposed section editor and said Go for it. Both imported clips and cuts of existing footage supported as implementation choice.

## Global constraints
- Work on main as requested; do not publish a release unless requested.
- Local processing, explicit exporter-download consent, originals and old sessions preserved.
- Named sections, split/duplicate/remove/move, individual trim and volume, optional individual voiceover.
- Timed arrows/boxes/highlights/text/custom library designs, move/resize using existing canvas.
- Editable title/credits cards: text, logo, colours, duration.
- Undo/redo; save/reopen timeline; preview selected section and rendered complete sequence.

## Review focus
- Silent clips and mixed video dimensions normalize with audio silence and letterboxing.
- Split sections preserve annotation timing and voiceover alignment.
- Cancellation and failed export keep originals and existing destination.
- Invalid saved timelines/paths/timing fail clearly; old sessions load unchanged.
- Recording, pending import/probe and export prevent close/edit races.

### Task 1: Timeline model and shared rendering
- [x] Write failing tests for legacy initialization, split/move/undo persistence, invalid paths/times, cards and timed overlay rendering.
- [x] Implement timeline operations/validation and render helpers; run tests.
### Task 2: Asynchronous sequence export
- [x] Write failing tests for render plan, silent audio normalization, timed overlay filters and originals safety.
- [x] Implement owned temporary staging, per-section render and final concat with cancellation; exercise actual FFmpeg.
### Task 3: Editor UI and recording integration
- [x] Write failing UI tests for editor entry, trims, section order, annotation timing, cards and saved timeline.
- [x] Implement dialog with section list, preview/canvas, playback/split and properties; reuse annotation library and microphone recording.
- [x] Wire page entry/export and append future recordings; test compatibility.
### Task 4: Verification and documentation
- [x] Run relevant/full tests; actual synthetic media export and UI visual inspection.
- [x] Fresh independent review; fix important findings. Update guide/README, commit on main.

## Execution ledger

- Implemented inline on main, following the user's branch preference and Go for it authorization.
- Ruling: both imported clips and separately recorded sections are supported; imported files are copied into the session, while split/trim operations reference retained sources.
- Ruling: use a resizable three-pane editor dialog inside Training video, with the app's shared theme and existing annotation gestures/design library.
- Ruling: export is 1280x720 at 30 fps with letterboxing and consistent stereo/48 kHz audio. Cards are still screens and annotations are static timed overlays; motion tracking, animated transitions and scrolling credits are outside this change.
- Ruling: edited sessions use schema 2 so older binaries reject them instead of silently dropping timelines; schema 1 recordings remain readable. Limit serialized sessions to 32 MB.
- Reviewer found pending-field loss on section switches and a stale voiceover preview source. Both were reproduced with regression tests and corrected; reviewer verified resolution.
- Native preview stress exposed a Qt accessibility/text update versus multimedia teardown hang. Avoid redundant text/source resets and populate fields before stopping old playback. Annotation-only commits retain the paused frame. Regression tests and four packaged full-preview cycles passed after correction.
- Full suite: 323 passed, exit 0. Windows frozen build and synthetic native export/import/preview checks passed. No ambient microphone was recorded during automation.
- User guide/README updated. This is a source update after v0.4.0; no new release/installer publication is part of this task.
