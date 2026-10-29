# Magnifier annotation

User chose magnification inside the drawn box. Add a rectangular lens to the default annotation gallery and toolbar; default 2x, adjustable 1.25–5x, with existing live preview, move/resize/delete/undo. Magnify screenshot pixels centred under the box; retain screenshot dimensions and pixels outside the box. Source files remain immutable. Other annotation layers remain independent.

The renderer samples a redaction-masked copy of the original screenshot, never an unmasked secret or a previously magnified layer. Existing masks still flatten last. Shared rendering covers editor preview, PNG and Word/PDF exports. A zoom field is stored only for magnifiers; schema 8 prevents older apps silently losing the lens. Older project schemas remain readable.

- [x] Failing tests for centred magnification, outside/source immutability, order-independent redaction safety, persistence/validation and interactive placement/editing.
- [x] Model/renderer/canvas/gallery/inspector/shortcut integration.
- [x] Regression suite, visual QA and independent review; update help/docs.

Verified: 182 tests passed (exit 0), visual editor/source immutability check passed, independent review had no important findings. Windows build/startup and frozen DOCX/PDF/native editor/template preparation checks passed, including magnifier rendering.
