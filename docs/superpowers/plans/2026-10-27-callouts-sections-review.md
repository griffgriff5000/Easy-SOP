# Callouts, sections and review checklist

The user selected three features and explicitly excluded emulator work.

## Design

- Text callout: enter text, drag from the target control to the label position, preview before release. Draw a readable white-backed label with coloured outline/text and a pointer. Existing Edit annotations can move the label or pointer endpoint independently; colour, stroke and font-size controls apply. Exports use the shared renderer and redactions remain last.
- Sections: store an optional section name per step. Choose/type it in the editor or assign a named section to a contiguous range using Group steps. Rename a section across its members. Display section starts in the step list; output section headings when the section changes, keeping overall step numbering. Reordering, duplication, undo and project storage retain membership.
- Review: reusable advisory checks for missing document details, no steps, placeholder titles, missing instructions/screenshots, unreadable image files and missing template assets. A Review SOP dialog links findings to their step/document fields. Interactive PDF/Word export shows issues before the save dialog and lets the user fix them or explicitly export anyway. Preview and programmatic exports remain available for drafts.

## Implementation tasks

- [x] Add failing tests for shared callout rendering/preview/editing and versioned persistence.
- [x] Add callout layout/rendering and editor tool; preserve redaction precedence and cancel/undo behavior.
- [x] Add section model validation, grouping editor controls, undo and section headings in PDF/Word.
- [x] Add review rules, navigable dialog and export review gate; verify no project mutation and no false missing-company warning with a template default.
- [x] Run full suite, visually verify UI and PDF/Word output, independent source review, update help/docs and rebuild/test the executable.

Keep existing user edits intact. Projects using callouts or sections move to schema 3; older schema-1/2 projects load with empty section membership.
