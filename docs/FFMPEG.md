# Training-video media tools

Recording/playback uses Qt Multimedia and its dynamically loaded FFmpeg backend. MP4 trimming, narration replacement and volume processing run the separate FFmpeg executable supplied by the pinned `imageio-ffmpeg` wheel. No video/audio data is uploaded.

`imageio-ffmpeg` is BSD-licensed. Its included FFmpeg executable has its own license. The Windows 0.8.0 wheel used here reports FFmpeg 9.0.2 under GPL version 3 or later (`ffmpeg -L`). Running the executable as a separate process does not replace this application's MIT license; bundled third-party code retains its license.

The [GPL v3 text](licenses/FFmpeg-GPL-3.0.txt) and this notice are included under licenses/ffmpeg by the release packager when the executable is present.

Before distributing a new installer containing that executable, include its GPL license/third-party notices and provide the complete corresponding source and build information for the actual FFmpeg build, including applicable enabled dependencies. The existing release notice collector includes dependency distribution licenses, but that alone does not satisfy the binary's source-distribution obligations. Do not publish a video-enabled release until these artifacts have been reviewed and supplied.

Upstream references:

- https://github.com/imageio/imageio-ffmpeg (wrapper, binary provenance/pins and build tooling)
- https://ffmpeg.org/legal.html (FFmpeg licensing)
- https://ffmpeg.org/download.html (upstream source)

Developers can inspect the packaged executable with `imageio_ffmpeg.get_ffmpeg_exe()` and run it with `-version` and `-L` to verify its build configuration and license.
