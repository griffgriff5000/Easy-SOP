# SOP Capture Studio

A local Windows desktop application for recording a selected application's mouse interactions, editing illustrated procedure steps and exporting an A4 SOP PDF. Python 3.12+, PySide6, Pillow and ReportLab. No cloud service, API key or account is required.

## Workspace

The app uses a shared layout and light/dark theme across all screens. File, Edit and View menus provide the main commands and show your configured shortcuts.

- **Step editor:** thumbnails on the left, screenshot in the centre, and **Instructions / Annotation** tabs on the right. **Details** hides the inspector for more canvas space. Use **Actions** for duplication, ordering and grouping; **Screenshot** for image replacement/retake/PNG export; **Export** for PDF or Word. Relevant annotation properties appear for the active tool or selected item.
- **Annotation Studio:** drawing tools on the left, canvas in the centre, and **Properties / Layers / Library** tabs on the right. **Position and size** expands precise transforms. **Layers > Arrange** contains grouping and stacking. **File** contains artwork/pack import and design export. Saved designs and canvas dimensions are on **Library**.
- **Document:** Builder, Details, Procedure, Control and Branding categories. Review checklist links reveal the relevant category automatically.
- **Settings:** Capture, Annotations, Files and defaults, and Appearance categories. Shortcut and studio launch buttons are at the top.
- **Templates:** catalogue at left, Details and Appearance/Word styles at right. Use **New template** for custom/Word imports, **More** for Save as new/Delete, and **Apply template** or **Apply and preview**.
- Both canvases have **Fit / zoom** controls. Middle-drag pans a zoomed canvas; choosing Fit recentres it.

### Direct document editor

Open **Document > Builder > Edit document** to click and type directly in the company document, with captured SOP steps already inserted. This uses **installed desktop Microsoft Word** inside the centre pane, retaining Word's layout, styles, tables, images, headers and footers. Use Word's ribbon, right-click menus and keyboard shortcuts, or the Save/Undo/Redo/B/I/U controls above the document. Collapse Word's ribbon with Ctrl+F1 for more page space.

The editable document is a separate working copy. Changes save into the project every five seconds and before export, switching projects or closing. DOCX and PDF exports use this saved edited document. PDF export of a directly edited document requires desktop Word, including documents initially built with Standard SOP. Original company templates and library files remain unchanged.

**Source / preview** retains the Fields, Template text and Information controls, plus the read-only PDF preview. These source controls and captured steps do not overwrite a directly edited document. To incorporate later source changes, choose **Rebuild from captured steps** and confirm replacement of manual document edits. Project Undo can restore the previous saved version; use the editor's Undo/Redo buttons for native Word edits.

On PCs without desktop Word, the editor shows an unavailable message. Source controls, DOCX generation and Standard/custom PDF export remain available until a directly edited document is saved.

## Run on Windows

Use a **short virtual-environment path**. Qt's installation includes long filenames that can exceed Windows' path limit when the environment is inside a deeply nested OneDrive checkout.

```powershell
python -m venv "$env:USERPROFILE\.venvs\easy-sop"
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m pip install -e '.[dev]'
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" run_studio.py
```

For normal use, `pip install -e .` installs just runtime dependencies. The `dev` extra adds pytest, pypdf and PyInstaller. No administrator privileges are required. Use Windows 10 version 2004 or later, or Windows 11. Other operating systems can run domain/PDF tests but cannot perform live Windows capture.

The generated application is `dist\SOPCaptureStudio\SOPCaptureStudio.exe`. Distribute the **whole SOPCaptureStudio folder**, including `_internal`; the executable is not a standalone single file. Build and verification status are recorded in [docs/VALIDATION.md](docs/VALIDATION.md).

## Workflow

Open **Help → User guide** or press **F1** in the application for the built-in, offline guide. Topics cover the full workflow, annotations, saving/recovery, settings and troubleshooting. **Help → Keyboard shortcuts** lists shortcuts including your currently configured manual-capture key. The Help menu also provides Open logs and About.

