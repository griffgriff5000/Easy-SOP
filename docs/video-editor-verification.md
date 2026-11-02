# Built-in video editor verification

2 November 2026, Windows x64.

Implemented: named sections from one recording or imported clips; split/trim, duplicate, remove and move; per-section volume/voiceover; timed arrows, lines, boxes, ellipses, highlights, labels, callouts and shared custom annotation designs; title/credits cards with logo, text, colours and duration; local full-sequence preview and MP4 export; saved sessions and undo/redo.

Validation:

- Final automated suite: **323 passed**, exit 0, 100.47 seconds.
- PyInstaller Windows build: exit 0.
- `scripts/verify_video_editor.py` uses only generated colours/tones and an owned editor window. Actual MP4 checks cover mixed video dimensions, letterboxing, silent clips, timed overlay appearance/disappearance, title and credits frames, audio duration, delayed section voiceover, half-volume and retained original bytes.
- Actual Qt import copied/probed a synthetic clip and appended it without replacing existing footage.
- The same check ran inside the frozen executable, verifying modules came from the packaged application. Four full-preview render/play/seek cycles completed and the editor closed cleanly.
- Light-theme native UI screenshot inspected. Section/card properties use shared styled scroll panels; unrelated card/video fields are hidden.
- Independent review found two important issues (pending property loss; stale narration preview source). Both have red-to-green regressions and were confirmed resolved on recheck.
- Added regressions for keeping the paused video frame during annotation edits and avoiding redundant card text resets. An initial native stress hang was investigated using Python and native thread stacks; text changes are now populated before playback teardown and unchanged text/sources are retained. Packaged stress passed afterwards.
- One full-suite run stalled in existing document-review UI tests. Their isolated run passed; a diagnostic full-suite rerun completed, and the final full suite also passed.

Preservation and compatibility:

- Originals and voiceover takes remain unchanged. Imports are copied; edits are stored in video.json. Failed/cancelled export keeps the prior MP4 and removes only owned staging files.
- Old schema 1 recording sessions load normally. Edited timelines save as schema 2, which older applications reject rather than silently stripping the edits. Session metadata is bounded to 32 MB.
- First export uses the existing optional, consented and checksum-verified FFmpeg download. No media is uploaded. No actual microphone was activated in automated checks; test microphone hardware on the target PC.

Current limits are visible in the guide: 1280x720/30 fps output, still title/credits cards and fixed-position timed overlays. Card text must fit in its preview. This source change is not yet a published installer release.
