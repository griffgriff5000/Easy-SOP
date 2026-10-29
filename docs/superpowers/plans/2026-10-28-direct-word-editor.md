# Direct centre document editing

Goal: click and type directly on the company document/SOP in the centre using installed desktop Microsoft Word. A synthetic Qt foreign-window proof succeeded on this PC with an isolated Word process.

Architecture: generate the complete SOP once into a private working DOCX, open it in a dedicated Word COM instance and host that instance's window in a Qt native container. Verify ownership by PID before embedding; never attach to user Word sessions. Save immutable DOCX snapshots into the project, with a schema 7 document_file/document_source_key. Once a saved edited document exists it is authoritative for Word/PDF exports; source fields/steps never silently regenerate it. Rebuild requires confirmation and creates a new snapshot, preserving prior versions for project Undo.

UI: Builder defaults to Edit document. Installed Word provides actual document pages and direct keyboard/mouse editing, with Save/Undo/Redo/basic formatting controls. Existing preview/source controls remain available on an explicit Source / preview tab. Native editor autosaves to project every five seconds and before export/project changes/close. Word's own keyboard Undo/Save work in the child window. Errors leave the working document open; closing never discards unsaved work. On systems without desktop Word, retain explicit preview mode with a clear editor-unavailable message.

- [x] Tests for authoritative document persistence/export, safe paths, source fingerprint, and rebuild generation.
- [x] Implement saved-document model/dispatch and owned Word session/container.
- [x] Integrate editor mode, save/rebuild/close lifecycle and source-change notices.
- [x] Unit suite, independent review, actual embedded Word edit/save/reopen/Word/PDF validation, docs and package.