1. Select **New SOP**, enter a title, choose a saved template and choose the parent directory. The app creates a fresh `SOP - <title>` folder; repeated titles get `(2)`, `(3)`, etc. Or open an existing `project.json`.
2. Refresh the application list, select the target window and use **Preview selection** to confirm its capture support.
3. Enable Windows Do Not Disturb manually if required. The application links to notification settings and does not change them.
4. Select **Start capture**, perform actions in the selected window and use the floating **Pause / Resume / Stop** controls. Default: left-click release followed by a 400 ms delay. **Ctrl+Shift+F8** takes a manual screenshot while the selected target is foreground. Shortcut conflicts are reported; change the shortcut in Settings.
5. Stop, edit step titles/descriptions/notes, drag steps to reorder and add manual steps as needed. Select annotation tools and drag on the screenshot. Click or drag with the marker tool to move its marker. Undo/redo also covers edits, deletion and image replacement.
6. Complete the Document page, preview the PDF and export. File dialogs confirm replacement of existing exports. Changes autosave locally; Ctrl+S flushes immediately.

To reuse a screenshot for another instruction, select its step and choose **Duplicate step**. The copy is inserted immediately afterward, with independent titles, markers and annotations. It shares the preserved original image, so editing either copy does not change the other.

To adjust an existing arrow, circle, highlight or redaction, choose **Edit annotations** from the tool list. Drag the shape's body to move it, or drag a square handle to resize it/change an arrow endpoint. Choose **Delete selected** to remove the selected shape. Moves, resizing, deletion and duplication all support Undo/Redo and autosave. Moving a redaction can reveal previously covered content; review the result before exporting.

**Live preview and styling:** choose a tool, set its colour and stroke thickness, then drag on the screenshot. You see the actual annotation before releasing to place it; press **Esc** to cancel. Select an existing annotation with **Edit annotations** to change its settings. With nothing selected, settings apply to new shapes. Stroke and text sizes are measured in original screenshot pixels; resize handles change the shape's overall dimensions.

New tools include **Straight line**, **Translucent highlight** with adjustable opacity, and **Text label**. For labels, enter the text, choose a font size and drag a box; text wraps within that box. Enlarge the box or reduce the font size if the label is clipped. Controls are enabled for the tools they affect. Numbered click-marker styling remains on Document; solid redactions always stay opaque black.

With **Arrow** selected, the **Arrow style** dropdown shows visual examples of solid, open-head and double-headed arrows. Choose an example before drawing, or select an existing arrow under Edit annotations to change its style.

Choose a window on Capture before using **Retake selected window** in the editor. Retaking captures one image and clears that step's old marker/annotations; Undo restores them. **Replace screenshot** imports an image and also clears prior annotations. Original image files are preserved in both cases.

Settings control delay, before/after-click timing, mouse buttons, global shortcut, optional initial frame, lossless PNG compression, annotation defaults, company/author/logo defaults, save location, orientation and theme. New-project defaults do not rewrite existing projects; the Document page changes an existing project's marker style and metadata.

## Template library and company documents

Open **Templates** to choose **Standard SOP**, a named custom layout, or an uploaded Word template. Select an entry and choose **Apply selected template to SOP**. Step editor shows the current template; PDF preview/export use that selection.

**Word uploads preserve company structure.** Upload a company `.docx` and give it a name. The app detects company styles, keeps covers, company tables, section layouts, headers, footers, logos and Word content controls, and removes recognised guidance/style demonstration sections. Lorem ipsum example prose is cleared; unknown content is retained. The SOP is inserted at an existing steps marker or where recognised guidance was removed, otherwise appended. Original uploads remain unchanged; no remote AI service is used.

Choose **Document > Fill template fields** for labelled company table values and **Next blank or placeholder**. Recognised title, reference, revision, prepared/checked/approved-by values use Document details; company-specific fields remain editable. Word content-control bindings repeat filled values on the cover and in tables. Complex/protected values offer **Edit on document**. Source values are applied when generating/rebuilding; existing direct edits are never replaced silently. Word refreshes contents and figure/table lists for preview/PDF and the embedded editor. DOCX marks these fields for refresh when opened in Word.

New structured preparation does not change existing library assets or already authored documents. Re-upload and apply a new version to recover structure lost by an earlier cleared template. Applying/rebuilding confirms replacement of direct edits. Fonts must be installed on the exporting PC.



