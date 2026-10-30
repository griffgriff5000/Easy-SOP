"""Verify packaged PE icon resources contain the supplied artwork at every size."""
from pathlib import Path
import argparse
import struct
import pefile


def verify(executable, icon):
    data = Path(icon).read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    assert (reserved, kind) == (0, 1)
    images = set()
    for index in range(count):
        length, offset = struct.unpack_from('<II', data, 6 + index * 16 + 8)
        images.add(data[offset:offset + length])
    with pefile.PE(str(executable)) as binary:
        resources = set()
        for resource in binary.DIRECTORY_ENTRY_RESOURCE.entries:
            if resource.id != 3: continue  # RT_ICON
            for item in resource.directory.entries:
                for language in item.directory.entries:
                    entry = language.data.struct
                    resources.add(binary.get_data(entry.OffsetToData, entry.Size))
    assert images <= resources, f'{executable} does not embed the complete application icon'
    print(Path(executable).name + ': supplied logo verified at all ' + str(count) + ' icon sizes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executables', type=Path, nargs='+')
    parser.add_argument('--icon', type=Path, default=Path(__file__).resolve().parents[1] / 'sop_capture/assets/app.ico')
    args = parser.parse_args()
    for executable in args.executables: verify(executable, args.icon)
