"""Shared colours, typography and control sizing for every studio workspace."""
def stylesheet(dark=False):
    bg,panel,text,muted,border=("#101c29","#192a3b","#eff5fb","#a1b4c7","#30475c") if dark else ("#f2f6fa","#ffffff","#183247","#587084","#d6e1ea")
    nav,selected=("#142333","#24485a") if dark else ("#e8eef4","#d7edf1")
    return f"""
    QWidget {{ font-family:'Segoe UI';font-size:10pt;color:{text}; }}
    QMainWindow,QDialog,QWidget#scrollPage {{ background:{bg}; }}
    QWidget#panel,QFrame#panel,QWidget#toolRail {{ background:{panel};border:1px solid {border};border-radius:6px; }}
    QMenuBar,QMenu {{ background:{panel};color:{text}; }}
    QMenuBar::item,QMenu::item {{ padding:6px 12px; }}
    QMenuBar::item:selected,QMenu::item:selected {{ background:{selected}; }}
    QFrame#sidebar {{ background:{nav};border-radius:8px; }}
    QFrame#sidebar QLabel {{ color:{text}; }}
    QFrame#sidebar QPushButton {{ background:transparent;border:0;text-align:left;padding:8px 10px; }}
    QFrame#sidebar QPushButton:checked {{ background:{selected};color:{text};border-radius:5px; }}
    QLabel#heading {{ font-size:18pt;font-weight:600; }}
    QLabel#subheading,QLabel#caption {{ color:{muted}; }}
    QLabel#status {{ background:{panel};padding:10px;border:1px solid {border};border-radius:6px; }}
    QPushButton,QToolButton {{ background:{panel};border:1px solid {border};border-radius:5px;padding:6px 8px;min-height:20px; }}
    QToolButton {{ padding:6px 8px; }}
    QToolButton[menuButton="true"] {{ padding-right:18px; }}
    QToolButton::menu-indicator {{ subcontrol-origin:padding;subcontrol-position:right center;right:4px;width:8px;height:8px; }}
    QPushButton:hover,QToolButton:hover {{ border-color:#168b9b;background:{bg}; }}
    QToolButton:checked {{ background:{selected};border-color:#168b9b; }}
    QPushButton:disabled,QToolButton:disabled {{ color:{muted}; }}
    QPushButton#primary,QToolButton#primary {{ background:#087f8c;color:white;font-weight:600;border-color:#087f8c; }}
    QPushButton#danger {{ background:#b73d48;color:white; }}
    QPushButton#primary:disabled,QToolButton#primary:disabled,QPushButton#danger:disabled {{ background:{bg};color:{muted};border:1px solid {border}; }}
    QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox,QKeySequenceEdit {{ background:{panel};border:1px solid {border};border-radius:5px;padding:5px 7px;selection-background-color:#168b9b;selection-color:white;min-height:20px; }}
    QLineEdit:disabled,QPlainTextEdit:disabled,QComboBox:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled {{ color:{muted};background:{bg}; }}
    QComboBox QAbstractItemView {{ background:{panel};color:{text};selection-background-color:#168b9b;selection-color:white; }}
    QListWidget,QTableWidget,QTextBrowser {{ background:{panel};border:1px solid {border};border-radius:6px;padding:4px; }}
    QListWidget::item {{ padding:6px 5px;border-radius:4px; }}
    QListWidget::item:selected {{ background:{selected};color:{text}; }}
    QTabWidget::pane {{ border:1px solid {border};border-radius:5px;background:{bg}; }}
    QTabBar::tab {{ background:{nav};color:{muted};padding:8px 12px;border:0;border-bottom:2px solid transparent; }}
    QTabBar::tab:selected {{ color:{text};background:{panel};border-bottom-color:#087f8c; }}
    QTabBar::tab:hover {{ color:{text}; }}
    QHeaderView::section {{ background:{nav};color:{text};padding:6px;border:0; }}
    QScrollArea {{ border:0;background:transparent; }}
    QSplitter::handle {{ background:{border}; }}
    QSplitter::handle:horizontal {{ width:2px;margin:0 3px; }}
    QDockWidget::title {{ background:{nav};padding:5px;font-weight:600; }}
    QGroupBox {{ border:1px solid {border};border-radius:6px;margin-top:14px;padding:12px;font-weight:600; }}
    QGroupBox::title {{ subcontrol-origin:margin;left:10px;padding:0 4px; }}
    QStatusBar {{ color:{muted}; }}
    QToolTip {{ background:{panel};color:{text};border:1px solid {border};padding:4px; }}
    """
