# Local natural speech implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation and one final independent review.

**Goal:** Generate natural, pretrained British-English narration from typed section scripts, preview before use, and keep all processing local.
**Architecture:** Run the original sherpa-onnx Windows offline TTS executable with a Kokoro v1.0 quantized pretrained model. Both are first-use downloads from their original GitHub distributor with pinned size/hash checks, safe extraction and per-user cache; no new runtime Python dependencies. A focused speech dialog renders WAV in a disposable preview folder via an owned cancellable process. Use voiceover copies a new take into the session and records script/voice/speed on that section.
**Spec:** User approved text-to-speech after explanation that it is pretrained and local, with preview and speed control. British English is the stated starting choice; a small selection of British voices allows listening before choosing.

## Constraints and review focus
- No training, voice cloning, cloud speech or media upload. Download only after explicit first-use consent.
- Keep existing narrator takes and section data unchanged until Use voiceover is pressed.
- Retain scripts/voice/speed per section; switching/editing sections is blocked while the speech dialog is active.
- Show generated duration against section duration; warn before using narration longer than the clip (export trims to section duration).
- Cancellation/invalid output/checksum failure must not corrupt cache, audio, session or an existing take.
- Bundle no TTS runtime/models; first-use originals retain their licenses. Current-user install/cache remains separate from updates.

## Tasks
- [x] Add failing tests for downloader, archive paths/checksum/cancel, voice/script validation and CLI output ownership. (tests/test_speech_runtime.py, 14 tests)
- [x] Implement speech runtime module with verified downloads, bounded extraction, managed cache and cancellable synthesis. (sop_capture/speech_runtime.py)
- [x] Add UI tests for preview/use/cancel/stale text/section script persistence; implement dedicated speech dialog and editor entry. (sop_capture/ui/speech_dialog.py, tests/test_speech_ui.py; section `speech` metadata validated in video_timeline.py)
- [ ] Reverify real synthesis and export after fixing installation: the 3 November independent check of `scripts/verify_speech.py` failed extracting `onnxruntime_providers_shared.dll`. The Windows Store Python cache expands the path to 270 characters. Earlier synthesis claims above the review are not sufficient release evidence. Audible/visual inspection is still outstanding.
- [ ] Include active speech generation in the editor busy state so application close/update guards cover the speech worker.
- [ ] Rebuild and verify the packaged application after those fixes. The executable inspected on 3 November was dated 2 November and predates the speech implementation. No release published.

## Independent verification

On 3 November the full automated suite passed (345 tests), but actual speech installation failed as described above. The subsequent capture-window fix passed 18 focused capture tests, covering normal, maximised and full-screen restoration on success and failure. Source publication does not imply the speech feature is release-ready.
