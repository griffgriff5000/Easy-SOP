# Windows downloads on GitHub

The Easy-SOP repository is private. Release pages and downloads require a signed-in GitHub account with access to the repository. Invite collaborators through the repository's access settings; do not change repository visibility to share a download.

The user download is the ZIP asset, not GitHub's automatically generated Source code ZIP. Users extract the complete folder and launch SOPCaptureStudio.exe. Python is bundled; personal application data is not. A fresh local template library contains Standard SOP only. Company Word templates already stored on a user's PC stay local and are never seeded into the release.

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

4. Create a draft GitHub release targeting the tested main commit, attach the ZIP and checksum, and verify the uploaded/downloaded archive matches the local checksum before publishing. A normal published release enables README's `/releases/latest` link; a prerelease is not selected by that endpoint.
5. Keep `_internal` with the EXE. Do not publish personal app-data directories, template backups or projects. Release assets are separate from the Git source history.

## First release verification

Version 0.1.0 is built from main commit `c178552` (application changes through `33a286b`). Release/package and template tests passed: 7 tests. The earlier application suite passed 226 tests. Fresh Windows build, startup, SOP/template DOCX/PDF exports, embedded Word editing, revision PDF import and authored revision export were verified before upload.

Published on 30 October 2026: [SOP Capture Studio 0.1.0](https://github.com/griffgriff5000/Easy-SOP/releases/tag/v0.1.0). The 78,333,011-byte ZIP was downloaded back through the authenticated release API and its SHA-256 matched `87607636e867389f448d10a80e5a8d59eddf5165e6f92cd55feff23bc136a397`. A checksum asset is attached. Repository visibility remains private.

Microsoft Word is not bundled and is required for direct Word editing and Word-based PDF conversion. Optional local AI requires a separate Ollama installation/model. The executable is unsigned; users should follow their organisation's Windows policies.
