# Annotation Studio implementation plan

Goal: draw and combine custom designs, customise existing shapes, import PNG/JPEG/SVG artwork, and reuse editable designs on SOP screenshots.

Architecture: a bounded, versioned design document contains an ordered list of editable vector/text/path/image layers and embedded normalized PNG artwork. annotations/designs.py validates documents, imports artwork, renders via Pillow, and stores atomic named library entries and portable JSON packs. ui/annotation_studio.py is the Qt layer editor and ui/design_canvas.py is the drawing surface. Annotation kind design embeds a snapshot in project schema 4. Existing annotation/capture behavior remains supported. One renderer produces transparent previews, PNG, screenshot composites and PDF/Word images. Redactions remain flattened last.

Design: canvas up to 2048x2048, up to 100 layers, 2000 points per path, image decode limits and bounded pack size. SVG imports accept static local vectors; reject external references, script and embedded active content, rasterize with QtSvg. PNG/JPEG are copied and normalized; imported assets stay immutable in existing projects if library files or originals change. Font presets sans/serif/mono with bold/italic use bundled fonts so exports stay portable.

Studio UI: New; saved-design library load/save/save-as/delete; import artwork/pack; export editable pack/transparent PNG. Drawing tools select, rectangle, ellipse, triangle, diamond, arrow, line, text, freehand. Live draw preview and selection resizing. Properties x/y/width/height/rotation/opacity/stroke/fill/font/text; layers with naming, visibility/lock, multi-select, group/ungroup, align, duplicate/delete and z-order. Local undo/redo, discard prompt on leaving dirty draft. Use design replaces a selected editable annotation or arms screenshot drag placement for a new design. Studio is available without a project for library work.

- [x] Failing tests for document validation, image/SVG import, portable packs, rendering and library snapshot isolation.
- [x] Implement design model, render/import/library and integrate schema 4 plus screenshot rendering/placement.
- [x] Implement studio drawing, inspector/layers and existing-annotation customisation.
- [x] UI tests covering draw/resize/layer edits, undo/redo, cancel/apply and project export; full suite, independent review, visual QA, docs, Windows build and smoke checks.
