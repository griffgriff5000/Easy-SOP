# Windows downloads on GitHub

The Easy-SOP repository is now public. Release pages and assets are available without signing in. Runtime update checks and downloads use public HTTPS endpoints without GitHub credentials. The first release was private at publication; the owner subsequently changed repository visibility.

The recommended user download is the versioned Windows x64 Setup.exe asset, not GitHub's automatically generated Source code ZIP. Setup creates Desktop and Start menu shortcuts and bundles the updater. The portable ZIP remains available for existing update clients. Python is bundled; personal application data is not. A fresh local template library contains Standard SOP only. Company Word templates already stored on a user's PC stay local and are never seeded into the release.

## Preparing a release

1. Use the short development environment described in README.md and install the required runtime/development dependencies. `pyproject.toml` declares the PDF import dependency as well as the other runtime libraries.
2. Run appropriate tests and build on Windows:

   ```powershell
   python -m PyInstaller --noconfirm SOPCaptureStudio.spec
   python scripts/smoke_template_bundle.py dist/SOPCaptureStudio/SOPCaptureStudio.exe
   ```

3. Gather license notices for the selected Python/Qt runtime, including the applicable open-source license texts, then package:

   ```powershell
   python scripts/package_release.py --licenses <license-notices-folder>
   ```

   The script writes `dist/releases/SOPCaptureStudio-<version>-Windows-x64.zip` and its `.zip.sha256` checksum. It includes the complete folder build, app license, quick-start guide, dependency metadata and installed dependency license files. It rejects builds containing personal project/history/template-profile files. It also checks archive CRCs. Review the included notices and runtime versions before distributing.

4. Install the official signed [Inno Setup compiler](https://jrsoftware.org/isdl.php) (tested with 7.1.1 x64), then build and verify Setup from that same ZIP:

   ```powershell
   python scripts/package_installer.py dist/releases/SOPCaptureStudio-0.3.0-Windows-x64.zip --compiler "C:\path\to\ISCC.exe"
   python scripts/smoke_installer.py dist/releases/SOPCaptureStudio-0.3.0-Windows-x64.zip --compiler "C:\path\to\ISCC.exe"
   ```

   The smoke uses a unique uninstall registration and unique shortcut names, installs to a temporary directory with spaces, updates the actual installed App folder, and uninstalls while checking an untracked personal-file sentinel survives. It does not replace real app shortcuts.

5. Create a draft GitHub release targeting the tested main commit. Attach **four assets**: Setup.exe, its `.exe.sha256`, the portable ZIP and its `.zip.sha256`. Verify uploaded/downloaded bytes match local checksums before publishing. A normal published release enables README's `/releases/latest` link; a prerelease is not selected by that endpoint.
6. Keep `_internal` with the EXE. Do not publish personal app-data directories, template backups or projects. Release assets are separate from the Git source history.

## Setup layout and data preservation

Setup installs without elevation to `%LOCALAPPDATA%\Programs\SOPCaptureStudio`. Application files, including `SOPCaptureUpdater.exe`, are in its `App` subfolder. Desktop (selected by default) and Start menu shortcuts target `App\SOPCaptureStudio.exe`. Uninstall records stay in the parent folder, so automatic updates replace App while retaining those records and stable shortcuts.

Uninstall removes files installed by Setup and the shortcuts. It does not delete projects or `%LOCALAPPDATA%\SOPCaptureStudio\SOPCaptureStudio`, which contains personal settings and libraries. Updater rollback folders are retained. Do not add broad recursive uninstall deletion rules. The installer is unsigned until code signing is configured; it does not remove SmartScreen warnings.

## Updater-enabled releases

Version 0.2.0 adds Help > Check for updates. The build spec creates a separate one-file SOPCaptureUpdater.exe and includes it beside SOPCaptureStudio.exe. The ZIP packager adds RELEASE.json with the matching app/version. Keep these names and the exact `SOPCaptureStudio-<version>-Windows-x64.zip` plus `.zip.sha256` naming for future stable releases. Bump both pyproject.toml and sop_capture.__version__ before building.

The client downloads and verifies the ZIP, then asks before saving/closing. A helper copied outside the installation waits for a confirmed close, re-verifies/extracts the archive beside the old app, preserves the previous folder, and launches the new app. The new UI acknowledges its token/version; startup failures roll back only after the new process exits. The helper never elevates or kills processes. Users whose app folder contains personal files must update manually in a clean folder.

Run `python scripts/smoke_updater.py dist/releases/SOPCaptureStudio-0.2.0-Windows-x64.zip` to exercise successful handoff and rollback with isolated real executable copies. Source runs cannot replace the checkout. Existing 0.1.0 users must download the first updater-enabled ZIP manually once.

Published on 30 October 2026: [v0.2.0](https://github.com/griffgriff5000/Easy-SOP/releases/tag/v0.2.0), source commit `9148f5b`. ZIP size: 86,241,321 bytes. SHA-256: `63edd0ebd0b40aa531a3a82a7276a93650f9c32cafdf9afa6c890b09253c801a`. Uploaded/downloaded bytes matched before publication. The public update feed and checksum asset were verified without authentication.

## First release verification

Version 0.1.0 is built from main commit `c178552` (application changes through `33a286b`). Release/package and template tests passed: 7 tests. The earlier application suite passed 226 tests. Fresh Windows build, startup, SOP/template DOCX/PDF exports, embedded Word editing, revision PDF import and authored revision export were verified before upload.

Published on 30 October 2026: [SOP Capture Studio 0.1.0](https://github.com/griffgriff5000/Easy-SOP/releases/tag/v0.1.0). The 78,333,011-byte ZIP was downloaded back through the authenticated release API and its SHA-256 matched `87607636e867389f448d10a80e5a8d59eddf5165e6f92cd55feff23bc136a397`. A checksum asset is attached. Repository visibility remains private.

Microsoft Word is not bundled and is required for direct Word editing and Word-based PDF conversion. Optional local AI requires a separate Ollama installation/model. The executable is unsigned; users should follow their organisation's Windows policies.

## Installer release verification

Published on 30 October 2026: [v0.3.0](https://github.com/griffgriff5000/Easy-SOP/releases/tag/v0.3.0), source commit `86b84ea`. Setup: 63,326,550 bytes, SHA-256 `974e0f8faf562d1e1ad643386c435e79c6fdb08f460ee4cb25d3f671814a627e`. Portable ZIP: 86,242,706 bytes, SHA-256 `0019067a4896ea308f91c2d6e5ddc843547136ee8f1b29b6ae7136b3d0c09631`. All four uploaded assets were downloaded back and verified before publication. The public latest-release feed selects the ZIP correctly alongside Setup, and the installer checksum is accessible without authentication. Validation: 248 automated tests, packaged Word/PDF/revision checks, install/update/reinstall/uninstall, and successful-update/failed-startup rollback smokes.
