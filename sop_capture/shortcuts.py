"""Validated, portable app shortcuts. Profiles contain action IDs, never executable code."""
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt

# id: (label, default key, allowed in sequences, context)
ACTIONS = {
    'new': ('New SOP', 'Ctrl+N', False, 'idle'),
    'open': ('Open SOP', 'Ctrl+O', False, 'idle'),
    'save': ('Save SOP', 'Ctrl+S', True, 'project'),
    'undo': ('Undo', 'Ctrl+Z', False, 'project'),
    'redo': ('Redo', 'Ctrl+Y', False, 'project'),
    'add_step': ('Add step', '', True, 'project'),
    'duplicate_step': ('Duplicate step', '', True, 'step'),
    'delete_step': ('Delete step', '', False, 'step'),
    'move_up': ('Move step up', '', True, 'step'),
    'move_down': ('Move step down', '', True, 'step'),
    'next_step': ('Select next step', '', True, 'step'),
    'previous_step': ('Select previous step', '', True, 'step'),
    'group_steps': ('Group steps', '', False, 'step'),
    'rename_section': ('Rename section', '', False, 'step'),
    'review': ('Review SOP', '', False, 'project'),
    'preview_pdf': ('Preview PDF', '', False, 'project'),
    'export_pdf': ('Export PDF', '', False, 'project'),
    'export_word': ('Export Word', '', False, 'project'),
    'replace_image': ('Replace screenshot', '', False, 'step'),
    'retake_image': ('Retake selected window', '', False, 'step'),
    'save_png': ('Save annotated PNG', '', False, 'step'),
    'delete_annotation': ('Delete selected annotation', '', True, 'step'),
    'remove_marker': ('Remove click marker', '', True, 'step'),
    'capture_start': ('Start capture', '', False, 'idle'),
    'capture_pause': ('Pause / resume capture', '', False, 'recording'),
    'capture_stop': ('Stop capture', '', False, 'recording'),
    'help': ('User guide', 'F1', False, 'any'),
    'shortcuts': ('Customise shortcuts', '', False, 'idle'),
    'annotation_studio': ('Annotation Studio', '', False, 'idle'),
}
for name, label in [('marker','Click marker'), ('edit','Edit annotations'), ('arrow','Arrow'), ('line','Straight line'), ('callout','Text callout'), ('text','Text label'), ('circle','Circle'), ('highlight','Outline box'), ('highlighter','Translucent highlight'), ('redact','Redaction'), ('blur','Blur'), ('magnifier','Magnifier')]:
    ACTIONS['tool_'+name] = ('Tool: '+label, '', True, 'step')
for index, label in enumerate(['Capture','Step editor','Document','Settings','Templates','Home','Annotation library']):
    ACTIONS['page_'+str(index)] = ('Show '+label, '', True, 'idle')


def default_profile():
    return {'version':1, 'bindings':{key: row[1] for key,row in ACTIONS.items()}, 'sequences':[]}


def normalize_key(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError('Invalid shortcut')
    if not value.strip(): return ''
    sequence = QKeySequence.fromString(value, QKeySequence.SequenceFormat.PortableText)
    if sequence.count() != 1 or sequence[0].key() in (Qt.Key.Key_unknown, 0):
        raise ValueError('Use one key combination per shortcut.')
    key, modifiers = sequence[0].key(), sequence[0].keyboardModifiers()
    if not (Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24) and not modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
        raise ValueError('Use Ctrl, Alt or Windows with the key, or use a function key.')
    result = sequence.toString(QKeySequence.SequenceFormat.PortableText)
    if result in {'Ctrl+C','Ctrl+V','Ctrl+X','Ctrl+A','Ctrl+Insert','Shift+Insert'}:
        raise ValueError('That shortcut is reserved for editing text.')
    return result


def normalize_capture_key(value):
    from .windows import parse_hotkey
    modifiers, code = parse_hotkey(value)
    parts = [label for flag, label in [(2,'Ctrl'),(1,'Alt'),(4,'Shift'),(8,'Meta')] if modifiers & flag]
    parts.append('F'+str(code-0x6F) if 0x70 <= code <= 0x87 else chr(code))
    return normalize_key('+'.join(parts))


def validate_profile(data, capture_key='Ctrl+Shift+F8'):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Unsupported shortcut profile version.')
    bindings, sequences = data.get('bindings'), data.get('sequences', [])
    if not isinstance(bindings, dict) or set(bindings)-set(ACTIONS):
        raise ValueError('Profile contains unknown actions.')
    if not isinstance(sequences, list) or len(sequences) > 100:
        raise ValueError('A profile supports up to 100 sequences.')
    result = default_profile()
    result['bindings'].update(bindings)
    used = {}
    # The native capture setting may temporarily contain invalid text while being edited.
    try: reserved = normalize_capture_key(capture_key)
    except ValueError: reserved = ''
    def check(value, label):
        key = normalize_key(value)
        if key:
            if key == reserved: raise ValueError(f'{label}: shortcut is reserved for manual capture.')
            if key in used: raise ValueError(f'{label}: {key} is already assigned to {used[key]}.')
            used[key] = label
        return key
    for action, key in result['bindings'].items():
        result['bindings'][action] = check(key, ACTIONS[action][0])
    identities = set()
    for sequence in sequences:
        if not isinstance(sequence, dict): raise ValueError('Invalid sequence.')
        identity, name, steps = sequence.get('id'), sequence.get('name'), sequence.get('actions')
        if not isinstance(identity,str) or not identity or len(identity)>80 or identity in identities:
            raise ValueError('Sequences must have unique identifiers.')
        if not isinstance(name,str) or not name.strip() or len(name)>100:
            raise ValueError('Give each sequence a name of up to 100 characters.')
        if not isinstance(steps,list) or not 1 <= len(steps) <= 20 or any(not isinstance(a,str) or a not in ACTIONS or not ACTIONS[a][2] for a in steps):
            raise ValueError('Sequences need 1-20 supported editor actions.')
        identities.add(identity)
        result['sequences'].append({'id':identity,'name':name.strip(),'shortcut':check(sequence.get('shortcut',''),name), 'actions':list(steps)})
    return result


def run_sequence(sequence, invoke):
    for action in sequence['actions']:
        if not invoke(action): return False
    return True
