"""Immutable document snapshots, independent of capture source data."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import uuid
from zipfile import ZipFile, BadZipFile

from .storage import atomic_bytes


def source_fingerprint(project):
    data = project.to_dict()
    for key in ('document_file', 'document_source_key', 'schema_version', 'updated'):
        data.pop(key, None)
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def store_document(store, data):
    try:
        if len(data) > 250_000_000:
            raise ValueError('Document exceeds 250 MB')
        with ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 1_000_000_000:
                raise ValueError('Expanded document is too large')
            types = archive.read('[Content_Types].xml')
            if b'wordprocessingml.document.main+xml' not in types or b'macroEnabled' in types:
                raise ValueError('Choose a Word .docx document')
            archive.read('word/document.xml')
    except (BadZipFile, KeyError) as exc:
        raise ValueError('Invalid Word document') from exc
    relative = f'Documents/{uuid.uuid4().hex}.docx'
    atomic_bytes(store.resolve(relative), data)
    return relative


def make_working_copy(project, root, output, rebuild=False):
    from .word_export import export_docx
    snapshot = deepcopy(project)
    if rebuild:
        snapshot.document_file = None
        snapshot.document_source_key = ''
    return export_docx(snapshot, root, Path(output))
