# Training-video media tools

Recording and playback use Qt Multimedia and its dynamically loaded FFmpeg libraries. These are separate from the optional standalone MP4 exporter. No video/audio data is uploaded.

## Bundled Qt backend

The PySide6 6.12.0 Windows x64 distribution contains FFmpeg 9.0.1 shared libraries, reporting LGPL 2.1 or later. They remain dynamically replaceable DLLs. The exact configuration read from avutil-61.dll, source archives (FFmpeg 9.0.1 and zlib 1.3.1), GNU licenses, Qt provisioning scripts and source provenance are included under licenses/additional/ffmpeg in the download. See BUILDING.md there. This application's MIT license does not replace third-party licenses. Reverse engineering for debugging modifications to LGPL libraries is permitted.

## Optional MP4 exporter

The installer does **not** bundle the standalone GPL FFmpeg executable. On first MP4 export, after explicit consent, the app downloads the original Gyan 9.0.2 essentials archive directly from its GitHub release, verifies the pinned archive and executable SHA-256 checksums, extracts only ffmpeg.exe and keeps it under the current user's LocalAppData media-tools cache. It is run as a separate local process. Later exports work offline; updates retain the cache. Cancellation or verification failure leaves an existing tool intact. Your system's GitHub/network policy applies.

The exact version, original-provider URL, sizes and checksum pins are in sop_capture/media_runtime.py, independently documented by imageio-ffmpeg's v0.8.0 binary manifest. Gyan supplies the exporter under GPL version 3 or later; its original archive contains its notices. A copy of GPL v3 is included in this app's notices. Development installs optionally use the imageio-ffmpeg wheel obtained directly from PyPI; that wrapper is not included in the installer.

Upstream references:

- https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2
- https://github.com/imageio/imageio-ffmpeg/blob/v0.8.0/tools/ffmpeg-sources.json
- https://ffmpeg.org/legal.html
- https://github.com/qt/qt5/blob/6.12.0/coin/provisioning/common/windows/install-ffmpeg.ps1
