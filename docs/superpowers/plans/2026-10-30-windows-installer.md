# Windows Installer Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline, followed by one fresh review.

**Goal:** Publish one Setup.exe with shortcuts and the bundled updater.

**Architecture:** Inno Setup installs the complete verified portable release into a stable App subfolder. Uninstall records stay in its parent; the existing updater replaces only App. Both download formats share the same payload.

**Tech Stack:** Python, Inno Setup 7, PyInstaller, pytest.

**Spec:** docs/superpowers/specs/2026-10-30-windows-installer.md

## Global Constraints

- Current-user installation without administrator elevation.
- Desktop shortcut selected by default; Start menu shortcut included.
- Preserve projects, templates, annotations and settings.
- Keep portable ZIP/checksum compatible with existing updater clients.
- Work on main as explicitly requested; publish v0.3.0 after verification.

## Review Focus

- Reinstall or uninstall after an in-app update must retain uninstall records and stable shortcut targets.
- Paths containing spaces must compile and install correctly.
- Missing or mismatched release payloads must fail before producing an installer.
- Uninstall must preserve files not installed by Setup and personal application data.
- Extra Setup release assets must not confuse existing ZIP update discovery.

### Task 1: Installer packaging

**Files:** Create `packaging/windows/SOPCaptureStudio.iss`, `scripts/package_installer.py`, `tests/test_installer_package.py`.

**Interfaces:** Consume the ZIP and checksum produced by `package_release.package`; produce Setup.exe and its SHA256 sidecar through `build_installer(archive: Path, compiler: Path, output: Path) -> tuple[Path, Path]`.

- [x] Write tests for verified payload staging, rejected checksum/version mismatches, compiler failure and generated installer checksum; run them and observe missing implementation failure.
- [x] Implement staging through existing strict ZIP validation and compile Inno configuration with stable App paths and isolated smoke-test overrides.
- [x] Run focused tests; expected all pass.

### Task 2: Release integration and actual installer verification

**Files:** Modify version metadata, README, `docs/RELEASING.md`, `docs/VALIDATION.md`, `scripts/smoke_updater.py`; add `scripts/smoke_installer.py`.

**Interfaces:** Consume Task 1's Setup.exe, ZIP and checksum; produce isolated installation/update/uninstall smoke results and public v0.3.0 release assets.

- [x] Bump app/project to 0.3.0, parameterize updater smoke version, document recommended Setup and portable compatibility.
- [x] Download and verify official Inno compiler, build app and both packages; expected exit 0 and matching digests.
- [x] Install to isolated directory/shortcut names, inspect Desktop and Start menu links, launch installed app and perform real update; expected stable link targets and retained uninstall records.
- [x] Uninstall test installation; expected installed files/links removed while untracked sentinel and personal application data remain.
- [x] Run full pytest and packaged application smoke; expected all pass. Obtain fresh review and fix material findings.
- [ ] Commit and push main, publish Setup/ZIP with both checksums, download/hash published assets and verify update feed parses ZIP with four assets.
