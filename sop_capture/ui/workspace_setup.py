"""Adapt existing business widgets into personal dock workspaces without duplicating data."""
from pathlib import Path
from PySide6.QtCore import QStandardPaths,Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QScrollArea,QLabel,QApplication,QMessageBox,QPushButton,QToolButton
from ..workspace_layouts import LayoutLibrary
from .workspaces import DockWorkspace,WorkspaceManager

SCREENS={0:('capture','Capture'),1:('editor','Step editor'),2:('document','Document'),3:('settings','Settings'),4:('templates','Template library'),5:('home','Home'),6:('annotations','Annotation library'),7:('revision','Document review')}


def wrap(page,key):
    old=page.layout();headers=[old.takeAt(0),old.takeAt(0)];tools=old.takeAt(0) if old.count() and old.itemAt(0).layout() else None
    holder=QWidget();holder.setObjectName('scrollPage');holder.setLayout(old);old.setContentsMargins(0,0,0,0)
    layout=QVBoxLayout(page);layout.setSpacing(8)
    for item in headers:
        if item and item.widget():layout.addWidget(item.widget())
    if key=='revision':
        # Keep document identity across the full width, above the dockable work area.
        for _ in range(2):
            item=old.takeAt(0)
            if item.widget():layout.addWidget(item.widget())
            elif item.layout():layout.addLayout(item.layout())
    host=DockWorkspace(key,holder,page);host.style_target=page;layout.addWidget(host,1)
    if tools:
        widget=QWidget();widget.setLayout(tools.layout());host.add_panel('tools','Screen actions',widget,'top')
        if key in {'capture','editor','revision'}:host.panels['tools'].hide()
    return host


def panel_from_splitter(host,role,title,widget,area):
    widget.setMaximumWidth(16777215);widget.setMaximumHeight(16777215);host.add_panel(role,title,widget,area)


