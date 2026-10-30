"""Offline, topic-based help packaged with the application."""
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QTextBrowser, QPushButton, QLabel


TOPICS = {
    "Application updates": """<h1>Install a newer app version</h1>
<p>Open <b>Help &gt; Check for updates</b>. Checks use the public GitHub stable release and send no document/project content. Download the offered Windows update; progress and cancellation are available. After verification, choose <b>Install and restart</b> and confirm.</p>
<p>Finish recording or document/export jobs first. Normal Word/project save and close checks run before installation; if closing fails, replacement is cancelled. The complete app folder is replaced by a separate helper after the old process exits. The preceding folder is retained; failed new startup is rolled back when the new process has exited. No Windows elevation or policy bypass is used.</p>
<p>Projects, templates, annotations and preferences stay separate. Personal files inside the app folder prevent automatic replacement. If a new app remains running without confirming, its files are not overwritten; a recovery message identifies the retained previous folder. Version 0.1.0 users install the updater-enabled ZIP manually once. Source runs can check/download but cannot replace the checkout.</p>""",
    "Custom workspaces": """<h1>Arrange the app around your work</h1>
<p>Each screen has its own layout. Drag panel title bars to dock at any edge, resize boundaries, double-click a title to float, or close a panel to hide it. Floating panels are hidden on inactive screens and can be moved to another monitor.</p>
<p><b>Workspace &gt; Customise this workspace</b> selects visible panels and toolbar actions. Drag checked actions into order, choose icons/text, theme, text size and compact/comfortable spacing, then Apply. Lock layout prevents accidental docking changes. The menu-bar Customise workspace control remains available even when all panels/toolbars are hidden.</p>
<p><b>Save named</b> stores a reusable layout; <b>Load named</b> restores it. <b>Copy to…</b> targets selected screens, with Select all for the whole app. Shared roles and settings copy; destination-specific tools stay available. Document content, SOP steps and review decisions are never copied by a layout.</p>
<p><b>Show / hide panels</b> reopens panels. Reset this screen and Reset all screens restore defaults without deleting named layouts or documents. Preferences save locally and separately from projects. Customise shortcuts opens the existing action/shortcut editor.</p>""",
    "Revising procedures": """<h1>Move an old procedure into a new Word template</h1>
<p>Open <b>Revise document</b> in the sidebar. Choose <b>New revision</b>, an old Word .docx or PDF, a new Word .docx template, an unused workspace folder and a new revision label. Saved Word templates are available in the dialog. Original documents are preserved; <b>Open revision</b> resumes revision.json.</p>
<p>Select an old element on the left. Choose its destination on the right, edit text or table cells, then <b>Approve placement</b>. <b>Suggest</b> proposes a match without approval. <b>Order</b> reorders approved content; exclusions require a reason. Undo/redo restores transfer decisions. The template's existing cover, tables, headers, footers and sections stay intact.</p>
<p><b>Save details</b> records the title, revision and change summary. <b>Preview</b> shows structure; <b>Original pages</b> shows PDF pages or renders Word using installed desktop Word. The <b>Word</b> tab provides final page editing with installed desktop Word. Manual edits remain authoritative; returning to placements confirms rebuilding and keeps a backup. <b>Export Word + report</b> saves a separate DOCX and transfer report, and warns about unresolved elements.</p>
<p>PDF reading order and extracted tables need visual checking. Scans offer page artwork or manual transcription; automatic OCR is not bundled. Equations, notes, comments, tracked changes and unsupported objects are flagged for manual transfer in Word. New required company table cells and complex table restructuring can be completed there.</p>
<p>Offline structural assistance works immediately. Optional <b>Find local AI</b> connects to an independently installed Ollama service and installed local model on this PC. No model is downloaded automatically. Suggestions and proposed text still require approval.</p>""",
    "Document builder": """<h1>Edit directly on the document</h1>
<p>Open <b>Document &gt; Builder &gt; Edit document</b>, then click and type on the pages. Installed desktop Microsoft Word provides the editor inside the centre pane. You can change text, remove template instructions, edit tables and images, and use Word styles and formatting.</p>
<p>Use Word's ribbon, right-click menus and shortcuts, or the Save/Undo/Redo/B/I/U controls. Ctrl+F1 collapses the ribbon for more page space. Changes save into the project every five seconds, before exports, switching projects and closing. Word and PDF exports retain your direct edits. PDF export of edited documents requires desktop Word.</p>
<p><b>Source / preview</b> contains the Fields, Template text and Information controls and a read-only PDF preview. Once you edit the document directly, source changes and new captured steps do not overwrite it. Choose <b>Rebuild from captured steps</b> to regenerate from the current template and source. This replaces manual document edits after confirmation; project Undo can restore the previous version.</p>
<p>The original template stays unchanged. If saving fails, keep the app open and retry; the working-copy path is shown in the editor. Without desktop Word you can still use source controls, DOCX generation and Standard/custom PDF export for documents without direct edits.</p>""",
    "Workspace layout": """<h1>A consistent workspace</h1>
<p>Use the sidebar to switch pages. File, Edit and View menus contain the main commands with your configured shortcuts. Secondary actions are in labelled menus beside the area they affect.</p>
<ul><li><b>Step editor:</b> steps at left, screenshot in the centre, Instructions and Annotation tabs at right. Details hides that inspector. Actions contains duplication, ordering and grouping. Screenshot contains replace/retake/PNG export. Export offers PDF and Word.</li>
<li><b>Annotation Studio:</b> drawing rail at left; Properties, Layers and Library tabs at right. Expand Position and size for exact transforms. Layers &gt; Arrange contains grouping/stacking; File contains import/export; Library contains saved designs and canvas dimensions.</li>
<li><b>Document:</b> Details, Procedure, Control and Branding tabs. Review links open the correct tab.</li>
<li><b>Settings:</b> Capture, Annotations, Files and defaults, and Appearance tabs.</li>
<li><b>Templates:</b> choose a catalogue entry, then edit Details and Appearance/Word styles. New template contains creation and import; More contains Save as new and Delete.</li></ul>
<p>Both canvases have Fit and zoom controls. Middle-drag pans while zoomed; choosing Fit recentres the view. The same spacing, controls and light/dark colours are used throughout.</p>""",

    "Annotation Studio": """<h1>Draw and reuse your own annotations</h1>
<p>Open <b>Annotation Studio...</b> in the Step editor or the Settings menu. Choose a drawing tool, then drag on the checkerboard. Use Freehand to draw a stroke. The preview becomes a new layer when you release; Esc cancels the current gesture.</p>
<p>Select and drag elements to move them. Use the white corner handle to resize one layer, or enter exact X, Y, width, height and rotation. Properties control fill, outline, opacity, font, text and arrow heads. Standard Windows font families fall back to bundled Vera if unavailable.</p>
<p>Ctrl selects multiple layers. Group combines selection for movement; Ungroup separates it. Forward/Backward controls stacking. Align, Duplicate, Delete, Visible and Locked work from the layers panel and properties. Undo/Redo changes the studio draft.</p>
<p><b>Import artwork</b> accepts PNG, JPEG, WebP and static SVG. Imported artwork is an image layer; SVG paths are flattened on import. External resources and active SVG content are unsupported. Use PNG for unsupported SVGs.</p>
<p>Name and <b>Save</b> the design to your local library; <b>Save as new</b> makes a separate entry. Export/import editable <b>.sopannotation</b> packs to share studio layers and embedded artwork. Export transparent PNG for use elsewhere. Designs support up to 100 layers on a 2048 by 2048 canvas.</p>
<p><b>Use design on step</b> arms drag placement on the screenshot. Select an existing annotation using Edit annotations and reopen the studio to customise it; Use design replaces it. Closing or discarding leaves the SOP unchanged. Placed designs are independent copies, so library edits or deletion do not alter saved SOPs. Saved designs are available across every project. You can also select an annotation on a screenshot and choose <b>Save selected to library</b> to name a reusable copy; each later placement remains independent. Redactions and blur remain in the screenshot editor and cover custom designs on export.</p>""",

    "Callouts, sections and review": """<h1>Make longer procedures easier to follow</h1>
<p><b>Text callout:</b> select Text callout in the annotation dropdown, enter the label, then drag from the button or field to the label position. Adjust colour, stroke and text size. Use Edit annotations to move the target handle or drag the label independently. A live preview appears while dragging.</p>
<p><b>Sections:</b> enter a section name below a step title, or choose Group steps and select a first and last step. Rename section changes every step using that name. Blank names remove grouping. Section headings appear in the list and PDF/Word exports; step numbering stays continuous. New steps inherit the selected section.</p>
<p><b>Review SOP:</b> check missing document details, instructions and screenshots. Select an item and choose Fix selected item to return to its editor. PDF and Word export show the checklist when issues exist; Export anyway allows intentional omissions in drafts.</p>""",

    "Getting started": """<h1>Create your first SOP</h1>
<p>SOP Capture Studio turns screenshots of a process into an editable procedure and a PDF.</p>
<ol>
<li>On <b>Home</b>, choose <b>New project</b> and enter its name, saved template and parent folder in one window. Check the proposed folder, then choose Create project. Each project gets a fresh subfolder; repeated titles get numbered folders. Reopen work from Recent projects or browse to project.json. Removing a recent shortcut keeps the project files.</li>
<li>Choose <b>Refresh windows</b>, select the application you want to document and use <b>Preview selection</b> to check the screenshot.</li>
<li>Choose <b>Start capture</b>. The main window minimises and floating capture controls appear.</li>
<li>Perform the process in your selected application. Clicks create steps automatically.</li>
<li>Choose <b>Stop</b> on the floating controls. Add instructions in the <b>Step editor</b>.</li>
<li>Complete the <b>Document</b> details, choose <b>Preview</b>, then <b>Export &gt; Export PDF</b>.</li>
</ol>
<p>Your work is saved automatically. Use <b>Open SOP</b> to continue a saved project later.</p>
<p>Select a topic on the left for more detail. This guide works without an internet connection.</p>
""",
    "Recording": """
<h1>Record a process</h1>
<p>First create or open a project, then select a target on the Capture page. Your own SOP Capture Studio windows cannot be selected.</p>
<p><b>Start capture</b> records clicks only in the selected window while it has focus. By default, a screenshot is taken 400 milliseconds after a left-click is released, allowing the interface to update.</p>
<ul>
<li><b>Pause</b> suspends recording; clicks during the pause are ignored. <b>Resume</b> continues.</li>
<li><b>Stop</b> finishes pending screenshots, saves the results and opens the editor.</li>
<li>For a screen that does not need a click, focus the selected application and press <b>{manual_shortcut}</b> for a manual screenshot. It has no click marker.</li>
</ul>
<p>Settings controls the delay, mouse buttons, manual shortcut and optional first screenshot. Before-click mode uses a recent frame, not a guaranteed exact instant before the click.</p>
<p>Enable Windows Do Not Disturb manually if needed; the app links to notification settings but does not change them. Return focus to your target after using another window.</p>
""",
    "Editing steps": """
<h1>Arrange and explain the steps</h1>
<p>Select a thumbnail to edit its <b>title</b>, <b>description</b> and optional <b>notes or warnings</b>.</p>
<ul>
<li><b>Add step</b> inserts a blank step below the selected step. If nothing is selected, it appends at the end.</li>
<li><b>Duplicate step</b> reuses the screenshot in a new step immediately below the original. Its text and annotations can be edited independently.</li>
<li>Drag thumbnails, or use <b>Move up</b> and <b>Move down</b>, to reorder steps. Numbering updates automatically.</li>
<li><b>Delete</b> removes the selected step. <b>Undo</b> restores it; <b>Redo</b> reapplies a change.</li>
<li><b>Replace screenshot</b> imports an image. <b>Retake selected window</b> captures the target selected on Capture.</li>
</ul>
<p>Replacing or retaking clears the step's old marker and annotations. Undo can restore them. Original image files are preserved.</p>
<p>A manual step can contain instructions without a screenshot. Attach one later using Replace screenshot.</p>
""",
    "Annotations": """
<h1>Annotate a screenshot</h1>
<p>Choose an icon under <b>Default annotations</b> or <b>Custom annotations</b> in the right-hand Annotation panel, or use the toolbar selector. Hover for names. Drag to see a <b>live preview</b>, then release to place it. Press <b>Esc</b> while dragging to cancel.</p>
<ul>
<li><b>Arrow:</b> the <b>Arrow style</b> dropdown shows pictures of solid, open-head and double-headed arrows.</li>
<li><b>Straight line</b>, <b>Circle / ellipse</b> and <b>Outline box</b> mark areas or connections.</li>
<li><b>Translucent highlight:</b> draw a coloured area and adjust Highlight opacity.</li>
<li><b>Text label:</b> enter your label, choose a text size and drag a box. Text wraps inside it; enlarge the box or reduce the font if text is clipped.</li>
<li><b>Solid redaction</b> covers an area with opaque black. <b>Blur</b> softens an area; use solid redaction for information that must be unreadable.</li>
</ul>
<p><b>Magnifier:</b> choose its icon under Default annotations and draw a box. The screenshot under its centre is enlarged inside the box, leaving the rest unchanged. Adjust Magnification (1.25x?5x), border colour and stroke. Select/edit moves or resizes it; Esc cancels a preview. The original file is unchanged, and generated PNG/Word/PDF screenshots include the lens. Source redactions are preserved when sampling.</p>
<p>Set <b>Colour</b> and <b>Stroke</b> thickness before drawing. Sizes are measured in original screenshot pixels, so appearance depends on the preview scale.</p>
<h2>Change an existing annotation</h2>
<p>Choose <b>Select / edit</b>, then click a shape. Drag its body to move it or drag a square handle to resize it/change an arrow endpoint. The toolbar edits the selected shape. With no shape selected, settings apply to new shapes.</p>
<p><b>Delete selected</b> removes the selected shape; <b>Remove last annotation</b> removes the most recently added one. Undo and redo cover placement, styling, moving and deletion.</p>
<h2>Click markers</h2>
<p>Choose <b>Move click marker</b> and click its new position. The Click marker checkbox hides/shows it; Remove marker deletes it. Change marker colour, radius and numbering on the Document page.</p>
<p><b>Save annotated PNG</b> saves a flattened image in the project's Annotated folder. The PDF uses your current annotations automatically.</p>
""",
    "Document and PDF": """
<h1>Prepare and export your document</h1>
<p>Use <b>Document</b> to set the SOP title, company, reference, version, author, reviewer, approver and status. Add a company logo, purpose, scope, prerequisites and revision history.</p>
<p>Created can be edited; Last updated is maintained when the project is saved. Approved is a document label, not an electronic approval workflow.</p>
<p>Choose portrait or landscape. On Step editor, use <b>Preview</b> to review the cover, instructions, screenshots, markers, redactions and page breaks. Close the preview to return to editing.</p>
<p><b>Export &gt; Export PDF</b> lets you choose a filename and destination, with Exports as the default folder. Confirm before replacing an existing PDF.</p>
<p>Check sensitive information before sharing. Exported screenshots include flattened annotations and redactions, but original screenshots in the editable project remain unredacted.</p>
""",
    "Saving and recovery": """
<h1>Save, reopen and recover work</h1>
<p>Edits autosave shortly after a change. <b>Ctrl+S</b> saves immediately; the status bar reports saving problems.</p>
<p>Each project folder contains:</p>
<ul><li><b>project.json:</b> the editable procedure and image references.</li>
<li><b>Screenshots:</b> preserved original PNG images.</li>
<li><b>Annotated:</b> annotated PNGs you explicitly save.</li>
<li><b>Exports:</b> exported PDF documents.</li>
<li><b>project.backup.json:</b> a previous valid project state for recovery.</li></ul>
<p>Keep the whole folder together when moving an editable project. To reopen it, choose <b>Open SOP</b> and select project.json. Missing images can be replaced without discarding other steps.</p>
<p>If the project is damaged and a backup exists, the app offers recovery. A project lock prevents simultaneous editing. Remove a stale lock only after confirming no other instance has the project open.</p>
<p>If saving fails, keep the app open, check disk space/permissions and retry Ctrl+S. Closing during recording begins Stop; close again after it finishes.</p>
<p>Processing is local, but OneDrive or another sync client may upload a project saved inside a synced folder. Choose a non-synced location if required.</p>
""",
    "Templates": """
<h1>Choose or design a document template</h1>
<p>Open <b>Templates</b> in the sidebar. The library contains Standard SOP, named custom PDF layouts and uploaded Word documents. Save/upload a template once and reuse it for any number of projects. Preview template uses a temporary sample, without changing your SOP. New project creates a new folder with a separate template copy. Project-specific edits do not change the library or other projects.</p>
<p><b>Annotation library</b> is also available without a project open. Preview designs, create/edit in Studio, duplicate, import artwork or editable packs, export packs and delete saved entries. Use on current screenshot returns to the step editor. Library changes leave already placed copies unchanged.</p>
<h2>Create a custom layout</h2>
<ol><li>Choose <b>New custom template</b> and enter a name.</li><li>Choose a logo, company default, fonts, sizes, colours, margins, screenshot width, cover and page-break preferences. Header/footer text can use {title}, {reference}, {version} and {company}.</li><li><b>Save changes</b> adds it to the list. Use <b>Save as new template</b> with a different name for a variant.</li><li>Open an SOP, select an entry and choose <b>Apply selected template to SOP</b> or <b>Apply and preview PDF</b>.</li></ol>
<p>An SOP's existing company text takes priority over the template default. Template orientation overrides Document unless set to project. Header/footer space is reserved even with small margins.</p>
<h2>Upload a company Word template</h2>
<p>Choose <b>New template &gt; Import Word template</b> and name the uploaded .docx. Company covers, tables, sections, branding, styles and linked content controls are retained. Recognised authoring guidance and style demonstrations are removed; Lorem ipsum sample prose is cleared. Unfamiliar company content stays intact. The original upload is unchanged.</p>
<p>Use <b>Document &gt; Fill template fields</b> to work through labelled company table cells. <b>Next blank or placeholder</b> finds unfinished values. Recognised metadata opens Document details; custom values can be edited here. Complex controls offer <b>Edit on document</b>. Source edits apply on generation/rebuild; rebuilding confirms replacement of direct edits.</p>
<p>Word refreshes contents and figure/table lists for previews/PDF and direct editing. Imported Word structure and data bindings are retained so repeated values remain connected. Existing template assets stay unchanged; re-upload a new version to adopt structured preparation. A previously cleared asset cannot recover its cover without re-uploading the original.</p>
<p><b>Export Word</b> on Step editor saves DOCX. Word-template PDF preview/export requires installed desktop Microsoft Word. Standard/custom PDFs work without Word.</p>
<h2>Existing SOPs keep their layout</h2>
<p>Applying copies the template and assets into the SOP folder. Library edits/deletion do not change it. Apply again to use a newer version, or apply Standard SOP to return to the built-in layout.</p>
""",
    "Settings": """
<h1>Adjust the application</h1>
<ul><li><b>Capture:</b> screenshot delay, click timing, mouse buttons, manual shortcut, lossless PNG compression and initial screenshot.</li>
<li><b>Annotations:</b> default marker colour/radius and step numbers. The editor toolbar sets individual shape styles.</li>
<li><b>Document defaults:</b> company, author, reference prefix, logo, PDF orientation and project directory.</li>
<li><b>Appearance:</b> light or dark theme.</li></ul>
<p>Document and marker defaults are used for new projects. Use Document to change an existing project. Capture settings take effect on the next recording session.</p>
<p>The default manual shortcut is Ctrl+Shift+F8; your current shortcut is <b>{manual_shortcut}</b>. If Windows reports a conflict, choose another supported combination such as Ctrl+Alt+F9.</p>
""",
    "Keyboard shortcuts": """
<h1>Keyboard shortcuts</h1>
<table cellpadding="8"><tr><td><b>F1</b></td><td>Open this guide while SOP Capture Studio has focus</td></tr>
<tr><td><b>Ctrl+N</b></td><td>New SOP</td></tr><tr><td><b>Ctrl+O</b></td><td>Open SOP</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save changes now</td></tr><tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr><tr><td><b>Esc</b></td><td>Cancel an annotation while dragging</td></tr>
<tr><td><b>{manual_shortcut}</b></td><td>Manual screenshot during an active session, with the selected target focused</td></tr></table>
<p>The manual screenshot shortcut is configurable in Settings and works while the target application has focus. The other shortcuts operate within SOP Capture Studio.</p>
""",
    "Troubleshooting": """
<h1>Common problems</h1>
<h2>Start capture is disabled</h2><p>Create/open a project and select a target window. Wait for any background operation to finish. Live capture requires Windows.</p>
<h2>No screenshot appears</h2><p>Check that recording is not paused, the selected target is foreground and the mouse button is enabled in Settings. Minimized, closed or unavailable targets are skipped. Watch the status bar for the reason.</p>
<h2>Blank, stale or incomplete preview</h2><p>Some browser GPU content, elevated/protected applications and separate popup windows do not support window-only rendering. Try another supported window and inspect each screenshot. The app does not fall back to capturing your entire desktop.</p>
<h2>Manual shortcut is unavailable</h2><p>Another application may already use it. Change the combination in Settings, then start capture again.</p>
<h2>Annotation is too small or text is clipped</h2><p>Select it using Edit annotations. Change Stroke or Text size, or drag its handles to enlarge the area. Preview/export use screenshot pixels, not display pixels.</p>
<h2>Cannot open or save a project</h2><p>Check permissions, disk space and whether another instance is editing it. Use the offered backup recovery if needed. Keep the app open if unsaved edits remain.</p>
<p>Use <b>Help → Open logs</b> or the sidebar's Open logs button to find diagnostic logs when reporting a problem.</p>
""",
}


class UserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SOP Capture Studio — User guide")
        self.resize(960, 700)
        self.setMinimumSize(720, 480)
        self.shortcut = "Ctrl+Shift+F8"
        outer = QVBoxLayout(self)
        title = QLabel("Help")
        title.setObjectName("heading")
        outer.addWidget(title)
        row = QHBoxLayout()
        self.topics = QListWidget()
        self.topics.addItems(TOPICS)
        self.topics.setFixedWidth(190)
        self.topics.setWordWrap(True)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.document().setDefaultStyleSheet("body {font-family: 'Segoe UI'; font-size: 10pt;} h1 {font-size: 18pt;} h2 {font-size: 12pt;} p, li {line-height: 145%;} li {margin-bottom: 8px;}")
        self.topics.currentTextChanged.connect(self._render)
        row.addWidget(self.topics)
        row.addWidget(self.browser, 1)
        outer.addLayout(row, 1)
        close = QPushButton("Close guide")
        close.clicked.connect(self.close)
        outer.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.show_topic("Getting started")

    def show_topic(self, topic="Getting started", shortcut=None):
        if shortcut is not None: self.shortcut = shortcut
        if topic not in TOPICS: topic = "Getting started"
        self.topics.setCurrentRow(list(TOPICS).index(topic))
        self._render(topic)

    def _render(self, topic):
        html = TOPICS.get(topic, "").replace("{manual_shortcut}", escape(self.shortcut))
        if topic == "Keyboard shortcuts" and hasattr(self.parent(), "shortcut_profile"):
            from ..shortcuts import ACTIONS
            profile = self.parent().shortcut_profile
            rows = [(key, ACTIONS[action][0]) for action, key in profile["bindings"].items() if key]
            rows += [(row["shortcut"], row["name"]) for row in profile["sequences"] if row["shortcut"]]
            html = "<h1>Current keyboard shortcuts</h1><table cellpadding='8'>"+"".join(
                f"<tr><td><b>{escape(key)}</b></td><td>{escape(label)}</td></tr>" for key, label in rows)+"</table>"
            html += "<p>Manual capture: <b>"+escape(self.shortcut)+"</b> (global, while recording).</p>"
            html += "<p>Open Settings &gt; Customise shortcuts to assign keys, clear assignments, create ordered action sequences, or import/export a profile. Changes apply when you choose Apply. Restore defaults removes custom sequences. App shortcuts work while the studio is active; reserved text-editing keys stay available in text fields. Sequences stop if an action is unavailable. Esc cancels an annotation gesture.</p>"
        self.browser.setHtml(html)
        self.browser.verticalScrollBar().setValue(0)
