# Annotation editing and screenshot duplication

Requested behavior: reposition existing annotations and reuse a screenshot for another procedural step.

Implementation decisions: add an Edit annotations tool. Drag a shape's body to move it; drag square handles to resize rectangles/ellipses or change arrow endpoints. Selected shapes can be deleted. Use image coordinates and constrain gestures to image boundaries. Editing creates one undo checkpoint per completed gesture; selection alone does not change a project. Selection handles never appear in PDF/PNG exports.

Duplicate step inserts an independently editable deep copy immediately after the selected step, assigns a new stable ID and reuses the immutable original PNG. Copy annotations, titles, instructions and marker state; changing the duplicate must not affect its source. Undo, redo, autosave and numbering follow existing editor behavior.

- [x] Add failing UI tests for duplicate independence/order/persistence/undo and shape move/resize/delete at scaled display sizes.
- [x] Implement image-coordinate hit testing and edit gestures in canvas.py; wire edit/delete controls and duplication in main_window.py.
- [x] Run the full suite, inspect the editor, review the change and rebuild the executable.

No schema migration or external service is needed.
