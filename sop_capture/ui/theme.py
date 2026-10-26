def stylesheet(dark=False):
    bg, panel, text, muted, border = ("#101c29", "#192a3b", "#eff5fb", "#a1b4c7", "#30475c") if dark else ("#f2f6fa", "#ffffff", "#183247", "#587084", "#d6e1ea")
    return f"""
    QWidget {{ font-family: 'Segoe UI'; font-size: 10pt; color: {text}; }}
    QMainWindow, QDialog {{ background: {bg}; }}
    QFrame#sidebar {{ background: #142e44; border-radius: 14px; }}
    QFrame#sidebar QLabel {{ color: #edf5fd; }}
    QFrame#sidebar QPushButton {{ color: #e4eef8; background: transparent; border: 0; text-align: left; padding: 14px; }}
    QFrame#sidebar QPushButton:checked {{ background: #275473; border-radius: 8px; }}
    QLabel#heading {{ font-size: 25pt; font-weight: 700; }}
    QLabel#subheading {{ color: {muted}; font-size: 11pt; }}
    QLabel#eyebrow {{ color: #218a9b; font-weight: 700; letter-spacing: 2px; }}
    QLabel#status {{ background: {panel}; padding: 16px; border: 1px solid {border}; border-radius: 10px; }}
    QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 7px; padding: 9px 14px; }}
    QPushButton:hover {{ border-color: #218a9b; background: {bg}; }}
    QPushButton:disabled {{ color: {muted}; }}
    QPushButton#primary {{ background: #087f8c; color: white; font-weight: 700; border: 0; padding: 14px 22px; }}
    QPushButton#danger {{ background: #b73d48; color: white; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{ background: {panel}; border: 1px solid {border}; border-radius: 6px; padding: 8px; selection-background-color: #168b9b; }}
    QListWidget {{ background: {panel}; border: 1px solid {border}; border-radius: 9px; padding: 7px; }}
    QListWidget::item {{ padding: 12px 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: #d7edf1; color: #12394c; }}
    QScrollArea {{ border: 0; background: transparent; }}
    QGroupBox {{ border: 1px solid {border}; border-radius: 8px; margin-top: 16px; padding: 16px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; }}
    QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border}; }}
    """
