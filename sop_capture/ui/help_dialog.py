"""Offline, topic-based help packaged with the application."""
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QTextBrowser, QPushButton, QLabel


TOPICS = {
    "Callouts, sections and review": """<h1>Make longer procedures easier to follow</h1>
<p><b>Text callout:</b> select Text callout in the annotation dropdown, enter the label, then drag from the button or field to the label position. Adjust colour, stroke and text size. Use Edit annotations to move the target handle or drag the label independently. A live preview appears while dragging.</p>
<p><b>Sections:</b> enter a section name below a step title, or choose Group steps and select a first and last step. Rename section changes every step using that name. Blank names remove grouping. Section headings appear in the list and PDF/Word exports; step numbering stays continuous. New steps inherit the selected section.</p>
<p><b>Review SOP:</b> check missing document details, instructions and screenshots. Select an item and choose Fix selected item to return to its editor. PDF and Word export show the checklist when issues exist; Export anyway allows intentional omissions in drafts.</p>""",

    "Getting started": """<h1>Create your first SOP</h1>
<p>SOP Capture Studio turns screenshots of a process into an editable procedure and a PDF.</p>
<ol>
<li>On <b>Capture</b>, choose <b>New SOP</b>, enter a title and choose where to save the project.</li>
<li>Choose <b>Refresh windows</b>, select the application you want to document and use <b>Preview selection</b> to check the screenshot.</li>
<li>Choose <b>Start capture</b>. The main window minimises and floating capture controls appear.</li>
<li>Perform the process in your selected application. Clicks create steps automatically.</li>
<li>Choose <b>Stop</b> on the floating controls. Add instructions in the <b>Step editor</b>.</li>
<li>Complete the <b>Document</b> details, choose <b>Preview PDF</b>, then <b>Export PDF</b>.</li>
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
<p>Choose a tool above the screenshot, drag to see a <b>live preview</b>, then release to place it. Press <b>Esc</b> while dragging to cancel.</p>
<ul>
<li><b>Arrow:</b> the <b>Arrow style</b> dropdown shows pictures of solid, open-head and double-headed arrows.</li>
<li><b>Straight line</b>, <b>Circle / ellipse</b> and <b>Outline box</b> mark areas or connections.</li>
<li><b>Translucent highlight:</b> draw a coloured area and adjust Highlight opacity.</li>
<li><b>Text label:</b> enter your label, choose a text size and drag a box. Text wraps inside it; enlarge the box or reduce the font if text is clipped.</li>
<li><b>Solid redaction</b> covers an area with opaque black. <b>Blur</b> softens an area; use solid redaction for information that must be unreadable.</li>
</ul>
<p>Set <b>Colour</b> and <b>Stroke</b> thickness before drawing. Sizes are measured in original screenshot pixels, so appearance depends on the preview scale.</p>
<h2>Change an existing annotation</h2>
<p>Choose <b>Edit annotations</b>, then click a shape. Drag its body to move it or drag a square handle to resize it/change an arrow endpoint. The toolbar edits the selected shape. With no shape selected, settings apply to new shapes.</p>
<p><b>Delete selected</b> removes the selected shape; <b>Remove last annotation</b> removes the most recently added one. Undo and redo cover placement, styling, moving and deletion.</p>
<h2>Click markers</h2>
<p>Choose <b>Move click marker</b> and click its new position. The Click marker checkbox hides/shows it; Remove marker deletes it. Change marker colour, radius and numbering on the Document page.</p>
<p><b>Save annotated PNG</b> saves a flattened image in the project's Annotated folder. The PDF uses your current annotations automatically.</p>
""",
    "Document and PDF": """
<h1>Prepare and export your document</h1>
<p>Use <b>Document</b> to set the SOP title, company, reference, version, author, reviewer, approver and status. Add a company logo, purpose, scope, prerequisites and revision history.</p>
<p>Created can be edited; Last updated is maintained when the project is saved. Approved is a document label, not an electronic approval workflow.</p>
<p>Choose portrait or landscape. On Step editor, use <b>Preview PDF</b> to review the cover, instructions, screenshots, markers, redactions and page breaks. Close the preview to return to editing.</p>
<p><b>Export PDF</b> lets you choose a filename and destination, with Exports as the default folder. Confirm before replacing an existing PDF.</p>
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
<p>Open <b>Templates</b> in the sidebar. The library contains Standard SOP, named custom PDF layouts and uploaded Word documents.</p>
<h2>Create a custom layout</h2>
<ol><li>Choose <b>New custom template</b> and enter a name.</li><li>Choose a logo, company default, fonts, sizes, colours, margins, screenshot width, cover and page-break preferences. Header/footer text can use {title}, {reference}, {version} and {company}.</li><li><b>Save changes</b> adds it to the list. Use <b>Save as new template</b> with a different name for a variant.</li><li>Open an SOP, select an entry and choose <b>Apply selected template to SOP</b> or <b>Apply and preview PDF</b>.</li></ol>
<p>An SOP's existing company text takes priority over the template default. Template orientation overrides Document unless set to project. Header/footer space is reserved even with small margins.</p>
<h2>Upload a company Word template</h2>
<p>Choose <b>Upload Word template</b>, select a .docx file and give it a name. Map its detected paragraph styles to step titles, instructions and captions, then save and apply it. Company fonts need to be installed on the exporting PC.</p>
<p>Prepare the document in Word with placeholders such as {{title}}, {{company}}, {{reference}}, {{version}}, {{author}}, {{purpose}}, {{scope}} and {{revision_history}}. Put <b>{{steps}}</b> alone in a body paragraph for repeating steps. Put <b>{{logo}}</b> alone in a paragraph for a logo override.</p>
<p><b>Save example Word template</b> provides a ready-to-edit starting document. If an upload has no steps placeholder, import explains that generated content will be appended. The app does not automatically understand an arbitrary company form.</p>
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
        title = QLabel("How to use SOP Capture Studio")
        title.setObjectName("heading")
        outer.addWidget(title)
        row = QHBoxLayout()
        self.topics = QListWidget()
        self.topics.addItems(TOPICS)
        self.topics.setFixedWidth(190)
        self.topics.setWordWrap(True)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.document().setDefaultStyleSheet("body {font-family: 'Segoe UI'; font-size: 11pt;} h1 {font-size: 20pt;} h2 {font-size: 13pt;} p, li {line-height: 145%;} li {margin-bottom: 8px;}")
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
        self.browser.setHtml(TOPICS.get(topic, "").replace("{manual_shortcut}", escape(self.shortcut)))
        self.browser.verticalScrollBar().setValue(0)