**New custom template** starts from Standard SOP. Set a name, logo, company default, font preset, text sizes, colours, margins/orientation, cover, screenshot width and page-per-step preference. Header/footer text supports `{title}`, `{reference}`, `{version}` and `{company}`. Save changes adds it to the list; Save as new with a different name creates a variant. Existing SOP company text takes priority over the template default. Small margins still reserve header/footer space.

**Upload Word template** keeps a `.docx` document's styles, tables, page layout, logos, headers and footers. Map its detected paragraph styles to generated step titles, instructions and captions. Fonts need to be installed on the exporting PC; the app cannot infer intended style mappings or reproduce unavailable fonts exactly.

Prepare the document once using these placeholders:

| Field | Content |
| --- | --- |
| `{{title}}` or `{{sop_title}}` | SOP title |
| `{{company}}`, `{{reference}}`, `{{version}}`, `{{author}}` | Document information |
| `{{reviewer}}`, `{{approver}}`, `{{status}}`, `{{created}}`, `{{updated}}` | Review/status and date fields |
| `{{purpose}}`, `{{scope}}`, `{{prerequisites}}`, `{{revision_history}}` | Procedure context |
| `{{steps}}` | Repeated titles, annotated screenshots, instructions and notes |
| `{{logo}}` | Optional logo override |

Put `{{steps}}` **once, alone in a body paragraph outside tables/headers**. Put `{{logo}}` alone in its own paragraph. Other text placeholders work in ordinary paragraphs, tables and headers/footers, including placeholders Word splits across text runs. These marker rules apply to existing structured templates. New uploads remove recognised guidance while retaining company structures, and do not require a steps marker. No automatic mapping of arbitrary company forms is claimed. Macro documents, embedded active objects, externally linked assets and active/external Word fields are unsupported. Ordinary hyperlinks are retained. Imported originals are not modified.

**Save example Word template** creates a prepared file to edit. **Export Word** on Step editor saves DOCX. **Word-template PDF preview/export requires installed desktop Microsoft Word**; Standard/custom PDF export works independently. Both formats use flattened, current redactions. Imported Word documents keep their own page design; custom PDF appearance controls do not restyle them.

Templates belong to the application library and can be reused across multiple projects. New SOP offers the saved library entries before creating the project. Each project receives its own template copy, screenshots, edited document and exports in a separate folder. The library is stored in local user application data. Applying copies a snapshot and assets into the project's `Templates/` folder: later library edits/deletion do not change an existing SOP, and moving the complete folder retains its layout. Apply again to adopt a newer library version. Existing projects without a selection use Standard SOP. Reopen updated projects with the updated app. Deleted library entries may retain their old assets to protect other open editors.

Projects saved with a template use schema version 2, preventing older app versions from silently discarding the selected layout. Version-1 projects still open in this app; a previous valid project file is retained as backup when saved.

### Magnifier box

Choose **Magnifier** in Default annotations or the toolbar, then drag a rectangle over the detail to enlarge. The centre underneath the box is magnified inside it; the rest of the screenshot keeps its size and pixels. Set **Magnification** from 1.25x to 5x (default 2x), plus border colour/stroke. Preview appears while dragging; Esc cancels. Select/edit lets you move, resize or delete the lens, with Undo/Redo support.

The source screenshot file is unchanged. Magnification is rendered into annotated PNGs and generated Word/PDF screenshots. Redactions/blur are applied to sampled pixels first, so zooming does not copy hidden source content elsewhere. Other annotations remain independent. Projects containing a magnifier use schema 8; older project schemas still open in this version. Magnifiers stay in the screenshot editor because they depend on screenshot pixels, rather than reusable studio artwork.

### Quick annotation selection

In **Step editor > Annotation** on the right, the icon gallery shows **Default annotations**, then a divider and **Custom annotations**. Click a default tool or saved design, then drag on the screenshot to place it. Hover over icons for names; the selected icon is highlighted. Custom designs refresh when the panel opens, with its refresh button, and after the studio closes. Use Annotation Studio to create/edit and save designs. The toolbar selector stays synchronised with default gallery tools; gallery columns wrap to the panel width. Custom annotations belong to the app library and are available across all projects. To keep an annotation already drawn on a screenshot, select it and choose **Save selected to library**, then give it a name. Each placement embeds an independent copy; editing or deleting a library entry does not alter existing SOPs. Magnifiers, blur and redaction remain built-in screenshot tools.

