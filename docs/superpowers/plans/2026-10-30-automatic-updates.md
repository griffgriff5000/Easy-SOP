# Automatic Updates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one independent final review.

**Goal:** Confirmed background download, verified installation, rollback and restart for the public Windows portable app.

**Architecture:** updates.py handles stable-release metadata, constrained downloads and staging; update_install.py handles validated plans and transactional replacement; a separately frozen updater helper waits outside the installation; update_dialog.py runs network work off the Qt thread. Startup acknowledges a successful new UI so the helper can roll back failed launches.

**Tech Stack:** Python stdlib HTTPS/ZIP/hashlib/ctypes, PySide6, PyInstaller helper EXE.

**Spec:** docs/superpowers/specs/2026-10-30-automatic-updates.md (approved via user reply).

## Constraints
- Public HTTPS requests only to the known repository and GitHub asset hosts; no credentials, shell commands or downloaded script execution.
- Only newer stable Windows x64 releases; explicit user confirmation before closing/installing.
- Validate checksums, ZIP paths/symlinks/size, manifests and expected binaries before touching installation.
- Preserve documents/settings. Refuse unsafe/overlapping roots, unsupported source runs, active capture/export and failed saves.
- Stay on main and publish a new updater-enabled release after verification, as authorised by the ongoing app distribution task.

## Review focus
- Malformed/network/cancel failures leave running app and previous installed files untouched.
- ZIP traversal, prefix collisions, symlinks, huge expanded content and wrong app/version are rejected.
- Live/locked processes and denied folder access cause bounded failure/rollback, never process killing or elevation.
- New executable crash or missing/mismatched acknowledgement restores old files; a still-running unacknowledged app is not overwritten.
- Settings/project folders are never included in replacement or cleanup; helper remains outside both app folders.

### Task 1: Release and download
- [x] Failing tests for versions/assets, domain restrictions, checksum/cancel and hostile archives.
- [x] Implement updates.py with bounded downloads and staging.
### Task 2: Transactional helper
- [x] Failing tests for root validation, replacement/rollback, startup acknowledgement and unrelated-folder preservation.
- [x] Implement update_install.py and run_updater.py; freeze the standalone helper.
### Task 3: GUI/lifecycle/release
- [x] Failing GUI tests for version/status/progress/cancel and guarded install.
- [x] Add Help dialog, save/close integration, startup acknowledgement; bump version to 0.2.0 and include helper/manifest in release.
- [x] Full tests (242 passed), real packaged apply/rollback smoke, independent review and docs.
- [x] Committed/pushed main and published v0.2.0 ZIP/checksum; uploaded/downloaded SHA-256 matched and public update feed was checked anonymously.

## Execution notes

Implemented inline on main as requested. The separate helper uses an explicit confirmation marker after normal close succeeds; cancelled closes do not install later. Production installs re-verify/re-extract the pinned archive, check ownership before and after staging, and preserve the prior folder. Parent-exit failures do not open duplicate app instances. A still-running unacknowledged new app is not overwritten. Same-version real binaries with an old-version manifest exercised physical handoff; a corrupt new executable exercised real rollback. The smoke harness waits for its own reopened test window before closing it, avoiding early-close races; it does not terminate user app processes.
