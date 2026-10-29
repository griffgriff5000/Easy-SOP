# Custom shortcuts and action sequences

Users can rebind app actions, disable shortcuts, create named sequences of synchronous editor actions, and import/export JSON profiles. Settings opens a searchable shortcut dialog. QKeySequenceEdit records one key combination; conflicts include the existing global manual-capture key. App shortcuts remain window-scoped. Sequences cannot launch external programs or invoke nested sequences, dialogs, recording or asynchronous exports. Individual shortcuts can invoke those existing app actions with their normal checks.

Implementation: shortcuts.py owns action metadata, validation and execution. ui/shortcuts_dialog.py owns editing, sequence ordering and import/export. MainWindow registers all shortcuts through one controller; existing native capture shortcut remains in Settings. Profiles save to QSettings after validation and apply immediately. Invalid stored profiles fall back to defaults with a notice.

1. Add failing tests for normalization, conflicts, invalid profiles, persistence and ordered sequence execution.
2. Implement validated profiles and action controller, then the editor dialog and MainWindow wiring.
3. Test integration and guarded actions, update help/README, independent review, package and smoke-test.
