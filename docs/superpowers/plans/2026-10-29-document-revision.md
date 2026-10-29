# Document Revision Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task with one final independent review.

**Goal:** Reviewed local transfer of existing DOCX/PDF procedures into a newer DOCX template.

**Architecture:** Separate revision workspace and persistence, source extraction and loss-aware DOCX placement, local suggestion service, Qt review page and existing Word editor. Append navigation index 7, leaving SOP projects unchanged.

**Tech Stack:** Python, PySide6/Qt PDF, python-docx/lxml, pdfplumber, optional loopback Ollama HTTP.

**Spec:** docs/superpowers/specs/2026-10-29-document-revision.md

## Global constraints
- Work on main and push directly as already requested.
- Originals immutable; each revision owns copies; no unapproved content in generated output.
- Suggestions and external model responses are data, never commands or approvals.
- Template cover, tables, headers, footers and sections remain intact.

## Review focus
- Unsupported charts, equations, notes, tracked changes and section properties: warn rather than silently discard.
- PDF scans/tables/reading order: retain page evidence and uncertainty.
- Duplicate placements, edited table cells and undo: persist exact approved state.
- Reopen, failed saves and Word native edits: preserve working copies and never rebuild silently.
- Local inference: reject nonlocal/cloud models, disable proxies/redirects and validate destination IDs.

### Task 1: Import and revision state
- [x] Write failing tests for ordered DOCX/table/image imports, PDF tables/scans, immutable snapshots, approval state and undo/reopen.
- [x] Implement revision_import.py and revisions.py with atomic state and destination matching.
- [x] Run focused tests.

### Task 2: Transfer and local assistant
- [x] Write failing tests for template retention, table editing, image relationships, revision metadata, ordered approved-only export and invalid AI proposals.
- [x] Implement revision_export.py and revision_assistant.py; use local structural rules by default and optional Ollama proposals.
- [x] Run focused tests and inspect a rendered revision.

### Task 3: Review UI and integration
- [x] Write failing tests for approve/exclude/edit/move, workspace reopen and guarded final editor lifecycle.
- [x] Implement revision_page.py: source list/page preview, destination/placement list and content editor, local assistant and final Word editor.
- [x] Integrate sidebar/shortcuts/help; document optional model/scanned-PDF limits.
- [x] Full suite (207 passed), visual QA, independent review, build/startup/export verification.
- Integration: commit and push directly to main, as requested.

## Ledger
Executing inline. No feature branch per user preference. No model download required; CPU structural assistance is usable immediately. Scanned PDFs retain rendered artwork and explicit manual transcription status instead of pretending OCR succeeded.

Review fixes: retain equations and block unsupported note/comment/track-change dependencies, reject active Word fields, preserve list numbering and template table styles, avoid inventing SOP reference metadata, preserve authored bytes while accounting for manual transfers, lock active revision workspaces. Order has its own tab so the table editor stays usable at minimum window width. Live model inference was not tested because no local model service is running. Frozen smoke verification covers real PDF dependencies and native Word revision editing/export.
