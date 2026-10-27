"""Render the demonstration PDF and application pages for local visual QA."""
from pathlib import Path
import sys
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize, QBuffer, QIODevice
from PySide6.QtPdf import QPdfDocument
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt
from sop_capture.storage import ProjectStore
from sop_capture.ui.main_window import MainWindow


def main():
    app = QApplication([])
    root = Path(__file__).resolve().parents[1]
    output = root / ".superpowers" / "visual"
    output.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="sop-visual-")
    project_root = Path(temporary.name) / "project"
    shutil.copytree(root / "demo" / "Permit Management", project_root)
    store = ProjectStore(project_root)
    window = MainWindow()
    window.set_project(store.load(), store)
    window.show()
    app.processEvents()
    for number, page in enumerate(("capture", "editor", "document", "settings")):
        window.show_page(number)
        app.processEvents()
        window.grab().save(str(output / f"ui-{page}.png"))
    window.show_page(1)
    window.steps_list.setCurrentRow(1)
    window.tool_picker.setCurrentIndex(window.tool_picker.findData("edit"))
    window.canvas.apply_gesture((400, 530), (400, 530))
    app.processEvents()
    window.grab().save(str(output / "ui-annotation-edit.png"))
    from sop_capture.models import Annotation
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    window.current_step().annotations.extend([
        Annotation(kind="highlighter", points=[285, 335, 900, 375], color="#ffdd00", opacity=35),
        Annotation(kind="text", points=[600, 205, 1150, 270], color="#087f8c", text="Check the permit details", font_size=32),
    ])
    window.canvas.refresh()
    window.tool_picker.setCurrentIndex(window.tool_picker.findData("arrow"))
    window.canvas.set_annotation_style(color="#2563eb", width=9)
    rect = window.canvas.image_rect()
    def position(x, y):
        return QPoint(round(rect.x()+x*rect.width()/1280), round(rect.y()+y*rect.height()/780))
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=position(1100, 420))
    QTest.mouseMove(window.canvas, position(940, 360))
    app.processEvents()
    window.grab().save(str(output / "ui-annotation-preview.png"))
    QTest.keyClick(window.canvas, Qt.Key.Key_Escape)
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=position(940, 360))
    window.arrow_style_picker.showPopup()
    app.processEvents()
    window.arrow_style_picker.view().window().grab().save(str(output / "ui-arrow-dropdown.png"))
    window.arrow_style_picker.hidePopup()
    window.show_help()
    app.processEvents()
    window.help_dialog.grab().save(str(output / "ui-help.png"))
    window.help_dialog.show_topic("Annotations")
    app.processEvents()
    window.help_dialog.grab().save(str(output / "ui-help-annotations.png"))
    window.help_dialog.close()
    from sop_capture.ui.theme import stylesheet
    window.setStyleSheet(stylesheet(True))
    window.show_page(1)
    app.processEvents()
    window.grab().save(str(output / "ui-editor-dark.png"))
    document = QPdfDocument()
    source = QBuffer()
    source.setData((store.root / "Exports" / "Create_a_work_permit.pdf").read_bytes())
    source.open(QIODevice.OpenModeFlag.ReadOnly)
    document.load(source)
    for number in range(document.pageCount()):
        size = document.pagePointSize(number)
        image = document.render(number, QSize(int(size.width()*1.3), int(size.height()*1.3)))
        opaque = QImage(image.size(), QImage.Format.Format_RGB32)
        opaque.fill(Qt.GlobalColor.white)
        painter = QPainter(opaque)
        painter.drawImage(0, 0, image)
        painter.end()
        opaque.save(str(output / f"pdf-{number+1}.png"))
    document.close()
    window.close()
    temporary.cleanup()
    print(output)


if __name__ == "__main__":
    main()
