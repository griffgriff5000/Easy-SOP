# SOP Capture Studio 0.4.0 release verification

Date: 2 November 2026. Windows x64; main branch.

This release adds the Training video workspace: screen/window capture, optional microphone, explicit microphone test, pause/stop controls, later narration with synchronized preview, trimming, volume and MP4 export. Original recordings/takes stay in their own session folder.

The installer excludes the imageio standalone FFmpeg binary. First export asks before fetching Gyan 9.0.2 from its original GitHub release. Both archive and executable are size/hash checked. Download cancellation/failure preserves the existing cache. The fixed per-user cache is outside the replaceable application folder. Qt Multimedia's FFmpeg 9.0.1 LGPL shared libraries are included, with source archives, build scripts/configuration and notices under licenses/additional/ffmpeg. See FFMPEG.md and qt-ffmpeg-build.txt.

Verified before publication:

- Full automated suite: 301 passed, exit 0.
- Windows PyInstaller build: exit 0; no imageio_ffmpeg/standalone exporter in ZIP.
- Actual pinned exporter download and checksum verification, including from the frozen process.
- Frozen executable: owned synthetic window recording with microphone disabled; synthetic narration, trim, half-volume, silence padding and silent MP4 export passed. No ambient microphone recording was automated.
- Independent review of the optional downloader and UI lifecycle found no important actionable issues.
- Complete ZIP metadata, required backend sources and licenses checked; checksum sidecars generated.
- All seven supplied icon sizes matched the main EXE, updater and Setup resources.
- Native per-user installer: default Desktop/Start menu shortcuts, update, reinstall and uninstall passed; personal sentinel retained.
- Actual frozen main-app Install and restart path: update and rollback passed on isolated test copies.

The native updater test initially hit an invalid-window-handle race while closing an already disappearing helper window. The test harness now tolerates only Windows error 1400, and the full update/rollback smoke passed again. No application updater change was needed.

A Microsoft Store Python development process uses virtualized AppData; the download was therefore also exercised inside the actual frozen executable to verify the installed runtime path. Microphone hardware should be checked with Test microphone on the user's own PC.

Artifacts:

- Setup.exe: 89,779,066 bytes; SHA-256 c8b8080f15b645eb87b8a4f08b9b352b70b5915a3db41077db8ed2b630871367
- ZIP: 115,360,477 bytes; SHA-256 7f8c78c12597f36dcf9e321a389b2d5f85e8e2284ca0f0281cdf682aec2d76b3

The application is unsigned. Projects/settings/libraries remain separate. Existing 0.3.2+ clients can install through Help > Check for updates; earlier install-button versions need Setup manually once.
