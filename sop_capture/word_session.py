"""Dedicated desktop Word process ownership and document lifecycle."""
import csv
from pathlib import Path
import subprocess
import logging

log=logging.getLogger(__name__)

class WordSession:
    """Own only a newly created Word process; never adopt an existing session."""
    def __init__(self, path, visible=True, read_only=False):
        import pythoncom
        import win32com.client
        import win32process
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq WINWORD.EXE', '/FO', 'CSV', '/NH'],
                                capture_output=True, text=True, check=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        existing = {int(row[1]) for row in csv.reader(result.stdout.splitlines())
                    if len(row) > 1 and row[0].upper() == 'WINWORD.EXE'}
        self.word = self.document = None
        self.owned = False
        self.externally_closed = False
        self.last_saved_path = Path(path).resolve()
        self.events = None
        self.initialized = True
        pythoncom.CoInitialize()
        try:
            self.word = win32com.client.DispatchEx('Word.Application')
            if self.word.Documents.Count:
                raise RuntimeError('Word reused an existing session. Close this editor and retry.')
            probe = self.word.Documents.Add()
            try:
                pid = win32process.GetWindowThreadProcessId(int(probe.ActiveWindow.Hwnd))[1]
                if pid in existing:
                    raise RuntimeError('Word reused an existing process. Direct editing was not started.')
                self.owned = True
            finally:
                probe.Close(False)
            self.word.AutomationSecurity = 3
            self.word.DisplayAlerts = 0
            log.info('Opening owned Word working document')
            self.document = self.word.Documents.Open(str(Path(path).resolve()), ReadOnly=read_only,
                                                    AddToRecentFiles=False, Visible=visible)
            log.info('Updating document fields and contents')
            # Rebuild generated contents rather than leaving cached entries
            # pointing at the removed template demonstration pages.
            self.document.Fields.Update()
            for index in range(1,self.document.TablesOfContents.Count+1):
                self.document.TablesOfContents(index).Update()
            for index in range(1,self.document.TablesOfFigures.Count+1):
                self.document.TablesOfFigures(index).Update()
            self.document.Repaginate()
            log.info('Word document ready')
            self.word.DisplayAlerts = -1 if visible else 0
            if visible:
                owner = self
                class Events:
                    def OnDocumentBeforeClose(self, Doc, Cancel):
                        # Remember native Save As even when the user closes Word
                        # before the next five-second project autosave.
                        try:
                            Doc = win32com.client.Dispatch(Doc)
                            if owner.document is not None and Doc.FullName == owner.document.FullName:
                                owner.last_saved_path = Path(Doc.FullName)
                        except Exception:
                            import logging
                            logging.getLogger(__name__).exception('Could not track closing Word document')
                self.events = win32com.client.WithEvents(self.word, Events)
            self.hwnd = int(self.document.ActiveWindow.Hwnd)
            self.word.Visible = visible
        except Exception:
            self.close()
            raise

    def save(self):
        # Ctrl+W may have closed the hosted document. Its last saved bytes remain
        # recoverable, but never silently pretend unsaved changes were persisted.
        try:
            import win32gui
            if not win32gui.IsWindow(self.hwnd):
                self.externally_closed = True
                return False
            if not self.document.Saved:
                self.document.Save()
            return True
        except Exception as exc:
            if getattr(exc, 'hresult', None) in (-2147417848, -2147023174, -2147220995):
                self.externally_closed = True
                return False
            raise RuntimeError('The Word document could not be saved. Keep the app open and retry. '
                               'If you closed it in Word, reopen the editor to recover the last save.') from exc

    def command(self, name):
        if name in ('Undo', 'Redo'):
            getattr(self.document, name)()
        else:
            font = self.document.ActiveWindow.Selection.Font
            setattr(font, name, 0 if getattr(font, name) else (-1 if name != 'Underline' else 1))

    @property
    def saved_path(self):
        if not self.externally_closed:
            self.last_saved_path = Path(self.document.FullName)
        return self.last_saved_path

    def close(self):
        if self.document is not None and not self.externally_closed:
            try:
                self.document.Close(False)
            except Exception:
                # Already closed externally is safe; never close other documents.
                if self.word is not None and self.word.Documents.Count:
                    raise
            self.document = None
        try:
            if self.owned and self.word is not None and self.word.Documents.Count == 0:
                self.word.Quit()
        except Exception as exc:
            # Word itself may have exited after Ctrl+W. Do not turn an already
            # closed process into an app shutdown failure.
            if getattr(exc, 'hresult', None) not in (-2147417848, -2147023174, -2147220995):raise
        finally:
            if self.events is not None:
                self.events.close()
                self.events = None
            self.word = None
            if self.initialized:
                import pythoncom
                pythoncom.CoUninitialize()
                self.initialized = False
