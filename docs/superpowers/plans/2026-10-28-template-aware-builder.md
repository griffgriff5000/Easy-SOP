# Template-aware document builder

Show the applied template and generated SOP together inside the Builder. The centre is the actual exported document rendered as paginated PDF; a right inspector holds title/company-information and original Word-template text controls. The preview is read-only; edits are made alongside it and Refresh updates the actual pages, preserving the original Word layout.

Original Word paragraphs and table-cell text can be edited via stable part/index records. Store per-project text patches with a source file hash, validate that they match the selected template and apply them to an export copy before metadata filling. Preserve unaffected runs, paragraph properties, tables, images, headers/footer styles. Paragraphs containing dynamic fields, pictures or complex structures stay read-only. Never write changes into the imported source/library template. New template application clears incompatible patches with project Undo support.

Project schema 6 adds template_text_edits. The inline preview uses a separate snapshot worker so typing stays available. It is generated on entering Builder; subsequent edits mark it stale, and Refresh explicitly rebuilds it. Discard stale results after project/template changes. Closing waits for preview worker completion; document/buffer resources are parent-owned and released.

- [x] Tests for formatted text patches, table cells, original immutability, source mismatch, persistence and stale preview handling.
- [x] Implement source-preserving template edits and schema.
- [x] Embed actual PDF preview plus compact inspector in Builder and load original template text for editing.
- [x] Full tests, review, visual/export QA, docs and rebuilt package.
