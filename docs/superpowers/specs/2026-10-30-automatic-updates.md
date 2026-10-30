# Confirmed in-app updates

Requested: public GitHub releases; download, install and restart automatically after user confirmation.

Proposed user flow: Help > Check for updates shows installed/latest version and release notes. Download happens in the background with progress and cancel support. The app verifies the official Windows ZIP against the release SHA-256, checks archive paths and expected executables, and stages it outside the installation. Install and restart is an explicit final action. Recording/background exports must finish first; normal Word/project save-and-close guards run before installation. If closing fails, nothing is replaced.

Installation: a small separately frozen updater helper is copied outside the installation and waits for the current process to exit. It replaces the complete portable app folder, keeps the previous folder for rollback, launches the new executable, and restores the old folder if installation/startup fails. A startup handoff confirms successful UI startup. It never elevates, changes Windows policy, kills unrelated processes, or touches projects, templates, annotations, preferences or recent history. Folder permission/lock failures leave the old app available with a recovery log.

Scope: Windows x64 packaged builds. Development/source runs can check/download but do not overwrite the checkout. Only stable newer releases from griffgriff5000/Easy-SOP are offered; no downgrade or prerelease installation. Public HTTPS endpoints need no GitHub credentials. Network checks are manual initially. Release packaging includes the updater helper and matching version metadata. Existing 0.1.0 users need one manual download of the updater-enabled release; later releases update in-app.
