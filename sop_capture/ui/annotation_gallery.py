"""Compact annotation icon grids with one shared tool selection."""
from PySide6.QtCore import Qt,QSize,Signal,QPointF
from PySide6.QtGui import QPixmap,QPainter,QPen,QColor,QIcon,QPolygonF,QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QFrame,QToolButton,QButtonGroup,QSizePolicy,QLayout


def tool_icon(kind):
    pixmap=QPixmap(40,40);pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    colour=QColor('#087f8c');painter.setPen(QPen(colour,2.4))
    if kind in {'arrow','line'}:
        painter.drawLine(7,31,32,8)
        if kind=='arrow':painter.drawPolyline(QPolygonF([QPointF(19,8),QPointF(32,8),QPointF(32,21)]))
    elif kind=='magnifier':
        painter.drawRect(4,4,25,25);painter.drawEllipse(9,9,15,15);painter.drawLine(24,25,35,36)
        painter.drawLine(13,16,21,16);painter.drawLine(17,12,17,20)
    elif kind=='circle':painter.drawEllipse(7,8,27,24)
    elif kind in {'highlight','highlighter','redact'}:
        if kind=='highlighter':painter.setBrush(QColor('#ffe57a'))
        if kind=='redact':painter.setBrush(QColor('#263442'))
        painter.drawRoundedRect(6,10,28,21,2,2)
    elif kind=='marker':
        painter.drawEllipse(7,7,26,26);painter.setBrush(colour);painter.drawEllipse(16,16,8,8)
    elif kind=='callout':
        painter.drawRoundedRect(5,6,30,22,3,3);painter.drawPolyline(QPolygonF([QPointF(12,28),QPointF(9,35),QPointF(23,28)]))
        painter.drawLine(11,14,29,14);painter.drawLine(11,20,25,20)
    elif kind=='text':
        painter.setFont(QFont('Arial',23));painter.drawText(pixmap.rect(),Qt.AlignmentFlag.AlignCenter,'A')
    elif kind=='blur':
        for row in range(4):
            for col in range(4):painter.fillRect(6+col*7,6+row*7,7,7,QColor('#c3dce0') if (row+col)%2 else colour)
    else:
        painter.setBrush(colour);painter.drawPolygon(QPolygonF([QPointF(9,5),QPointF(10,32),QPointF(18,24),QPointF(25,35),QPointF(30,32),QPointF(23,21),QPointF(34,19)]))
    painter.end();return QIcon(pixmap)


class IconGrid(QWidget):
    def __init__(self):
        super().__init__();self.buttons=[];self.columns=5
        self.grid=QGridLayout(self);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(4)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)

    def relayout(self):
        columns=max(1,self.width()//46)
        while self.grid.count():self.grid.takeAt(0)
        for index,button in enumerate(self.buttons):self.grid.addWidget(button,index//columns,index%columns,Qt.AlignmentFlag.AlignLeft)
        self.columns=columns;self.setFixedHeight(((len(self.buttons)+columns-1)//columns)*46)

    def resizeEvent(self,event):
        super().resizeEvent(event);self.relayout()

    def minimumSizeHint(self):return QSize(42,0)

    def sizeHint(self):return QSize(220,self.height())

    def add(self,button):self.buttons.append(button);self.relayout()

    def clear(self):
        while self.grid.count():self.grid.takeAt(0)
        for button in self.buttons:button.hide();button.deleteLater()
        self.buttons=[];self.relayout()


class AnnotationGallery(QWidget):
    tool_chosen=Signal(str)
    design_chosen=Signal(str)
    refresh_requested=Signal()

    def __init__(self,tools):
        super().__init__();self.default_buttons={};self.custom_buttons={};self.group=QButtonGroup(self)
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(8)
        box.addWidget(QLabel('Default annotations'))
        self.defaults=IconGrid();box.addWidget(self.defaults)
        for label,kind in tools:
            if kind=='design':continue
            item=self.make_button(label,tool_icon(kind));self.default_buttons[kind]=item
            item.clicked.connect(lambda checked=False,key=kind:self.tool_chosen.emit(key));self.defaults.add(item)
        self.divider=QFrame();self.divider.setFrameShape(QFrame.Shape.HLine);box.addWidget(self.divider)
        title=QHBoxLayout();title.addWidget(QLabel('Custom annotations'));title.addStretch()
        refresh=QToolButton();refresh.setText('↻');refresh.setToolTip('Refresh custom annotations');refresh.clicked.connect(self.refresh_requested);title.addWidget(refresh);box.addLayout(title)
        self.custom=IconGrid();box.addWidget(self.custom)
        self.empty=QLabel('Save designs in Annotation Studio to add them here.');self.empty.setObjectName('caption');self.empty.setWordWrap(True);box.addWidget(self.empty)
        self.setStyleSheet('QToolButton[annotationTile="true"] {border:1px solid transparent; border-radius:4px; padding:2px;} QToolButton[annotationTile="true"]:hover {border-color:#087f8c; background:#e2f0f2;} QToolButton[annotationTile="true"]:checked {border:2px solid #087f8c; background:#d7edf0;}')

    def make_button(self,label,icon):
        item=QToolButton();item.setProperty('annotationTile',True);item.setFixedSize(42,42);item.setIconSize(QSize(34,34));item.setIcon(icon)
        item.setToolTip(label);item.setAccessibleName(label);item.setCheckable(True);self.group.addButton(item)
        return item

    def clear_custom(self):
        for item in self.custom_buttons.values():self.group.removeButton(item)
        self.custom.clear();self.custom_buttons={};self.empty.show()

    def add_custom(self,identity,name,icon):
        item=self.make_button(name,icon);self.custom_buttons[identity]=item
        item.clicked.connect(lambda checked=False,key=identity:self.design_chosen.emit(key));self.custom.add(item);self.empty.hide()

    def select(self,kind,identity=None):
        self.group.setExclusive(False)
        for key,item in self.default_buttons.items():item.setChecked(kind==key)
        for key,item in self.custom_buttons.items():item.setChecked(kind=='design' and identity==key)
        self.group.setExclusive(True)

    def showEvent(self,event):
        super().showEvent(event);self.refresh_requested.emit()
