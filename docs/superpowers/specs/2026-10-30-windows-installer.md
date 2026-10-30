# Windows installer and shortcuts

User selected a Setup installer with shortcuts and bundled updater.

Design: one Windows x64 Setup.exe download. Install for the current user, without administrator elevation, beneath LocalAppData/Programs/SOPCaptureStudio. Desktop shortcut is selected by default and can be deselected; a Start menu shortcut is also installed. Both target the stable App/SOPCaptureStudio.exe path.

The complete existing app and updater live inside the App subfolder. Installer/uninstaller metadata stays in the parent installation folder so the current transactional updater can replace App without touching uninstallation records or shortcut targets. The updater remains an internal component, launched from Help > Check for updates; no separate download or shortcut is provided for it.

Keep the portable ZIP/checksum release assets for existing in-app update clients and optional portable use; offer Setup.exe as the recommended download. Keep projects/templates/annotations/preferences outside the installation and never delete personal app data during uninstall. Windows signing remains a separate next step; the installer does not suppress SmartScreen or bypass policy.

Verify actual per-user installation, Desktop/Start menu shortcut targets, app startup and updater presence, then update the installed App subfolder with the existing helper and confirm shortcuts remain valid. Uninstall tests use isolated synthetic targets/shortcuts and preserve a personal-data sentinel. Publish the installer and portable assets together as v0.3.0 after testing.