def install_workspaces(window,library=None):
    if library is None:library=LayoutLibrary(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'workspace-layouts.json')
    manager=WorkspaceManager(library,window);window.workspaces=manager;window.workspace_keys={i:key for i,(key,title) in SCREENS.items()}
    global_defaults={0:['new','open','capture_start','capture_stop'],1:['undo','redo','add_step','duplicate_step','annotation_studio','export_pdf'],2:['save','review','preview_pdf','export_word'],3:['shortcuts'],4:[],5:['new','open'],6:['annotation_studio'],7:['screen_new','screen_open','undo','redo','screen_export']}
    for index,(key,title) in SCREENS.items():
        page=window.settings if index==3 else window.pages.widget(index);host=wrap(page,key);host.global_dark=window.settings.value('theme')=='Dark'
        if index==0:panel_from_splitter(host,'outline','Application windows',window.windows_list,'left')
        elif index==1:
            steps=window.editor_splitter.widget(0);panel_from_splitter(host,'outline','Steps',steps,'left');panel_from_splitter(host,'properties','Step details and annotations',window.editor_inspector,'right');window.editor_inspector.setMinimumWidth(220)
            # The original Details control now toggles the dock instead of hiding only its contents.
            window.inspector_toggle.toggled.disconnect();window.inspector_toggle.toggled.connect(host.panels['properties'].setVisible)
            def sync_inspector(visible,h=host):
                if h.suspended:return
                previous=window.inspector_toggle.blockSignals(True);window.inspector_toggle.setChecked(not h.panels['properties'].isHidden());window.inspector_toggle.blockSignals(previous)
            host.panels['properties'].visibilityChanged.connect(sync_inspector)
        elif index==2:panel_from_splitter(host,'properties','Document fields and template text',window.builder_edit_tabs,'right');window.builder_edit_tabs.setMinimumWidth(250)
        elif index==4:panel_from_splitter(host,'outline','Saved templates',window.templates_page.catalogue,'left')
        elif index==6:panel_from_splitter(host,'outline','Saved annotations',window.annotation_library_page.entries,'left')
        elif index==7:
            revision=window.revision_page
            panel_from_splitter(host,'outline','Source elements',revision.sources,'top');revision.sources.setMaximumHeight(110)
            old_right=revision.right_tabs.parentWidget()
            panel_from_splitter(host,'properties','New revision and placement',revision.right_tabs,'right')
            old_right.hide()
            content=revision.right_tabs.widget(0);content.setObjectName('scrollPage');revision.right_tabs.removeTab(0)
            approval=content.layout().takeAt(content.layout().count()-1);content.layout().removeWidget(revision.proposal)
            shell=QWidget();shell.setObjectName('scrollPage');shell_box=QVBoxLayout(shell);shell_box.setContentsMargins(0,0,0,0)
            area=QScrollArea();area.setWidgetResizable(True);area.setWidget(content);shell_box.addWidget(area,1);shell_box.addWidget(revision.proposal);shell_box.addLayout(approval.layout());revision.right_tabs.insertTab(0,shell,'Placement')
            final=revision.right_tabs.widget(3);final.setObjectName('scrollPage');revision.right_tabs.removeTab(3);word_area=QScrollArea();word_area.setWidgetResizable(True);word_area.setWidget(final);revision.right_tabs.insertTab(3,word_area,'Word')
            revision.status.setParent(page);page.layout().addWidget(revision.status)
            for label in revision.source_tabs.parentWidget().findChildren(QLabel):label.setWordWrap(True)
            # Keep the original source preview central; all editing controls remain the same objects.
            assistant=QWidget();assistant_box=QHBoxLayout(assistant);assistant_box.setContentsMargins(5,5,5,5)
            for field in (revision.instruction,revision.model,revision.ask_button):assistant_box.addWidget(field)
            for button in revision.findChildren(QPushButton):
                if button.text()=='Find local AI':assistant_box.addWidget(button);break
            host.add_panel('assistant','Local assistant',assistant,'bottom')
            stages=QHBoxLayout()
            for label,tab in [('1  Choose documents',None),('2  Review transfers',0),('3  Finalise',3)]:
                item=QToolButton();item.setText(label)
                def stage(checked=False,target=tab,r=revision,h=host):
                    if target is None:r.new()
                    elif r.work:h.panels['properties'].show();r.right_tabs.setCurrentIndex(target)
                item.clicked.connect(stage);stages.addWidget(item,1)
            page.layout().insertLayout(2,stages)
        actions={}
        navigation={identity for identity in window.action_bindings if identity.startswith('page_')}|{'help','shortcuts'}
        allowed={0:{'new','open','save','capture_start','capture_pause','capture_stop'},1:set(window.action_bindings),2:{'new','open','save','undo','redo','review','preview_pdf','export_pdf','export_word'},3:{'annotation_studio'},4:set(),5:{'new','open'},6:{'annotation_studio'},7:{'undo','redo'}}[index]|navigation
        for identity,existing in window.action_bindings.items():
            if identity not in allowed:continue
            action=QAction(existing.text(),host);action.triggered.connect(lambda checked=False,i=identity:window.action_bindings[i].trigger());actions[identity]=action
        if index==0:
            for identity,label,callback in [('screen_refresh','Refresh windows',window.refresh_windows),('screen_preview','Preview selection',window.preview_target),('screen_images','Screenshots folder',window.open_screenshots)]:
                action=QAction(label,host);action.triggered.connect(callback);actions[identity]=action
        if index==4:
            for identity,label,callback in [('screen_custom','New custom template',window.templates_page.new_custom),('screen_import','Import Word template',window.templates_page.import_word),('screen_preview','Preview template',window.templates_page.preview_selected),('screen_apply','Apply template',window.templates_page.apply_selected),('screen_save','Save template',window.templates_page.save_changes)]:
                action=QAction(label,host);action.triggered.connect(lambda checked=False,call=callback:call());actions[identity]=action
        if index==6:
            library_page=window.annotation_library_page
            for identity,label,callback in [('screen_new','New annotation',lambda:library_page.edit_design(new=True)),('screen_edit','Edit annotation',library_page.edit_design),('screen_import','Import annotation pack',library_page.import_pack),('screen_export','Export annotation pack',library_page.export),('screen_duplicate','Duplicate annotation',library_page.duplicate),('screen_use','Use annotation',library_page.use_selected)]:
                action=QAction(label,host);action.triggered.connect(lambda checked=False,call=callback:call());actions[identity]=action
        if index==7:
            for identity,label,callback in [('screen_new','New revision',revision.new),('screen_open','Open revision',revision.open),('undo','Undo transfer',revision.undo),('redo','Redo transfer',revision.redo),('screen_export','Export revised Word',revision.export),('screen_original','Original pages',revision.original_pages)]:
                action=QAction(label,host);action.triggered.connect(callback);actions[identity]=action
        if index in {2,7}:
            editor=window.word_editor if index==2 else window.revision_page.word_editor
            for item in editor.edit_buttons[3:]:item.hide()
            for identity,label,command in [('word_bold','Word: bold','Bold'),('word_italic','Word: italic','Italic'),('word_underline','Word: underline','Underline')]:
                action=QAction(label,host);action.triggered.connect(lambda checked=False,e=editor,c=command:e._command(c) if e.session else None);actions[identity]=action
        host.set_actions(actions,global_defaults[index]);host.appearance()
        if 'outline' in host.panels:host.resizeDocks([host.panels['outline']],[190],Qt.Orientation.Horizontal)
        if 'properties' in host.panels:host.resizeDocks([host.panels['properties']],[410 if index==7 else 270],Qt.Orientation.Horizontal)
        if index==7:host.resizeDocks([host.panels['outline']],[100],Qt.Orientation.Vertical)
        manager.register(key,title,host)
    menu=window.menuBar().addMenu('Workspace');window.workspace_menu=menu
    menu.addAction('Customise this workspace…',manager.show_dialog)
    panels_menu=menu.addMenu('Show / hide panels')
    def panels():
        panels_menu.clear()
        if manager.active is not None:
            for dock in manager.hosts[manager.active].panels.values():panels_menu.addAction(dock.toggleViewAction())
    panels_menu.aboutToShow.connect(panels)
    lock=menu.addAction('Lock layout');lock.setCheckable(True)
    lock.triggered.connect(lambda checked:manager.hosts[manager.active].set_locked(checked))
    menu.aboutToShow.connect(lambda:lock.setChecked(manager.hosts[manager.active].options['locked']))
    menu.addAction('Reset this screen',lambda:manager.hosts[manager.active].reset_layout())
    def reset_all():
        if QMessageBox.question(window,'Reset all workspaces','Reset panel positions, toolbars and appearance on all screens? Named layouts and document data are kept.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:manager.reset_all()
    menu.addAction('Reset all screens…',reset_all);menu.addSeparator();menu.addAction('Customise shortcuts…',window.show_shortcuts)
    # Keep a recovery/customisation control available even when every dock/toolbar is hidden.
    window.workspace_button=window.menuBar().addAction('Customise workspace…');window.workspace_button.triggered.connect(manager.show_dialog)
    manager.activate(window.workspace_keys[window.pages.currentIndex()]);return manager
