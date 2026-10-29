# Project home and reusable libraries

User selected the proposed four-part home: Recent projects, one-window New project, template preview/management, and annotation browsing/management. Implement on main as explicitly requested earlier, with no feature branch.

Architecture: preserve existing page indices 0–4 and append Home (5) and Annotation library (6), while displaying Home first in navigation. Add a local bounded MRU registry using atomic JSON, updated only after successful open/create; missing entries remain removable without deleting projects. Replace sequential New SOP prompts with a validated dialog containing name, template, parent folder and exact proposed folder preview. Reserve new folders atomically as before. Keep library snapshots and per-project data unchanged.

Template preview uses a temporary sample project and selected library snapshot; it never applies to the active SOP. Annotation library has list/previews, studio create/edit, duplicate, import artwork/pack, export and confirmed library-entry deletion; existing project placements remain independent. Library use on an active screenshot returns to Step editor.

Files: recent_projects.py; ui/home_page.py; ui/new_project_dialog.py; ui/annotation_library_page.py; main_window.py integration; templates_page.py standalone preview callback; shortcuts.py page navigation; app.py CLI project routing. Test Qt paths use QStandardPaths test mode so recent history does not pollute real user data.

- [x] Tests for MRU order/deduplication/missing paths, unified dialog cancellation/folders, navigation and independent library actions.
- [x] Implement MRU, Home and unified dialog; route create/open/recent through existing project locking/recovery lifecycle.
- [x] Add annotation library and independent template preview.
- [x] Full tests (193 passed), visual QA at multiple sizes/themes, independent review, Windows build/startup and documentation.
- Integration: commit and push directly to main, as requested by the user.
