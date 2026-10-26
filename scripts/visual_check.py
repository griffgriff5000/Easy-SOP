"""Render the demonstration PDF and application pages for local visual QA."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
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
    store = ProjectStore(root / "demo" / "Permit Management")
    window = MainWindow()
    window.set_project(store.load(), store)
    window.show()
    app.processEvents()
    for number, page in enumerate(("capture", "editor", "document", "settings")):
        window.show_page(number)
        app.processEvents()
        window.grab().save(str(output / f"ui-{page}.png"))
    from sop_capture.ui.theme import stylesheet
    window.setStyleSheet(stylesheet(True))
    window.show_page(1)
    app.processEvents()
    window.grab().save(str(output / "ui-editor-dark.png"))
    document = QPdfDocument()
    document.load(str(store.root / "Exports" / "Create_a_work_permit.pdf"))
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
    print(output)


if __name__ == "__main__":
    main()