## Privacy and capture limitations

- Only explicitly started sessions collect click events. Live screenshots use window-only Win32 rendering; **there is no desktop capture fallback**. Own-process windows are excluded from selection, and a target must retain its HWND and process ID.
- Focus is checked at trigger and screenshot time. Off-target actions are ignored. Captures may be skipped if focus changes, the target moves during rendering, becomes minimized, closes, is protected or does not support rendering. Recording can continue after the target becomes available again.
- No typed text, password events, clipboard contents or accessibility field values are recorded. **Visible information inside screenshots can still be sensitive**, including revealed passwords. Use solid redaction for information that must be unreadable. Blur is a visual aid and is not a secure substitute for opaque redaction.
- Redactions are flattened into exported images/PDFs. Original screenshots and editable projects remain unredacted: share the reviewed PDF rather than the entire project when originals must remain private.
- Before-click mode uses the most recent in-memory frame captured before mouse-down, at most one second old. Exact synchronous pre-click capture is not guaranteed. Frame age is stored in step metadata. Cache memory is discarded on pause/stop.
- Browser GPU content, popups that are separate windows, UAC/secure desktops, DRM/protected content and elevated applications may not capture correctly. Preview first. The app cannot reliably detect every stale or partially rendered screenshot. Do not use it to bypass application protection.
- Do Not Disturb is manual; no registry tweaks or simulated success. No notification setting is changed, so none needs restoration.
- Logging is local. There is no telemetry or automatic upload. If you choose a OneDrive, SharePoint-synced or other synced project directory, **that sync client may upload files** independently of this application. Choose a non-synced local directory where required by your organisation.

## Projects and recovery

```text
SOP - Procedure name/
  project.json
  project.backup.json
  Screenshots/     # immutable PNGs with stable unique filenames
  Annotated/       # optional flattened PNGs generated by the editor
  Exports/         # reviewed PDF documents
```

Step IDs and image paths stay stable across reordering. JSON is versioned and replaced atomically after writing a temporary sibling file; a previous valid JSON is retained as backup. Capture images are saved before the project references them. Missing images leave the remaining project editable and show a warning in exported output.

If opening fails and a backup exists, the app offers recovery. An exclusive `.project.lock` prevents two normal app instances writing simultaneously. After a crash, remove a stale lock only after confirming no other instance is editing that folder; the app offers this explicitly. Do not edit an active project in a second application. Unreferenced original images are retained to avoid accidental loss and may consume additional disk space.

Application settings and rolling logs use the current Windows user profile. Select **Open logs** in the sidebar. Closing during capture initiates Stop; close again after capture has finished. Failed saves keep the window open for recovery.

## Demonstration

Open `demo\Permit Management\project.json`. Its fictional screenshots contain no real user information. Regenerate a missing demo with:

```powershell
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/create_demo.py
```

## Tests and packaging

```powershell
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m pytest -q
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/smoke_windows.py
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/smoke_windows.py --renderer-executable dist/SOPCaptureStudio/SOPCaptureStudio.exe
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/visual_check.py
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/verify_templates.py
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" -m PyInstaller --noconfirm SOPCaptureStudio.spec
.\dist\SOPCaptureStudio\SOPCaptureStudio.exe --smoke-test
& "$env:USERPROFILE\.venvs\easy-sop\Scripts\python.exe" scripts/smoke_template_bundle.py dist/SOPCaptureStudio/SOPCaptureStudio.exe
```

The native smoke script creates a separate, synthetic target and checks inventory, window rendering, hook/hotkey registration and release. It does not inject input or inspect existing applications. Focus restrictions may prevent its manual-session check; it reports this rather than claiming success. `visual_check.py` saves application screenshots and PDF page renders in `.superpowers/visual` for inspection. The executable is unsigned; corporate deployment/code signing is outside this local build.

`requirements-lock.txt` records the environment used for validation. Add `-c requirements-lock.txt` to the install command to reproduce those dependency versions.

## Source layout

