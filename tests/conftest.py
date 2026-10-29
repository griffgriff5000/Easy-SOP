"""Keep one Qt application alive for the full desktop test session."""
import os
import gc
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QEvent,QStandardPaths
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope='session',autouse=True)
def qt_application():
    QStandardPaths.setTestModeEnabled(True)
    app=QApplication.instance() or QApplication([])
    yield app
    # Finish Qt resource disposal while QApplication still owns its platform state.
    gc.collect()
    # Qt can retain closed top-level editors via signal/parent references. Dispose
    # them explicitly before QApplication tears down fonts/PDF/platform services.
    for widget in app.topLevelWidgets():widget.deleteLater()
    app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    app.processEvents()
    gc.collect()
    app.sendPostedEvents(None,QEvent.Type.DeferredDelete)

@pytest.fixture(autouse=True)
def finish_qt_deferred_cleanup(qt_application):
    yield
    # Unit tests do not run QApplication.exec(); service deferred widget/document
    # deletion between cases as the real application event loop normally does.
    # Bound signal callbacks can retain closed editors in Python cycles. Release
    # those wrappers before Qt/PDF platform teardown, rather than at interpreter exit.
    gc.collect()
    qt_application.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    qt_application.processEvents()
    qt_application.sendPostedEvents(None,QEvent.Type.DeferredDelete)
