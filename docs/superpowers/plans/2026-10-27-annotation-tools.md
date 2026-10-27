# Live annotation preview and styling

The user requested a preview while placing annotations, editable colours/sizes, and chose text labels, straight lines and translucent highlights as new tools.

Use the existing inline canvas rather than a separate modal editor: this keeps the screenshot visible while placing shapes. Draw with current style settings and show the actual rendered annotation during drag before committing it. Escape cancels placement. Share the renderer with PDF/PNG output so colour, geometry, text wrapping and opacity agree with export. Preview/selection overlays must never mutate saved steps.

Add colour picker, stroke width, font size, opacity and text controls. Apply changes to the selected annotation; with no selection, use them for subsequent shapes. Shape size remains adjustable via drag/resize handles. Retain the current tools, undo/redo, redaction ordering and old project compatibility. New fields have validated defaults in the version-1 schema; old projects load unchanged, while older app versions do not support new shape kinds.

- [x] Test new shape persistence/rendering, validation and redaction precedence.
- [x] Implement shared image renderer and new model fields.
- [x] Test non-mutating live preview, cancellation, selected styling and line editing through Qt events.
- [x] Implement canvas previews and a compact two-row toolbar; preserve image-coordinate editing.
- [x] Run full tests, visually inspect preview and styling, get independent review, rebuild and smoke-test executable.
