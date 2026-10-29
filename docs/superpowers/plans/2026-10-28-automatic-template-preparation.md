# Automatic template preparation implementation plan

Goal: uploading a company DOCX automatically reads its Word style definitions, clears its example body, retains company page furniture and builds the SOP using those styles, without a cleanup questionnaire.

Architecture: a focused word_template module analyses styles and prepares a separate DOCX. TemplatesPage.import_path opts into preparation; TemplateLibrary.save supports it explicitly so existing profiles and structured integration callers remain unchanged. Prepared assets retain styles/numbering/header/footer relationships and the first section page layout, replace body content with generated document fields/steps markers, and record the prepared flag. Updates save that flag. Word export uses learned title/step/body styles, avoids duplicated manual numbering when Word styles already number headings, and fills recognised header placeholders. Existing authored documents remain authoritative until explicit rebuild.

Ruling: clear the whole main body as explicitly requested, including example images/tables and content controls; preserve header/footer branding and their content. For multi-section bodies retain the first section as the reusable page layout; later section breaks belong to cleared content. This is deterministic style inspection, with no remote AI or uploaded company data. Existing library entries are not migrated silently.

- [x] Add failing tests for automatic UI import, corporate styles, body removal, numbering, header/footer/logo/layout preservation, updates and original immutability.
- [x] Implement preparation module, library opt-in and automatic upload UI.
- [x] Integrate generated styles and header placeholders; preserve legacy marker-based templates and direct editor.
- [x] Test actual supplied MEH DOCX, visually inspect real Word output, review, run full suite, build and validate package; document workflow.

Validation: full suite 164 passed with process exit 0; actual uploaded MEH DOCX generated and visually inspected; frozen startup, preparation, native Word editing and all export checks passed. Independent review reported no important defects.