- `models.py`, `storage.py`, `geometry.py`: project schema, persistence and coordinate transforms.
- `windows.py`: Win32 window inventory, isolated rendering process, low-level mouse hook and global hotkey.
- `capture.py`: bounded capture queue, focus checks, delay and session lifecycle.
- `imaging.py`, `pdf_export.py`: shared flattened annotations and PDF layout.
- `templates.py`, `word_export.py`, `document_export.py`: template library, portable snapshots, Word generation and export dispatch.
- `ui/`: Qt capture dashboard, step editor, annotation canvas, document fields and settings.
- `app.py`, `run_studio.py`: startup, DPI setup, rotating logs and multiprocessing-safe entry points.

AI/OCR, SharePoint publishing, approval workflows and centrally shared template libraries are future extensions. See the approved [design](docs/superpowers/specs/2026-10-23-sop-capture-studio-design.md) for the architectural boundaries.

## Third-party licences

The project uses the repository's MIT licence. Dependencies retain their own licences, including PySide6/Qt (LGPL/GPL/commercial terms), Pillow and ReportLab. The bundled PDF font is Bitstream Vera distributed with ReportLab; the packaging configuration includes ReportLab's fonts and associated licence files. Preserve the dependency notices and assess your organisation's distribution obligations before corporate rollout. Nothing in the app requires an OpenAI account or service.

### Callouts, sections and review

- Choose **Text callout**, type a label, then drag from its target to the label position. Use **Edit annotations** to move either end; colour, stroke and text size are adjustable.
- Enter a **Section / stage** on a step or use **Group steps...** for a range. **Rename section...** updates all matching steps. PDF and Word include section headings with continuous step numbering.
- **Review SOP** flags missing document details, instructions and screenshots. Select an item to fix it. Export checks the draft and offers **Export anyway** for intentional omissions.

### Custom shortcuts and action sequences

Open **Settings > Customise shortcuts** (also on the Settings page). Search for an action, click its shortcut box and press a key combination. Clear the box to disable a shortcut. Choose **Apply** to save and activate changes.

The **Action sequences** tab lets you create a named sequence, add editor actions, reorder them with Up/Down and assign one shortcut. For example: **Add step**, then **Tool: Text callout**. Sequences stop when an action is unavailable. They support editor actions; dialogs, recording controls and asynchronous exports are available as individual shortcuts. Shortcuts operate within SOP Capture Studio. The global manual-capture shortcut remains in capture settings.

Import/export JSON profiles to share a setup. Imports are validated and staged until Apply. Duplicate assignments and manual-capture conflicts are rejected. Restore defaults resets bindings and removes sequences. Help displays the current assigned keys.

### Annotation Studio

Open **Annotation Studio...** in the Step editor, or **Settings > Annotation Studio...** to work on your library without an SOP.

- Draw rectangles, ellipses, triangles, diamonds, arrows, lines, text and freehand strokes. The checkerboard shows transparency. Draw a shape to see a live preview, then release to add it; Esc cancels the gesture.
- Select elements on the canvas or in the layers list. Ctrl selects multiple layers. Drag to move; use the white corner handle for single-layer resizing, or enter exact position and size. Set fill/outline colours, stroke thickness, arrow heads, opacity, rotation, font family, bold/italic and text. Fonts use standard Windows families or the bundled Vera preset; unavailable families fall back to Vera.
- Duplicate, delete, align, reorder, group/ungroup, hide or lock layers. Undo/Redo operates within the studio. Locked elements keep their geometry until unlocked.
- Import PNG, JPEG, WebP or static SVG artwork. Artwork is embedded as an image layer, with resizing, rotation and transparency controls. SVG artwork is rasterized on import; its internal vector paths are not separately editable. External SVG resources, active content and unsupported SVG elements are rejected; use a standalone PNG for those files.
- Name and save designs in the local library; Save as new creates a separate entry. Export/import `.sopannotation` packs to share editable studio layers with their embedded artwork. Export transparent PNG for other applications.
- Choose **Use design on step**, then drag on the screenshot to preview its placement and size. To customise an existing shape or custom design, select it with **Edit annotations** and reopen the studio. Apply replaces that annotation; closing/discarding keeps the SOP unchanged. Redaction and blur masks stay in the screenshot editor and are applied over custom artwork in exports.

The library supports canvases up to 2048?2048 and up to 100 layers per design. Placed designs are embedded snapshots: moving original artwork or changing/deleting library entries does not change saved SOPs. Projects using custom designs require this version of SOP Capture Studio (schema 4).
