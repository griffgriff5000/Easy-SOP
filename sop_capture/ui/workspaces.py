"""Native per-screen docking, recoverable layout preferences and toolbar editing."""
import base64
from copy import deepcopy
from PySide6.QtCore import Qt,QByteArray,QRect,QTimer,Signal,QEvent
from PySide6.QtGui import QAction,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QDockWidget,QToolBar,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDialog,QDialogButtonBox,QListWidget,QListWidgetItem,QComboBox,QSpinBox,QCheckBox,QFormLayout,QInputDialog,QMessageBox,QStyle)
from ..workspace_layouts import validate_layout,portable_copy
from .theme import stylesheet

AREAS={'left':Qt.DockWidgetArea.LeftDockWidgetArea,'right':Qt.DockWidgetArea.RightDockWidgetArea,'top':Qt.DockWidgetArea.TopDockWidgetArea,'bottom':Qt.DockWidgetArea.BottomDockWidgetArea}


class DockWorkspace(QMainWindow):
    changed=Signal()
    def __init__(self,name,central,parent=None):
        super().__init__(parent);self.name=name;self.panels={};self.actions={};self.default_layout=None;self.suspended=False;self.suspended_visibility={};self.restoring=False
        self.options={'theme':'auto','font_size':10,'density':'comfortable','tool_style':'both','locked':False};self.global_dark=False;self.style_target=self
        self.setObjectName('workspace_'+name);self.setWindowFlags(Qt.WindowType.Widget);self.setDockNestingEnabled(True);self.setDockOptions(self.DockOption.AllowNestedDocks|self.DockOption.AllowTabbedDocks|self.DockOption.AnimatedDocks);self.setCentralWidget(central)
        self.toolbar=QToolBar('Workspace tools',self);self.toolbar.setObjectName('toolbar_'+name);self.addToolBar(self.toolbar);self.toolbar_ids=[]
        self.toolbar.topLevelChanged.connect(self.notify);self.toolbar.visibilityChanged.connect(self.notify);self.toolbar.installEventFilter(self)

    def notify(self,*args):
        if not self.restoring and not self.suspended:self.changed.emit()

    def eventFilter(self,watched,event):
        if event.type() in {QEvent.Type.Resize,QEvent.Type.Move}:self.notify()
        return super().eventFilter(watched,event)

    def add_panel(self,role,title,widget,area='right'):
        dock=QDockWidget(title,self);dock.setObjectName('panel_'+self.name+'_'+role);dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas);dock.setWidget(widget);self.addDockWidget(AREAS[area],dock);self.panels[role]=dock
        dock.topLevelChanged.connect(self.notify);dock.dockLocationChanged.connect(self.notify);dock.visibilityChanged.connect(self.notify);dock.installEventFilter(self);return dock

    def set_actions(self,actions,selected):
        self.actions=actions;self.set_toolbar(selected)

    def set_toolbar(self,identities):
        self.toolbar.clear();self.toolbar_ids=[]
        icons={'save':'SP_DialogSaveButton','open':'SP_DialogOpenButton','new':'SP_FileDialogNewFolder','undo':'SP_ArrowBack','redo':'SP_ArrowForward','help':'SP_DialogHelpButton','delete_step':'SP_TrashIcon','add_step':'SP_FileDialogNewFolder','duplicate_step':'SP_FileDialogContentsView','annotation_studio':'SP_FileDialogDetailedView','export_pdf':'SP_DialogSaveButton','export_word':'SP_DialogSaveButton','preview_pdf':'SP_FileDialogInfoView','review':'SP_DialogApplyButton','capture_start':'SP_MediaPlay','capture_pause':'SP_MediaPause','capture_stop':'SP_MediaStop','screen_new':'SP_FileDialogNewFolder','screen_open':'SP_DialogOpenButton','screen_export':'SP_DialogSaveButton','screen_original':'SP_FileDialogInfoView'}
        for identity in dict.fromkeys(identities):
            action=self.actions.get(identity)
            if action is None:continue
            if action.icon().isNull():action.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap,icons.get(identity,'SP_FileIcon'))))
            self.toolbar.addAction(action);self.toolbar_ids.append(identity)
        self.toolbar.setVisible(bool(self.toolbar_ids));self.notify()

    def seal_defaults(self):self.default_layout=self.capture()

    def capture(self):
        panels={}
        for role,dock in self.panels.items():
            area=next((name for name,value in AREAS.items() if value==self.dockWidgetArea(dock)),'right');geometry=dock.geometry()
            visible=self.suspended_visibility.get(role,not dock.isHidden()) if self.suspended else not dock.isHidden()
            panels[role]={'area':area,'visible':visible,'floating':dock.isFloating(),'size':[max(100,dock.width()),max(60,dock.height())],'geometry':[geometry.x(),geometry.y(),geometry.width(),geometry.height()]}
        return validate_layout({'version':1,'screen':self.name,'state':base64.b64encode(bytes(self.saveState(1))).decode(),'panels':panels,'toolbar':self.toolbar_ids[:],'available_actions':list(self.actions),**self.options})

    def set_locked(self,locked):
        self.options['locked']=locked
        features=QDockWidget.DockWidgetFeature.DockWidgetClosable
        if not locked:features|=QDockWidget.DockWidgetFeature.DockWidgetMovable|QDockWidget.DockWidgetFeature.DockWidgetFloatable
        for panel in self.panels.values():panel.setFeatures(features)
        self.toolbar.setMovable(not locked);self.toolbar.setFloatable(not locked);self.notify()

    def appearance(self):
        dark=self.global_dark if self.options['theme']=='auto' else self.options['theme']=='dark'
        padding=3 if self.options['density']=='compact' else 6
        rules=stylesheet(dark) if self.options['theme']!='auto' else ''
        if self.options['font_size']!=10:rules+=f'\nQWidget {{ font-size:{self.options["font_size"]}pt; }}'
        if self.options['density']=='compact':rules+=f'\nQPushButton,QToolButton {{ padding:{padding}px 8px; }} QListWidget::item {{ padding:{padding}px 5px; }}'
        if self.style_target.styleSheet()!=rules:self.style_target.setStyleSheet(rules)
        self.toolbar.setToolButtonStyle({'icons':Qt.ToolButtonStyle.ToolButtonIconOnly,'text':Qt.ToolButtonStyle.ToolButtonTextOnly,'both':Qt.ToolButtonStyle.ToolButtonTextBesideIcon}[self.options['tool_style']])

    def apply_layout(self,layout,portable=False):
        layout=portable_copy(layout,self.capture(),set(self.actions)) if portable or layout['screen']!=self.name else validate_layout(layout)
        self.restoring=True
        try:
            self.options={k:layout[k] for k in self.options};self.set_toolbar(layout['toolbar'])
            native=False
            if layout.get('state'):
                native=self.restoreState(QByteArray(base64.b64decode(layout['state'])),1)
            for role,data in layout['panels'].items():
                dock=self.panels.get(role)
                if dock is None:continue
                if not native:
                    dock.setFloating(False);self.addDockWidget(AREAS[data['area']],dock);self.resizeDocks([dock],[max(80,data['size'][0])],Qt.Orientation.Horizontal);self.resizeDocks([dock],[max(60,data['size'][1])],Qt.Orientation.Vertical);dock.setFloating(data['floating'])
                if dock.isFloating():
                    coords=data.get('geometry',[80,80,400,300]);rectangle=QRect(*coords);screens=QApplication.screens();screen=next((s for s in screens if s.availableGeometry().intersects(rectangle)),QApplication.primaryScreen());available=screen.availableGeometry()
                    rectangle.setWidth(max(180,min(rectangle.width(),available.width())));rectangle.setHeight(max(100,min(rectangle.height(),available.height())));rectangle.moveLeft(max(available.left(),min(rectangle.left(),available.right()-rectangle.width()+1)));rectangle.moveTop(max(available.top(),min(rectangle.top(),available.bottom()-rectangle.height()+1)));dock.setGeometry(rectangle)
                dock.setVisible(data['visible']);self.suspended_visibility[role]=data['visible']
            self.set_locked(layout['locked']);self.appearance()
            if self.suspended:
                for dock in self.panels.values():
                    if dock.isFloating():dock.hide()
        finally:self.restoring=False
        self.notify()

    def reset_layout(self):
        if self.default_layout:self.apply_layout(deepcopy(self.default_layout))

    def deactivate(self):
        if self.suspended:return
        self.suspended_visibility={role:not dock.isHidden() for role,dock in self.panels.items()};self.suspended=True
        for dock in self.panels.values():
            if dock.isFloating():dock.hide()
        if self.toolbar.isFloating():self.toolbar.hide()

    def activate(self):
        self.restoring=True
        try:
            for role,visible in self.suspended_visibility.items():self.panels[role].setVisible(visible)
            self.suspended=False;self.toolbar.setVisible(bool(self.toolbar_ids))
        finally:self.restoring=False


