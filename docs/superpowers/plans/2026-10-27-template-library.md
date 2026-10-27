# Template library implementation plan

> Use superpowers:executing-plans for inline implementation and an independent final review.

Goal: multiple reusable SOP templates, user Word uploads, and named custom layouts based on Standard SOP.

Architecture: a local template library owns immutable template assets and named profiles. Applying a profile copies a snapshot into the project, keeping it portable and independent of subsequent library edits. The existing ReportLab renderer gains configurable appearance; a separate Word renderer fills approved placeholders, inserts procedural content using mapped Word styles, and uses an independent installed Word instance for PDF conversion.

User-approved requirements: template selection, multiple imports, preserve company styles, custom logo/text/style parameters and save under a name. No company reference document was supplied; ship a prepared example and document the placeholder contract. Word content without a standalone {{steps}} anchor gets generated procedure content appended, with that behavior disclosed before import. This does not claim automatic understanding of arbitrary company forms.

## Global constraints

- Local processing, original screenshots preserved, redactions flattened in every export.
- Standard and custom PDF export must work without Microsoft Word. Word-template PDF export requires installed desktop Word; DOCX export remains available without Word.
- Read old projects with an empty template selection; never silently overwrite imported source files, named profiles or exports.
- Validate archive sizes, reject macro documents/unsafe external relationships, confine project asset paths and validate custom appearance parameters.
- Preserve user's .vscode configuration; implementation remains on feat/sop-capture-studio.

## Review focus

- Missing library assets and malicious project paths must fail clearly rather than read unrelated files.
- Template edits/removal must not alter an already configured project.
- Long text, portrait screenshots and imported table/header formatting must survive export without clipping.
- Preview, PDF and DOCX must use current redactions and the selected profile.
- Cancelling selection/import or failed saves must not leave a different active template or lose project edits.

## Tasks

1. Library/domain/storage: add template settings validation, import inspection, immutable assets, profile CRUD and project snapshots. Test round trips, duplicates, missing assets, traversal, old projects and snapshots unaffected by edits.
2. Custom PDF: add fonts/sizes/colours/margins, screenshot sizing, page-per-step, header/footer and optional profile logo/company. Test changed page geometry, text, pagination and defaults.
3. Word rendering: preserve supplied document, replace known placeholders across runs, insert steps at standalone body {{steps}} or append, map named paragraph styles, use annotated images. Add DOCX export and isolated Word conversion with cleanup. Test styles, split-run placeholders, images/redactions, missing tokens/assets and rejection of unsafe archives.
4. Qt integration: Templates page with library list, Standard/custom/Word choices, name/parameters/logo/style mappings, upload/save/update/delete/apply, project selection summary and preview. Wire all exports through the selected template and add DOCX export. Test save/import/apply/reopen/undo and export dispatch.
5. Verify UI and representative custom/Word PDFs visually, update help/README/dependencies, run suite, independent review and rebuild executable.

Progress is recorded in docs/IMPLEMENTATION.md as tasks finish. No automatic emulator integration is part of this change.
