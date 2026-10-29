# Basic company-information document builder

Goal: a small local editor for title and company-required information, followed automatically by captured SOP steps. No paid component or external editing engine.

Design: the Document page opens on a Builder tab with the existing title field and a basic rich-text company-information editor (headings, bold/italic/underline, lists and simple tables). The insertion boundary below it is fixed: procedure steps are generated after this content, so users do not edit or accidentally delete captured steps inside the front matter. Preview uses the existing actual PDF export. Document metadata remains in Details/Procedure/Control/Branding tabs.

Architecture: Project.company_information stores bounded Qt HTML, default empty; projects using it upgrade monotonically to schema 5. company_information.py parses a restricted text/table subset and emits native Word paragraphs/tables and ReportLab flowables. Only newly generated company information is reconstructed; original company Word template content remains separate and is not loaded into a lossy rich-text round trip. Word export inserts the section immediately before generated steps at the existing anchor, or after original company content when appending. Standard PDF inserts it before Procedure. No external images/resources in the basic text editor.

- [x] Failing tests for parsing/style/order, template preservation and monotonic persistence.
- [x] Implement model/renderers and shared company-information parser.
- [x] Add basic editor and title to Builder tab, autosave/undo/preview and correct review routing.
- [x] Full suite, independent review, visual QA, README/help, Windows package and actual export smoke checks.