class WorkspaceDialog(QDialog):
    def __init__(self,manager,screen,parent=None):
        super().__init__(parent);self.manager=manager;self.screen=screen;self.host=manager.hosts[screen];self.setWindowTitle('Customise workspace — '+manager.names[screen]);self.resize(760,650)
        box=QVBoxLayout(self);note=QLabel('Drag panel title bars to dock or float them. Changes here apply to this screen; use Copy to reuse compatible settings elsewhere.');note.setWordWrap(True);box.addWidget(note)
        row=QHBoxLayout();box.addLayout(row);left=QVBoxLayout();right=QVBoxLayout();row.addLayout(left,1);row.addLayout(right,1)
        left.addWidget(QLabel('Visible panels'));self.panels=QListWidget();left.addWidget(self.panels)
        current=self.host.capture()
        for role,dock in self.host.panels.items():
            item=QListWidgetItem(dock.windowTitle());item.setData(Qt.ItemDataRole.UserRole,role);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if current['panels'][role]['visible'] else Qt.CheckState.Unchecked);self.panels.addItem(item)
        right.addWidget(QLabel('Toolbar actions — checked items appear in this order'));self.actions=QListWidget();self.actions.setDragDropMode(QListWidget.DragDropMode.InternalMove);right.addWidget(self.actions)
        for identity in current['toolbar']+[k for k in self.host.actions if k not in current['toolbar']]:
            action=self.host.actions[identity];item=QListWidgetItem(action.icon(),action.text());item.setData(Qt.ItemDataRole.UserRole,identity);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if identity in current['toolbar'] else Qt.CheckState.Unchecked);self.actions.addItem(item)
        form=QFormLayout();box.addLayout(form);self.theme=QComboBox();self.theme.addItems(['auto','light','dark']);self.theme.setCurrentText(current['theme']);form.addRow('Theme',self.theme)
        self.font=QSpinBox();self.font.setRange(8,16);self.font.setValue(current['font_size']);form.addRow('Text size (pt)',self.font)
        self.density=QComboBox();self.density.addItems(['comfortable','compact']);self.density.setCurrentText(current['density']);form.addRow('Spacing',self.density)
        self.tool_style=QComboBox();self.tool_style.addItems(['both','icons','text']);self.tool_style.setCurrentText(current['tool_style']);form.addRow('Toolbar labels',self.tool_style)
        self.locked=QCheckBox('Lock panel and toolbar positions');self.locked.setChecked(current['locked']);form.addRow(self.locked)
        presets=QHBoxLayout();self.presets=QComboBox();self.presets.addItems(manager.library.presets());self.presets.addItem('');self.presets.setCurrentText('');presets.addStretch();presets.addWidget(self.presets)
        for label,callback in [('Load named',self.load_preset),('Save named…',self.save_preset),('Delete named',self.delete_preset),('Copy to…',self.copy),('Reset screen',self.reset)]:
            button=QPushButton(label);button.clicked.connect(callback);presets.addWidget(button)
        box.addLayout(presets);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close);buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply);buttons.rejected.connect(self.reject);box.addWidget(buttons)

    def apply(self):
        try:
            layout=self.host.capture();layout.update(theme=self.theme.currentText(),font_size=self.font.value(),density=self.density.currentText(),tool_style=self.tool_style.currentText(),locked=self.locked.isChecked())
            for i in range(self.panels.count()):item=self.panels.item(i);layout['panels'][item.data(Qt.ItemDataRole.UserRole)]['visible']=item.checkState()==Qt.CheckState.Checked
            layout['toolbar']=[self.actions.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.actions.count()) if self.actions.item(i).checkState()==Qt.CheckState.Checked]
            # Visibility/preferences are explicit; preserve existing native placement.
            self.host.apply_layout(layout);self.manager.save(self.screen);return True
        except Exception as exc:QMessageBox.warning(self,'Workspace',str(exc));return False

    def save_preset(self):
        if not self.apply():return
        name,ok=QInputDialog.getText(self,'Save named layout','Layout name:')
        if ok:
            try:self.manager.library.save_preset(name,self.host.capture());self.presets.clear();self.presets.addItems(self.manager.library.presets());self.presets.setCurrentText(name.strip())
            except Exception as exc:QMessageBox.warning(self,'Workspace',str(exc))

    def load_preset(self):
        name=self.presets.currentText()
        if name in self.manager.library.presets():self.host.apply_layout(self.manager.library.presets()[name],portable=self.manager.library.presets()[name]['screen']!=self.screen);self.manager.save(self.screen);self.accept()

    def delete_preset(self):
        name=self.presets.currentText()
        if name and QMessageBox.question(self,'Delete layout',f'Delete saved layout “{name}”?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:self.manager.library.delete_preset(name);self.presets.removeItem(self.presets.currentIndex())

    def copy(self):
        if not self.apply():return
        dialog=QDialog(self);dialog.setWindowTitle('Copy layout to screens');box=QVBoxLayout(dialog);note=QLabel('Only compatible panel roles and actions are copied. Other tools and document content stay on each screen.');note.setWordWrap(True);box.addWidget(note);targets=QListWidget();box.addWidget(targets)
        for key,title in self.manager.names.items():
            if key==self.screen:continue
            item=QListWidgetItem(title);item.setData(Qt.ItemDataRole.UserRole,key);item.setCheckState(Qt.CheckState.Unchecked);targets.addItem(item)
        all_button=QPushButton('Select all screens');all_button.clicked.connect(lambda:[targets.item(i).setCheckState(Qt.CheckState.Checked) for i in range(targets.count())]);box.addWidget(all_button)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);box.addWidget(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:self.manager.copy(self.screen,[targets.item(i).data(Qt.ItemDataRole.UserRole) for i in range(targets.count()) if targets.item(i).checkState()==Qt.CheckState.Checked])
            except Exception as exc:QMessageBox.warning(self,'Workspace',str(exc))

    def reset(self):self.host.reset_layout();self.manager.save(self.screen);self.accept()


class WorkspaceManager:
    def __init__(self,library,owner):
        self.library=library;self.owner=owner;self.hosts={};self.names={};self.active=None;self.timer=QTimer(owner);self.timer.setSingleShot(True);self.timer.setInterval(700);self.timer.timeout.connect(self.save_active)

    def register(self,key,title,host):
        self.hosts[key]=host;self.names[key]=title;host.seal_defaults();saved=self.library.screen(key)
        if saved:
            try:host.apply_layout(saved)
            except (ValueError,TypeError,KeyError):host.reset_layout()
        host.changed.connect(lambda:self.timer.start() if self.active==key else None);host.deactivate()

    def activate(self,key):
        if key==self.active:return
        if self.active is not None:self.save(self.active);self.hosts[self.active].deactivate()
        self.active=key;self.hosts[key].activate()

    def save(self,key):
        try:self.library.save_screen(key,self.hosts[key].capture());return True
        except OSError as exc:self.owner.statusBar().showMessage('Workspace layout could not be saved: '+str(exc));return False
    def save_active(self):
        try:
            if self.active is not None:self.save(self.active)
        except OSError as exc:self.owner.statusBar().showMessage('Workspace layout could not be saved: '+str(exc))

    def copy(self,source,targets):
        layout=self.hosts[source].capture()
        for target in targets:
            if target!=source:self.hosts[target].apply_layout(layout,portable=True);self.save(target)

    def show_dialog(self):
        if self.active is None:return
        dialog=WorkspaceDialog(self,self.active,self.owner);dialog.exec();dialog.deleteLater()

    def reset_all(self):
        for key,host in self.hosts.items():host.reset_layout();self.save(key)

    def close(self):
        self.timer.stop()
        for key,host in self.hosts.items():self.save(key);host.deactivate()
