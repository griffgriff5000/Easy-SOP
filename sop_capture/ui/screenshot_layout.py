"""The same screenshot layout choices for documents and saved templates."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox,QLabel
from ..templates import appearance


class ScreenshotLayoutControls(QWidget):
    changed=Signal()
    def __init__(self):
        super().__init__();form=QFormLayout(self)
        self.count=QComboBox()
        for value in (0,1,2,3,4,6):self.count.addItem('Automatic' if value==0 else str(value),value)
        self.count.setAccessibleName('Screenshots per page')
        self.mode=QComboBox();self.mode.addItem('Vertical','vertical');self.mode.addItem('Grid (two columns)','grid')
        self.mode.setAccessibleName('Screenshot layout')
        form.addRow('Screenshots per page',self.count);form.addRow('Layout',self.mode)
        note=QLabel('Maximum screenshots per page. Images keep their proportions; long instructions may add pages. Automatic Vertical keeps flowing; Automatic Grid uses up to four screenshots. Layout applies to generated SOP content. Direct Word edits are retained until you choose Rebuild from captured steps.')
        note.setWordWrap(True);note.setObjectName('caption');form.addRow(note)
        self.count.currentIndexChanged.connect(lambda _:self.changed.emit());self.mode.currentIndexChanged.connect(lambda _:self.changed.emit())

    def values(self):
        return {'screenshots_per_page':self.count.currentData(),'screenshot_layout':self.mode.currentData()}

    def set_values(self,values):
        settings=appearance(values);blocked=self.blockSignals(True)
        try:
            self.count.setCurrentIndex(self.count.findData(settings['screenshots_per_page']))
            self.mode.setCurrentIndex(self.mode.findData(settings['screenshot_layout']))
        finally:self.blockSignals(blocked)
