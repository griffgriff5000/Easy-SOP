"""Small shared building blocks for consistent desktop workspaces."""
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QToolButton,QMenu,QFormLayout,QButtonGroup,QScrollArea,QStyledItemDelegate,QStyleOptionViewItem)


def page_header(layout,title,subtitle=''):
    label=QLabel(title);label.setObjectName('heading');layout.addWidget(label)
    if subtitle:
        caption=QLabel(subtitle);caption.setObjectName('subheading');caption.setWordWrap(True);layout.addWidget(caption)


def menu_button(text,entries,parent=None):
    button=QToolButton(parent);button.setText(text);button.setAccessibleName(text);button.setProperty('menuButton',True)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    menu=QMenu(button)
    for title,callback in entries:
        if title is None:menu.addSeparator()
        else:menu.addAction(title,callback)
    button.setMenu(menu);return button


def form_page():
    widget=QWidget();widget.setObjectName('scrollPage')
    form=QFormLayout(widget);form.setSpacing(12);form.setContentsMargins(16,16,16,16)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    return widget,form


def scroll_panel(widget):
    area=QScrollArea();area.setWidgetResizable(True);area.setWidget(widget);return area


def tool_icon(kind):
    pixmap=QPixmap(24,24);pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#087f8c'),2));painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind in {'rect','highlight','redact','blur'}:painter.drawRoundedRect(4,5,16,14,1,1)
    elif kind in {'ellipse','circle'}:painter.drawEllipse(4,5,16,14)
    elif kind=='triangle':painter.drawPolygon(QPolygonF([QPointF(12,4),QPointF(21,20),QPointF(3,20)]))
    elif kind=='diamond':painter.drawPolygon(QPolygonF([QPointF(12,3),QPointF(21,12),QPointF(12,21),QPointF(3,12)]))
    elif kind in {'arrow','line'}:
        painter.drawLine(4,19,20,5)
        if kind=='arrow':painter.drawPolyline(QPolygonF([QPointF(11,5),QPointF(20,5),QPointF(20,14)]))
    elif kind=='text':
        painter.drawLine(4,5,20,5);painter.drawLine(12,5,12,20);painter.drawLine(8,20,16,20)
    elif kind=='path':painter.drawPolyline(QPolygonF([QPointF(3,17),QPointF(7,7),QPointF(11,18),QPointF(16,5),QPointF(21,14)]))
    else:painter.drawPolygon(QPolygonF([QPointF(5,3),QPointF(6,20),QPointF(11,15),QPointF(16,21),QPointF(19,18),QPointF(14,12),QPointF(21,10)]))
    painter.end();return QIcon(pixmap)


def tool_rail(combo):
    rail=QWidget();rail.setObjectName('toolRail');box=QVBoxLayout(rail);box.setContentsMargins(4,8,4,8);box.setSpacing(4)
    group=QButtonGroup(rail);group.setExclusive(True);buttons=[]
    for index in range(combo.count()):
        button=QToolButton();button.setCheckable(True);button.setIcon(tool_icon(combo.itemData(index)));button.setIconSize(QSize(24,24));button.setFixedSize(38,38)
        button.setToolTip(combo.itemText(index));button.setAccessibleName(combo.itemText(index));button.clicked.connect(lambda checked=False,i=index:combo.setCurrentIndex(i))
        group.addButton(button);box.addWidget(button);buttons.append(button)
    combo.currentIndexChanged.connect(lambda index:buttons[index].setChecked(True) if index>=0 else None)
    buttons[combo.currentIndex()].setChecked(True);box.addStretch();return rail


class ThumbnailDelegate(QStyledItemDelegate):
    """Put step screenshots above their captions, keeping long titles readable."""
    def initStyleOption(self,option,index):
        super().initStyleOption(option,index)
        option.decorationPosition=QStyleOptionViewItem.Position.Top
        option.decorationAlignment=Qt.AlignmentFlag.AlignHCenter
        option.displayAlignment=Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop

    def sizeHint(self,option,index):
        size=super().sizeHint(option,index)
        return QSize(size.width(),max(112,size.height()))
