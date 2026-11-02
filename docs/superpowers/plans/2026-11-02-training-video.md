# Training Video Implementation Plan

**Approved scope:** record a screen or window with optional live microphone narration; add a new voiceover while watching a recording; preview, trim start/end, adjust narration volume and export MP4. Local processing, original assets retained. No full timeline editor is required.

**Architecture:** Qt Multimedia captures/plays media. Its Windows DLL search paths are initialized before loading the FFmpeg backend. A separate bundled FFmpeg executable performs accurate trimmed MP4 export in a background QProcess, writing an owned temporary file before atomic replacement. Each training video has an independent folder and JSON session; SOP projects and recording remain separate.

**Execution:** inline on main as requested throughout this project. Use TDD for data/export logic and UI state; run actual capture only against an owned synthetic test window, never record ambient microphone audio during automated tests. Perform one fresh code review before completion.

## Tasks

- [x] Add validated video session storage and export arguments; test persistence, path containment, trim/volume handling and original preservation.
- [x] Add lazy Qt recorder controller with explicit recording/paused/stopping states, selected screen/window and microphone, microphone test, recoverable original recording assets and asynchronous finalization.
- [x] Add Training Video screen, new/open sessions, source/microphone controls, playback, later narration, trimming, volume, MP4 export/cancel and floating recording controls. Integrate independent customizable workspace and prevent shutdown/update during recording or export.
- [x] Package multimedia plugins, FFmpeg executable and required notices; pin dependency and document source/licensing requirements for future release builds.
- [x] Verify synthetic audio/video export (duration, audio replacement, volume and originals), actual owned-window silent recording, UI transitions and full suite. Obtain fresh review and fix material findings. Commit and push main; do not publish a new release unless requested.

## Verification focus

- Microphone capture begins only on explicit Record, Record voiceover or Test microphone actions.
- Output must never overwrite source footage, narration or an existing export on failure/cancel.
- The app waits for recorder finalization and refuses close/update while recording or exporting.
- Voiceover and video share a timeline; originals remain available. Playback must be ready before narration and failures must stop the microphone.
- Errors stop capture cleanly and preserve incomplete assets for inspection.
