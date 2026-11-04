# Local text-to-speech narration

SOP Capture Studio can turn a typed script into a section voiceover with a pretrained, neutral British English voice. Nothing is trained or cloned, and no script or audio leaves the computer.

## Using it
1. Select a video section in the video editor and choose **Text to speech...** beside the voiceover controls.
2. Type the narration (up to 6,000 characters), pick a voice and speaking speed (x0.6 to x1.5), then **Generate preview**.
3. **Play preview** to listen. Try another voice if one does not sound right; naturalness varies by voice.
4. **Use voiceover** becomes available only for audio generated from the current script, voice and speed. Changing any of them disables it until a new preview is generated.
5. Using the voiceover saves it as a *new* take in the video session (earlier takes remain), starts it at the section start, and stores the script, voice ID and speed with the section. Undo/Redo, autosave, duplicate and split all carry that metadata.

Voices (British English): Emma (default, ID 21), Alice 20, Isabella 22, Lily 23 (female); Daniel 24, Fable 25, George 26, Lewis 27 (male).

If the narration is longer than the section, you are warned before applying it. The video length and narration speed are never changed automatically; export trims audio at the end of the section.

## First use and offline operation
The first preview asks permission to download about 154 MB (engine 21.9 MB, voice model 132.4 MB) from their original GitHub releases. Sizes and SHA-256 hashes are pinned in `sop_capture/speech_runtime.py`; archives are extracted safely (no links, traversal, reserved Windows names or oversized contents) into a staging folder and replace the cache only after every needed file verifies. A failed or cancelled download leaves the existing cache untouched. Files live under `%LOCALAPPDATA%\SOPCaptureStudio\SOPCaptureStudio\speech`, outside the installation folder, and are not in the installer. After installation, generation works offline. Files are re-verified before each run; damaged files prompt a new download.

## Upstream components and licences
- sherpa-onnx v2.0.1 offline TTS (k2-fsa), Apache License 2.0 - https://github.com/k2-fsa/sherpa-onnx
- ONNX Runtime (Microsoft), MIT licence - https://github.com/microsoft/onnxruntime
- Kokoro v1.0 int8 multi-language model, Apache License 2.0 - the model's own LICENSE and README are kept in the cache beside a `THIRD-PARTY-NOTICES.txt`.

The engine is run as a separate hidden process (no shell) with `sherpa-onnx-offline-tts.exe --kokoro-model ... --kokoro-voices ... --kokoro-tokens ... --kokoro-lexicon lexicon-gb-en.txt --sid=<voice> --speed=<speed>`. Flags were checked against the v2.0.1 `--help`.

## Verification
`python scripts/verify_speech.py` installs from the cached development archives if needed (otherwise downloads), generates real speech, applies it through the editor and checks the exported MP4 audio for long (trimmed) and short (silence-padded) narration. The packaged app can be checked with `SOPCaptureStudio.exe --speech-smoke <output.wav>` (exit 0 on success). No microphone is used.
